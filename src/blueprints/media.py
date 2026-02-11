import os
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from werkzeug.security import safe_join
from werkzeug.utils import secure_filename

from content_db import Activity, MediaService, db

from .forms import UploadAndAssignForm


media_bp = Blueprint(
    "media", __name__, url_prefix="/media", template_folder="../templates/media"
)


@media_bp.route("/upload", methods=["GET", "POST"])
def upload():
    form = UploadAndAssignForm()
    form.activity_id.choices = [
        (a.id_activity, f"{a.year} – {a.title}")
        for a in Activity.query.order_by(Activity.year.desc()).all()
    ]

    if form.validate_on_submit():
        activity_id = form.activity_id.data

        for file in form.files.data:
            if file.filename == "":
                continue

            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # Create MediaItem
            MediaService.create_media_item(
                session=db.session,
                id_activity=activity_id,
                filename=filename,
                type_media="onbekend",  # will be set later
                storage_path=f"uploads/{filename}",  # temporary
                caption=file.filename,
            )

        db.session.commit()
        flash(f"{len(form.files.data)} bestanden geüpload en toegewezen.", "success")
        return redirect(url_for("activity.detail", id_activity=activity_id))

    return render_template("upload.html", form=form)


@media_bp.route("/original/<path:rel_path>")
def serve_original(rel_path):
    full_path = safe_join(current_app.config["RESOURCES_FOLDER"], rel_path)
    if not Path(full_path).is_file():
        abort(404)
    return send_from_directory(current_app.config["RESOURCES_FOLDER"], rel_path)


@media_bp.route("/thumbnail/<path:rel_path>")
def serve_thumbnail(rel_path):
    """
    Serve thumbnails from resources/.../thumbnails/
    Falls back to static placeholder if missing
    Example: /media/thumbnail/2016/Ajakkes/foto/photo.jpg
    """
    thumb_path = safe_join(current_app.config["RESOURCES_FOLDER"], rel_path)

    if Path(thumb_path).is_file():
        return send_from_directory(current_app.config["RESOURCES_FOLDER"], rel_path)

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

    return send_from_directory(current_app.config["STATIC_IMAGES_FOLDER"], fallback)


@media_bp.route("/media/fallback/<filename>")
def serve_fallback(filename):
    """
    Direct fallback images (used by enrich_media_items or frontend)
    """
    return send_from_directory(current_app.config["STATIC_IMAGES_FOLDER"], filename)
