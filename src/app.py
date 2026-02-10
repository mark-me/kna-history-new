import os
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.security import safe_join
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from PIL import Image
from slugify import slugify
from werkzeug.utils import secure_filename
from wtforms import (
    DateField,
    MultipleFileField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional

from config import Config
from content_db import (
    Activity,
    ActivityService,
    MediaAppearance,
    MediaItem,
    MediaService,
    Member,
    MemberService,
    Role,
    RoleService,
    db,
)
from utils import move_and_rename_media

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ─── Forms ───────────────────────────────────────────────────────────────

class QuickActivityForm(FlaskForm):
    title = StringField("Titel", validators=[DataRequired()])
    year = StringField("Jaar", validators=[DataRequired()])
    type = SelectField("Type", choices=[
        ("Uitvoering", "Uitvoering"),
        ("Event", "Evenement"),
        ("Rehearsal", "Repetitie"),
        ("Meeting", "Vergadering"),
    ], validators=[DataRequired()])
    start_date = DateField("Startdatum", validators=[Optional()])
    end_date = DateField("Einddatum", validators=[Optional()])
    folder = StringField("Mapnaam (optioneel)")
    description = TextAreaField("Beschrijving")
    submit = SubmitField("Activiteit aanmaken")


class QuickMemberForm(FlaskForm):
    first_name = StringField("Voornaam", validators=[DataRequired()])
    last_name = StringField("Achternaam", validators=[DataRequired()])
    id_lid = StringField("ID (optioneel – auto indien leeg)")
    submit = SubmitField("Lid toevoegen")


class UploadAndAssignForm(FlaskForm):
    files = MultipleFileField("Scans / foto's", validators=[DataRequired()])
    activity_id = SelectField("Toewijzen aan activiteit", coerce=str, validators=[DataRequired()])
    submit = SubmitField("Uploaden en toewijzen")


# ─── Routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    activities = ActivityService.list_activities(db.session, limit=20)
    return render_template("index.html", activities=activities)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    form = UploadAndAssignForm()
    form.activity_id.choices = [
        (a.id_activity, f"{a.year} – {a.title}") for a in Activity.query.order_by(Activity.year.desc()).all()
    ]

    if form.validate_on_submit():
        activity_id = form.activity_id.data

        for file in form.files.data:
            if file.filename == "":
                continue

            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # Create MediaItem
            media = MediaService.create_media_item(
                session=db.session,
                id_activity=activity_id,
                filename=filename,
                type_media="onbekend",  # will be set later
                storage_path=f"uploads/{filename}",  # temporary
                caption=file.filename
            )

        db.session.commit()
        flash(f"{len(form.files.data)} bestanden geüpload en toegewezen.", "success")
        return redirect(url_for("activity_detail", id_activity=activity_id))

    return render_template("upload.html", form=form)


@app.route("/activity/new", methods=["GET", "POST"])
def activity_new():
    form = QuickActivityForm()
    if form.validate_on_submit():
        activity = ActivityService.create_activity(
            session=db.session,
            id_activity=f"{form.year.data}-{form.title.data[:30]}",  # temp ID
            title=form.title.data,
            type_=form.type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            year=int(form.year.data),
            folder=form.folder.data or None,
            description=form.description.data
        )
        db.session.commit()
        flash("Activiteit aangemaakt.", "success")
        return redirect(url_for("activity_detail", id_activity=activity.id_activity))

    return render_template("activity_form.html", form=form, title="Nieuwe activiteit")


@app.route("/activity/<id_activity>")
def activity_detail(id_activity):
    activity = ActivityService.get_activity(db.session, id_activity, load_roles=True)
    if not activity:
        flash("Activiteit niet gevonden.", "danger")
        return redirect(url_for("index"))

    media = MediaService.list_media_for_activity(db.session, id_activity)
    return render_template("activity_detail.html", activity=activity, media=media)

@app.route("/member/quick-create", methods=["POST"])
def member_quick_create():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    id_lid = request.form.get("id_lid", "").strip()

    if not first_name or not last_name:
        flash("Voornaam en achternaam zijn verplicht", "danger")
        return render_template("partials/member_quick_form.html")

    with db.session.begin():
        member = MemberService.quick_create_member(
            db.session,
            first_name=first_name,
            last_name=last_name,
            id_lid=id_lid or None
        )

    # Return updated <select> with new member selected
    members = Member.query.order_by(Member.current_last_name).all()
    return render_template("partials/member_select.html", members=members, selected=member.id_member)


@app.route("/activity/<id_activity>/bulk-assign", methods=["POST"])
def bulk_assign_appearances(id_activity):
    media_ids = request.form.getlist("media_ids")
    member_ids = request.form.getlist("member_ids")
    role_ids = request.form.getlist("role_ids") or [None] * len(member_ids)

    with db.session.begin():
        for mid in media_ids:
            for i, mem_id in enumerate(member_ids):
                role_id = role_ids[i] if i < len(role_ids) else None
                MediaService.create_media_appearance(
                    db.session,
                    id_media=int(mid),
                    id_member=mem_id,
                    id_role=int(role_id) if role_id else None,
                    id_activity=id_activity,
                    appearance_context="bulk toegewezen"
                )
        
        # After successful assignment → finalize files
        for mid in media_ids:
            item = MediaService.get_media_item(db.session, int(mid))
            if item:
                success = move_and_rename_media(
                    db.session,
                    item,
                    base_resources_dir=app.config["RESOURCES_FOLDER"]
                )
                if not success:
                    flash(f"Kon bestand {item.filename} niet verplaatsen", "warning")
        
        db.session.commit()

    flash(f"{len(media_ids)} media bijgewerkt met {len(member_ids)} leden.", "success")
    return redirect(url_for("activity_detail", id_activity=id_activity))


@app.route("/activity/<id_activity>/parse-roles", methods=["POST"])
def parse_roles(id_activity):
    text = request.form.get("program_text", "").strip()
    
    with db.session.begin():
        created, errors = RoleService.bulk_create_from_text(
            db.session,
            id_activity=id_activity,
            program_text=text,
            delimiter="–"
        )
        db.session.commit()

    if errors:
        for error in errors:
            flash(error, "warning")
    
    flash(f"{created} rollen toegevoegd.", "success")
    return redirect(url_for("activity_detail", id_activity=id_activity))


def finalize_media_assignment(id_activity):
    activity = ActivityService.get_activity(db.session, id_activity)
    if not activity:
        flash("Activiteit niet gevonden", "danger")
        return redirect(url_for("activity_detail", id_activity=id_activity))

    media_items = MediaService.list_media_for_activity(db.session, id_activity)
    moved = 0
    failed = 0

    with db.session.begin():
        for item in media_items:
            if move_and_rename_media(db.session, item, app.config["RESOURCES_FOLDER"]):
                moved += 1
            else:
                failed += 1

        db.session.commit()

    flash(f"{moved} bestanden verplaatst, {failed} mislukt.", "success" if not failed else "warning")
    return redirect(url_for("activity_detail", id_activity=id_activity))

@app.route("/media/original/<path:rel_path>")
def serve_original(rel_path):
    """
    Serve original media files from resources/
    Example: /media/original/2016/Ajakkes/foto/photo.jpg
    """
    full_path = safe_join(app.config["RESOURCES_FOLDER"], rel_path)

    if not Path(full_path).is_file():
        abort(404)

    # Optional: add MIME type detection or caching headers later
    return send_from_directory(app.config["RESOURCES_FOLDER"], rel_path)


@app.route("/media/thumbnail/<path:rel_path>")
def serve_thumbnail(rel_path):
    """
    Serve thumbnails from resources/.../thumbnails/
    Falls back to static placeholder if missing
    Example: /media/thumbnail/2016/Ajakkes/foto/photo.jpg
    """
    thumb_path = safe_join(app.config["RESOURCES_FOLDER"], rel_path)

    if Path(thumb_path).is_file():
        return send_from_directory(app.config["RESOURCES_FOLDER"], rel_path)

    # Fallback to placeholder based on type (extract from path)
    type_media = "foto"  # default
    parts = rel_path.lower().split("/")
    if len(parts) >= 3 and parts[-3] in ["foto", "film", "poster", "audio", "pdf"]:
        type_media = parts[-3]

    fallback = {
        "pdf": "media_type_booklet.png",
        "mp4": "media_type_video.png",
        "film": "media_type_video.png",
        "poster": "media_type_booklet.png",
    }.get(type_media, "media_type_booklet.png")  # default placeholder

    return send_from_directory(app.config["STATIC_IMAGES_FOLDER"], fallback)


@app.route("/media/fallback/<filename>")
def serve_fallback(filename):
    """
    Direct fallback images (used by enrich_media_items or frontend)
    """
    return send_from_directory(app.config["STATIC_IMAGES_FOLDER"], filename)
# More routes later: member_new, role_add, media_assign, etc.

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESOURCES_FOLDER'], exist_ok=True)
    
    with app.app_context():
        db.create_all()  # ensure tables exist
    app.run(debug=True)