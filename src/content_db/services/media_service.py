# content_db/services/media_service.py

from datetime import date
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from ..models import Activity, MediaAppearance, MediaItem, MediaType, Member, Role


class MediaService:
    """
    CRUD operations for MediaItem (photos, videos, posters, programs, etc.)
    and MediaAppearance (which members/roles appear in which media)
    """

    # ─── MediaType (simple lookup table) ─────────────────────────────────────

    @staticmethod
    def create_or_get_media_type(
        session: Session, type_code: str, description: Optional[str] = None
    ) -> MediaType:
        """Create if not exists, otherwise return existing"""
        type_code = type_code.strip().lower()
        stmt = select(MediaType).where(MediaType.type_code == type_code)
        if existing := session.execute(stmt).scalar_one_or_none():
            return existing

        new_type = MediaType(
            type_code=type_code, description=description or type_code.capitalize()
        )
        session.add(new_type)
        session.flush()
        return new_type

    # ─── MediaItem CRUD ──────────────────────────────────────────────────────

    @staticmethod
    def create_media_item(
        session: Session,
        id_activity: str,
        filename: str,
        type_media: str,
        file_extension: Optional[str] = None,
        storage_path: Optional[str] = None,
        capture_date: Optional[date] = None,
        caption: Optional[str] = None,
        credit: Optional[str] = None,
        display_order: int = 0,
    ) -> MediaItem:
        """Create a new media item (photo, video, poster, program, etc.)"""
        if not id_activity or not filename or not type_media:
            raise ValueError("id_activity, filename and type_media are required")

        # Ensure media type exists
        MediaService.create_or_get_media_type(session, type_media)

        activity = session.get(Activity, id_activity)
        if not activity:
            raise ValueError(f"Activity {id_activity} not found")

        item = MediaItem(
            id_activity=id_activity,
            filename=filename.strip(),
            type_media=type_media.strip().lower(),
            file_extension=file_extension.strip().lower() if file_extension else None,
            storage_path=storage_path,
            capture_date=capture_date,
            caption=caption,
            credit=credit,
            display_order=display_order,
        )
        session.add(item)
        session.flush()  # so we can use item.id_media right away if needed
        return item

    @staticmethod
    def get_media_item(
        session: Session, id_media: int, load_appearances: bool = False
    ) -> Optional[MediaItem]:
        """Get single media item, optionally with appearances"""
        stmt = select(MediaItem).where(MediaItem.id_media == id_media)
        if load_appearances:
            stmt = stmt.options(selectinload(MediaItem.appearances))
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def list_media_for_activity(
        session: Session,
        id_activity: str,
        type_media: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MediaItem]:
        """List all media items belonging to one activity"""
        stmt = select(MediaItem).where(MediaItem.id_activity == id_activity)
        if type_media:
            stmt = stmt.where(MediaItem.type_media == type_media.lower())
        stmt = stmt.order_by(MediaItem.display_order, MediaItem.filename)
        stmt = stmt.limit(limit).offset(offset)
        result = session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def update_media_item(
        session: Session,
        id_media: int,
        filename: Optional[str] = None,
        type_media: Optional[str] = None,
        file_extension: Optional[str] = None,
        storage_path: Optional[str] = None,
        capture_date: Optional[date] = None,
        caption: Optional[str] = None,
        credit: Optional[str] = None,
        display_order: Optional[int] = None,
    ) -> Optional[MediaItem]:
        """Partial update"""
        values = {}
        if filename is not None:
            values["filename"] = filename.strip()
        if type_media is not None:
            values["type_media"] = type_media.strip().lower()
            # Ensure type exists
            MediaService.create_or_get_media_type(session, type_media)
        if file_extension is not None:
            values["file_extension"] = (
                file_extension.strip().lower() if file_extension else None
            )
        if storage_path is not None:
            values["storage_path"] = storage_path
        if capture_date is not None:
            values["capture_date"] = capture_date
        if caption is not None:
            values["caption"] = caption
        if credit is not None:
            values["credit"] = credit
        if display_order is not None:
            values["display_order"] = display_order

        if not values:
            return None

        stmt = (
            update(MediaItem)
            .where(MediaItem.id_media == id_media)
            .values(**values)
            .returning(MediaItem)
        )
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def delete_media_item(session: Session, id_media: int) -> bool:
        """Delete media item (will cascade to appearances if configured)"""
        stmt = delete(MediaItem).where(MediaItem.id_media == id_media)
        result = session.execute(stmt)
        return result.rowcount > 0

    # ─── MediaAppearance CRUD ────────────────────────────────────────────────

    @staticmethod
    def create_media_appearance(
        session: Session,
        id_media: int,
        id_member: str,
        id_role: Optional[int] = None,
        appearance_context: Optional[str] = None,
        display_order: int = 0,
        notes: Optional[str] = None,
    ) -> MediaAppearance:
        """Link a member (and optionally a role) to a media item"""
        media = session.get(MediaItem, id_media)
        if not media:
            raise ValueError(f"MediaItem {id_media} not found")

        member = session.get(Member, id_member)
        if not member:
            raise ValueError(f"Member {id_member} not found")

        if id_role:
            role = session.get(Role, id_role)
            if not role:
                raise ValueError(f"Role {id_role} not found")
            # Optional: check if role belongs to the same activity
            if role.id_activity != media.id_activity:
                raise ValueError(
                    "Role does not belong to the same activity as the media item"
                )

        appearance = MediaAppearance(
            id_media=id_media,
            id_member=id_member,
            id_role=id_role,
            appearance_context=appearance_context,
            display_order=display_order,
            notes=notes,
        )
        session.add(appearance)
        session.flush()
        return appearance

    @staticmethod
    def get_media_appearance(
        session: Session, id_appearance: int
    ) -> Optional[MediaAppearance]:
        """Get single appearance record"""
        return session.get(MediaAppearance, id_appearance)

    @staticmethod
    def list_appearances_for_media(
        session: Session,
        id_media: int,
        load_members: bool = False,
        load_roles: bool = False,
    ) -> List[MediaAppearance]:
        """All people/roles appearing in one media item"""
        stmt = select(MediaAppearance).where(MediaAppearance.id_media == id_media)
        if load_members:
            stmt = stmt.options(selectinload(MediaAppearance.member))
        if load_roles:
            stmt = stmt.options(selectinload(MediaAppearance.role))
        stmt = stmt.order_by(MediaAppearance.display_order)
        result = session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def update_media_appearance(
        session: Session,
        id_appearance: int,
        id_role: Optional[int] = None,  # can set to None to remove role context
        appearance_context: Optional[str] = None,
        display_order: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[MediaAppearance]:
        """Partial update"""
        values = {}
        if id_role is not None:  # explicit None allowed to clear
            values["id_role"] = id_role
        if appearance_context is not None:
            values["appearance_context"] = appearance_context
        if display_order is not None:
            values["display_order"] = display_order
        if notes is not None:
            values["notes"] = notes

        if not values:
            return None

        stmt = (
            update(MediaAppearance)
            .where(MediaAppearance.id_appearance == id_appearance)
            .values(**values)
            .returning(MediaAppearance)
        )
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def delete_media_appearance(session: Session, id_appearance: int) -> bool:
        """Remove one appearance link"""
        stmt = delete(MediaAppearance).where(
            MediaAppearance.id_appearance == id_appearance
        )
        result = session.execute(stmt)
        return result.rowcount > 0

    # ─── Convenience: bulk link members/roles to media ───────────────────────

    @staticmethod
    def link_members_to_media(
        session: Session,
        id_media: int,
        member_roles: List[
            dict
        ],  # [{'id_member': str, 'id_role': int|None, 'context': str, ...}]
    ) -> List[MediaAppearance]:
        created = []
        for data in member_roles:
            app = MediaService.create_media_appearance(
                session=session,
                id_media=id_media,
                id_member=data["id_member"],
                id_role=data.get("id_role"),
                appearance_context=data.get("appearance_context"),
                display_order=data.get("display_order", 0),
                notes=data.get("notes"),
            )
            created.append(app)
        return created
