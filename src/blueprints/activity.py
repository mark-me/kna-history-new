from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from content_db import ActivityService, MediaService, Member, RoleService, db
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
        # ... same logic as before
        activity = ActivityService.create_activity(...)
        db.session.commit()
        flash("Activiteit aangemaakt.", "success")
        return redirect(url_for("activity.detail", id_activity=activity.id_activity))
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
def finalize_media(id_activity):
    activity = ActivityService.get_activity(db.session, id_activity)
    if not activity:
        flash("Activiteit niet gevonden", "danger")
        return redirect(url_for("activity.detail", id_activity=id_activity))

    media_items = MediaService.list_media_for_activity(db.session, id_activity)
    moved = 0
    failed = 0

    with db.session.begin():
        for item in media_items:
            if move_and_rename_media(
                db.session, item, current_app.config["RESOURCES_FOLDER"]
            ):
                moved += 1
            else:
                failed += 1

        db.session.commit()

    flash(
        f"{moved} bestanden verplaatst, {failed} mislukt.",
        "warning" if failed else "success",
    )
    return redirect(url_for("activity.detail", id_activity=id_activity))
