import os

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from slugify import slugify

from content_db import Activity, ActivityService, MediaService, Member, RoleService, db
from utils import move_and_rename_media

from .forms import QuickActivityForm

activity_bp = Blueprint(
    "activity",
    __name__,
    url_prefix="/activity",
    template_folder="../templates/activity",
)


@activity_bp.route("/new", methods=["GET", "POST"])
def new():
    form = QuickActivityForm()

    if form.validate_on_submit():
        # ────────────────────────────────────────────────
        #  Create new activity – fill from form
        # ────────────────────────────────────────────────
        activity = Activity(
            title=form.title.data.strip(),
            year=form.year.data,
            type=form.type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data.strip() or None,
            # folder will be generated below if not provided
        )

        # Generate folder name if user didn't specify one
        if not form.folder.data or not form.folder.data.strip():
            # Clean and slugify title → safe folder name
            safe_title = slugify(activity.title)
            activity.folder = f"{activity.year}-{safe_title}"
        else:
            # Use user-provided folder name, but still clean it
            activity.folder = slugify(form.folder.data.strip())

        base_folder = activity.folder
        counter = 1
        while Activity.query.filter_by(folder=activity.folder).first():
            activity.folder = f"{base_folder}-{counter}"
            counter += 1

        db.session.add(activity)
        db.session.commit()

        flash("Activiteit succesvol aangemaakt.", "success")
        return redirect(url_for("activity.detail", id_activity=activity.id_activity))

    # GET or validation failed → show form
    return render_template("activity_form.html", form=form, title="Nieuwe activiteit")


@activity_bp.route("/<id_activity>")
def detail(id_activity):
    activity = ActivityService.get_activity(db.session, id_activity, load_roles=True)
    if not activity:
        flash("Activiteit niet gevonden.", "danger")
        return redirect(url_for("core.index"))

    media = MediaService.list_media_for_activity(db.session, id_activity)
    members = Member.query.order_by(Member.current_last_name).all()
    return render_template(
        "activity_detail.html",
        activity=activity,
        media=media,
        members=members,
        roles=activity.roles,
    )


@activity_bp.route("/<id_activity>/bulk-assign", methods=["POST"])
def bulk_assign(id_activity):
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
                    appearance_context="bulk toegewezen",
                )

        # After successful assignment → finalize files
        for mid in media_ids:
            if item := MediaService.get_media_item(db.session, int(mid)):
                success = move_and_rename_media(
                    db.session,
                    item,
                    base_resources_dir=current_app.config["RESOURCES_FOLDER"],
                )
                if not success:
                    flash(f"Kon bestand {item.filename} niet verplaatsen", "warning")

        db.session.commit()

    flash(f"{len(media_ids)} media bijgewerkt met {len(member_ids)} leden.", "success")
    return redirect(url_for("activity.detail", id_activity=id_activity))


@activity_bp.route("/<id_activity>/parse-roles", methods=["POST"])
def parse_roles(id_activity):
    text = request.form.get("program_text", "").strip()

    with db.session.begin():
        created, errors = RoleService.bulk_create_from_text(
            db.session, id_activity=id_activity, program_text=text, delimiter="–"
        )
        db.session.commit()

    if errors:
        for error in errors:
            flash(error, "warning")

    flash(f"{created} rollen toegevoegd.", "success")
    return redirect(url_for("activity.detail", id_activity=id_activity))


@activity_bp.route("/<id_activity>/finalize-media", methods=["POST"])
def finalize_media(slug):
    activity = Activity.query.filter_by(slug=slug).first_or_404()

    for media in activity.media:
        if not media.storage_path or 'uploads/' not in media.storage_path:
            continue  # skip already finalized

        # Example move logic – adapt to your paths
        old = os.path.join(current_app.config['UPLOAD_FOLDER'], media.filename)
        new_dir = os.path.join(current_app.config['RESOURCES_DIR'], activity.folder)
        os.makedirs(new_dir, exist_ok=True)
        new = os.path.join(new_dir, media.filename)
        os.rename(old, new)

        media.storage_path = f"{activity.folder}/{media.filename}"
        # thumbnail generation here if needed

    db.session.commit()

    flash("Media succesvol gefinaliseerd.", "success")
    return redirect(url_for("activity.detail", id_activity=activity.id_activity))
