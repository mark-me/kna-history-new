# content_db/services/media_mention_service.py

from datetime import date
from typing import List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from ..models import MediaMention, Member, Activity, MediaItem, MentionMediaItem, MentionActivity, MentionMember


class MediaMentionService:
    """
    CRUD operations for MediaMention
    (press clippings, interviews, reviews, mentions in books/social media, etc.)
    """

    # ─── Create ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_media_mention(
        session: Session,
        mention_date: Optional[date] = None,
        source: str = "",
        title: str = "",
        url: Optional[str] = None,
        media_type: Optional[
            str
        ] = None,  # article / video / podcast / photo / mention / obituary / ...
        description: Optional[str] = None,
        notes: Optional[str] = None
    ) -> MediaMention:
        """
        Create a new media mention record.
        The linked entities (members, activities, media items) are optional.
        """
        if not source or not title:
            raise ValueError("source and title are required")

        mention = MediaMention(
            mention_date=mention_date,
            source=source.strip(),
            title=title.strip(),
            url=url.strip() if url else None,
            media_type=media_type.strip().lower() if media_type else None,
            description=description,
            notes=notes,
        )
        session.add(mention)
        session.flush()  # so we can use mention.id_mention immediately

        return mention

    # ─── Read ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_media_mention(session: Session, id_mention: int) -> Optional[MediaMention]:
        """Get a single mention by its ID"""
        return session.get(MediaMention, id_mention)

    @staticmethod
    def list_media_mentions(
        session: Session,
        mention_date_from: Optional[date] = None,
        mention_date_to: Optional[date] = None,
        source_contains: Optional[str] = None,
        media_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MediaMention]:
        """
        List media mentions with flexible filtering
        """
        stmt = select(MediaMention)

        if mention_date_from:
            stmt = stmt.where(MediaMention.mention_date >= mention_date_from)
        if mention_date_to:
            stmt = stmt.where(MediaMention.mention_date <= mention_date_to)
        if source_contains:
            stmt = stmt.where(MediaMention.source.ilike(f"%{source_contains}%"))
        if media_type:
            stmt = stmt.where(MediaMention.media_type == media_type.lower())

        stmt = stmt.order_by(
            MediaMention.mention_date.desc().nulls_last(), MediaMention.title
        )
        stmt = stmt.limit(limit).offset(offset)

        result = session.execute(stmt)
        return result.scalars().all()

    # ─── Update ──────────────────────────────────────────────────────────────

    @staticmethod
    def update_media_mention(
        session: Session,
        id_mention: int,
        mention_date: Optional[date] = None,
        source: Optional[str] = None,
        title: Optional[str] = None,
        url: Optional[str] = None,
        media_type: Optional[str] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[MediaMention]:
        """Partial update of a media mention"""
        values = {}
        if mention_date is not None:
            values["mention_date"] = mention_date
        if source is not None:
            values["source"] = source.strip()
        if title is not None:
            values["title"] = title.strip()
        if url is not None:
            values["url"] = url.strip() if url else None
        if media_type is not None:
            values["media_type"] = media_type.strip().lower() if media_type else None
        if description is not None:
            values["description"] = description
        if notes is not None:
            values["notes"] = notes

        if not values:
            return None

        stmt = (
            update(MediaMention)
            .where(MediaMention.id_mention == id_mention)
            .values(**values)
            .returning(MediaMention)
        )
        result = session.execute(stmt)
        updated = result.scalar_one_or_none()
        return updated

    # ─── Delete ──────────────────────────────────────────────────────────────

    @staticmethod
    def delete_media_mention(session: Session, id_mention: int) -> bool:
        """Delete a media mention record"""
        stmt = delete(MediaMention).where(MediaMention.id_mention == id_mention)
        result = session.execute(stmt)
        return result.rowcount > 0

    # ─── Convenience methods ─────────────────────────────────────────────────

    @staticmethod
    def find_mentions_for_member(
        session: Session, id_member: str, limit: int = 20
    ) -> List[MediaMention]:
        """
        Placeholder: find mentions related to a member.
        (Requires a many-to-many association table in real apps)
        """
        # If you later add a many-to-many table (member_mention), use join here
        # For now: return empty or implement simple text search in description/source
        stmt = (
            select(MediaMention)
            .where(
                MediaMention.description.ilike(f"%{id_member}%")
                | MediaMention.source.ilike(f"%{id_member}%")
            )
            .limit(limit)
        )
        result = session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def find_mentions_for_activity(
        session: Session, id_activity: str, limit: int = 20
    ) -> List[MediaMention]:
        # Similar placeholder logic
        stmt = (
            select(MediaMention)
            .where(MediaMention.description.ilike(f"%{id_activity}%"))
            .limit(limit)
        )
        result = session.execute(stmt)
        return result.scalars().all()


@staticmethod
def link_member_to_mention(
    session: Session,
    id_mention: int,
    id_member: str,
    role_context: Optional[str] = None,
    notes: Optional[str] = None
) -> MentionMember:
    mention = session.get(MediaMention, id_mention)
    member = session.get(Member, id_member)
    if not mention or not member:
        raise ValueError("Mention or member not found")

    link = MentionMember(
        mention_id=id_mention,
        member_id=id_member,
        role_context=role_context,
        notes=notes
    )
    session.add(link)
    session.flush()
    return link


@staticmethod
def link_activity_to_mention(
    session: Session,
    id_mention: int,
    id_activity: str,
    relevance: Optional[str] = None,
    notes: Optional[str] = None
) -> MentionActivity:
    mention = session.get(MediaMention, id_mention)
    activity = session.get(Activity, id_activity)
    if not mention or not activity:
        raise ValueError("Mention or activity not found")

    link = MentionActivity(
        mention_id=id_mention,
        activity_id=id_activity,
        relevance=relevance,
        notes=notes
    )
    session.add(link)
    session.flush()
    return link


@staticmethod
def link_media_item_to_mention(
    session: Session,
    id_mention: int,
    id_media_item: int,
    page_number: Optional[int] = None,
    notes: Optional[str] = None
) -> MentionMediaItem:
    mention = session.get(MediaMention, id_mention)
    item = session.get(MediaItem, id_media_item)
    if not mention or not item:
        raise ValueError("Mention or media item not found")

    link = MentionMediaItem(
        mention_id=id_mention,
        media_item_id=id_media_item,
        page_number=page_number,
        notes=notes
    )
    session.add(link)
    session.flush()
    return link