# services/utils.py
from slugify import slugify
from pathlib import Path
from content_db import MediaItem
import logging

logger = logging.getLogger(__name__)

def move_and_rename_media(
    session,
    media_item: MediaItem,
    base_resources_dir: str,
    overwrite: bool = False
) -> bool:
    """
    Move file from uploads/ to resources/{folder}/{type}/{clean_name}
    Also moves thumbnail if exists.
    Returns True if successful.
    """
    if not media_item.filename:
        return False

    activity = media_item.activity
    if not activity or not activity.folder:
        logger.warning(f"No folder for activity {media_item.id_activity}")
        return False

    # Build target path
    type_subdir = media_item.type_media if media_item.type_media else "overig"
    clean_name = slugify(media_item.caption or Path(media_item.filename).stem)
    ext = Path(media_item.filename).suffix.lower() or ".jpg"
    new_filename = f"{clean_name}{ext}"

    target_dir = Path(base_resources_dir) / activity.folder / type_subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / new_filename

    # Source path (temporary upload)
    source_path = Path("uploads") / media_item.filename
    if not source_path.exists():
        logger.warning(f"Source file missing: {source_path}")
        return False

    # Move main file
    if target_path.exists() and not overwrite:
        logger.warning(f"File already exists: {target_path}")
        return False

    source_path.rename(target_path)

    # Move thumbnail if exists
    thumb_source = Path("uploads/thumbnails") / media_item.filename
    if thumb_source.exists():
        thumb_target_dir = target_dir / "thumbnails"
        thumb_target_dir.mkdir(exist_ok=True)
        thumb_target = thumb_target_dir / new_filename
        thumb_source.rename(thumb_target)

    # Update DB
    media_item.filename = new_filename
    media_item.storage_path = str(target_path.relative_to(base_resources_dir))
    session.add(media_item)
    session.flush()

    logger.info(f"Moved {media_item.filename} to {target_path}")
    return True