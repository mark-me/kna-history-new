"""
KNA Data Reader Service

Reads and formats data from the KNA content database for display.
Uses SQLAlchemy ORM with Flask-SQLAlchemy.
"""

import binascii
import os
from typing import List, Dict, Optional, Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from ..database import db
from ..models import (
    Member,
    Activity,
    Role,
    MediaItem,
    MediaAppearance,
    MediaType,
    MemberNameHistory,
)


class ReaderService:
    """
    Data access service for KNA content database.

    Provides methods to query and format data for web display.
    Now works with Flask-SQLAlchemy db.session.
    """

    def __init__(self, resources_dir: str = None):
        """
        Initialize with resources directory path

        Args:
            resources_dir: Path to resources directory (where media is stored)
                          If None, uses current Flask app config
        """
        if resources_dir is None:
            from flask import current_app

            self.dir_resources = current_app.config.get("RESOURCES_FOLDER", "resources")
        else:
            self.dir_resources = resources_dir

    # ─── Path encoding/decoding ─────────────────────────────────────

    def encode(self, folder: str, file: str) -> str:
        """Encode file path as hex string for URLs"""
        path = os.path.join(folder, file)
        return binascii.hexlify(path.encode("utf-8")).decode()

    def decode(self, hex_path: str) -> str:
        """Decode hex string back to file path"""
        return binascii.unhexlify(hex_path.encode("utf-8")).decode()

    # ─── Media enrichment ───────────────────────────────────────────

    def enrich_media_items(self, items: List[MediaItem]) -> List[Dict[str, Any]]:
        """
        Enrich media items with thumbnail/media paths and display info.

        Args:
            items: List of MediaItem ORM objects

        Returns:
            List of dictionaries with enriched media information
        """
        enriched = []
        for item in items:
            folder = item.activity.folder if item.activity else "unknown"
            file_ext = item.file_extension.lower() if item.file_extension else ""

            dir_media = os.path.join(self.dir_resources, folder, item.type_media)
            dir_thumbnail = os.path.join(dir_media, "thumbnails")

            # Special cases for non-image types
            if file_ext in ["pdf", "mp4"]:
                dir_thumbnail = "static/images"
                file_thumbnail = (
                    f"media_type_{'booklet' if file_ext == 'pdf' else 'video'}.png"
                )
            else:
                file_thumbnail = item.filename

            path_thumbnail = self.encode(dir_thumbnail, file_thumbnail)
            path_media = self.encode(dir_media, item.filename)

            enriched.append(
                {
                    "id_media": item.id_media,
                    "filename": item.filename,
                    "type_media": item.type_media.capitalize()
                    if item.type_media
                    else "Unknown",
                    "caption": item.caption,
                    "credit": item.credit,
                    "path_thumbnail": path_thumbnail,
                    "path_media": path_media,
                    "display_order": item.display_order,
                    "activity_title": item.activity.title if item.activity else None,
                    "activity_id": item.activity.id_activity if item.activity else None,
                    "activity_year": item.activity.year if item.activity else None,
                }
            )

        return enriched

    # ─── Member info ────────────────────────────────────────────────

    def lid_info(
        self, id_lid: str, session: Session = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get basic member information + media count.

        Args:
            id_lid: Member ID
            session: SQLAlchemy session (uses db.session if not provided)

        Returns:
            Dictionary with member info or None if not found
        """
        if session is None:
            session = db.session

        stmt = (
            select(Member, func.count(MediaAppearance.id_appearance).label("qty_media"))
            .outerjoin(MediaAppearance, MediaAppearance.id_member == Member.id_member)
            .where((Member.id_member == id_lid) & (Member.gdpr_permission == 1))
            .group_by(Member.id_member)
        )

        result = session.execute(stmt).first()
        if not result:
            return None

        member, qty_media = result

        return {
            "id_lid": member.id_member,
            "Voornaam": member.current_first_name,
            "Achternaam": member.current_last_name,
            "Geboortedatum": member.birth_date.isoformat()
            if member.birth_date
            else None,
            "qty_media": qty_media or 0,
        }

    # ─── Timeline ───────────────────────────────────────────────────

    def timeline(self, session: Session = None) -> List[Dict[str, Any]]:
        """
        Get chronological overview of productions/events and new members by year.

        Args:
            session: SQLAlchemy session (uses db.session if not provided)

        Returns:
            List of timeline entries by year
        """
        if session is None:
            session = db.session

        events = self._load_timeline_events(session)
        new_members = self._load_timeline_members(session)
        return self._build_timeline(events, new_members)

    def _load_timeline_events(self, session: Session) -> List[Dict[str, Any]]:
        """
        Load activities (productions/events) for timeline.
        """
        stmt = select(
            Activity.id_activity,
            Activity.title,
            Activity.type,
            Activity.year,
            Activity.start_date,
            Activity.end_date,
            Activity.description,
        ).order_by(Activity.year.desc(), Activity.start_date.desc())
        result = session.execute(stmt)
        return [dict(row._mapping) for row in result]

    def _load_timeline_members(self, session: Session) -> List[Dict[str, Any]]:
        """
        Load members who joined in specific years (GDPR-approved).
        Uses membership_period join_date if available.
        """
        from ..models import MembershipPeriod

        stmt = (
            select(
                Member.id_member,
                Member.current_first_name,
                Member.current_last_name,
                func.min(MembershipPeriod.join_date).label("join_date"),
            )
            .outerjoin(MembershipPeriod, MembershipPeriod.id_member == Member.id_member)
            .where(Member.gdpr_permission == 1)
            .group_by(Member.id_member)
            .order_by(func.min(MembershipPeriod.join_date))
        )
        result = session.execute(stmt)

        members = []
        for row in result:
            members.append(
                {
                    "id_member": row.id_member,
                    "current_first_name": row.current_first_name,
                    "current_last_name": row.current_last_name,
                    "join_date": row.join_date,
                }
            )

        return members

    def _build_timeline(self, events: List[Dict], members: List[Dict]) -> List[Dict]:
        """
        Group events and new members by year.
        """
        from collections import defaultdict

        by_year = defaultdict(lambda: {"events": [], "new_members": []})

        # Group events
        for ev in events:
            year = ev.get("year") or (
                ev["start_date"].year if ev.get("start_date") else None
            )
            if year:
                by_year[year]["events"].append(ev)

        # Group new members (using join_date year)
        for m in members:
            if year := m.get("join_date") and m["join_date"].year:
                by_year[year]["new_members"].append(
                    {
                        "id_lid": m["id_member"],
                        "Voornaam": m["current_first_name"],
                        "Achternaam": m["current_last_name"],
                    }
                )

        # Build sorted result
        timeline = []
        for year in sorted(by_year.keys(), reverse=True):
            timeline.append(
                {
                    "jaar": year,
                    "nieuwe_leden": by_year[year]["new_members"],
                    "events": by_year[year]["events"],
                }
            )

        return timeline

    # ─── Medium / file detail ───────────────────────────────────────

    def medium(
        self, dir_medium: str, file_medium: str, session: Session = None
    ) -> Optional[Dict]:
        """
        Get detailed info for a specific media file, including linked members.

        Args:
            dir_medium: Directory/folder name (typically activity folder)
            file_medium: Filename
            session: SQLAlchemy session (uses db.session if not provided)

        Returns:
            Dictionary with media details or None if not found
        """
        if session is None:
            session = db.session

        # Find matching MediaItem (assuming dir_medium is activity.folder)
        stmt = (
            select(MediaItem)
            .join(Activity, Activity.id_activity == MediaItem.id_activity)
            .where(
                Activity.folder.like(f"%{dir_medium}%"),
                MediaItem.filename == file_medium,
            )
            .options(
                selectinload(MediaItem.appearances).selectinload(
                    MediaAppearance.member
                ),
                selectinload(MediaItem.activity),
            )
        )

        item = session.execute(stmt).scalar_one_or_none()
        if not item:
            return None

        appearances = [
            {
                "id_lid": app.member.id_member,
                "Voornaam": app.member.current_first_name,
                "Achternaam": app.member.current_last_name,
                "context": app.appearance_context,
            }
            for app in item.appearances
            if app.member
        ]

        return {
            "id_media": item.id_media,
            "filename": item.filename,
            "type_media": item.type_media.capitalize()
            if item.type_media
            else "Unknown",
            "caption": item.caption,
            "credit": item.credit,
            "activity_title": item.activity.title if item.activity else None,
            "activity_id": item.activity.id_activity if item.activity else None,
            "leden": appearances,
        }

    # ─── Activity media ─────────────────────────────────────────────

    def activity_media(
        self, id_activity: str, session: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Get all media items for an activity with enriched paths.

        Args:
            id_activity: Activity ID
            session: SQLAlchemy session (uses db.session if not provided)

        Returns:
            List of enriched media items
        """
        if session is None:
            session = db.session

        stmt = (
            select(MediaItem)
            .where(MediaItem.id_activity == id_activity)
            .options(selectinload(MediaItem.activity))
            .order_by(MediaItem.display_order, MediaItem.id_media)
        )

        items = session.execute(stmt).scalars().all()
        return self.enrich_media_items(items)

    # ─── Member media ───────────────────────────────────────────────

    def member_media(
        self, id_member: str, session: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Get all media items where a member appears.

        Args:
            id_member: Member ID
            session: SQLAlchemy session (uses db.session if not provided)

        Returns:
            List of enriched media items
        """
        if session is None:
            session = db.session

        stmt = (
            select(MediaItem)
            .join(MediaAppearance, MediaAppearance.id_media == MediaItem.id_media)
            .where(MediaAppearance.id_member == id_member)
            .options(selectinload(MediaItem.activity))
            .order_by(MediaItem.id_media)
        )

        items = session.execute(stmt).scalars().all()
        return self.enrich_media_items(items)

    # ─── Search ─────────────────────────────────────────────────────

    def search_media(self, query: str, session: Session = None) -> List[Dict[str, Any]]:
        """
        Search media items by caption or filename.

        Args:
            query: Search query string
            session: SQLAlchemy session (uses db.session if not provided)

        Returns:
            List of enriched media items matching the search
        """
        if session is None:
            session = db.session

        stmt = (
            select(MediaItem)
            .where(
                (MediaItem.caption.ilike(f"%{query}%"))
                | (MediaItem.filename.ilike(f"%{query}%"))
            )
            .options(selectinload(MediaItem.activity))
            .order_by(MediaItem.id_media)
        )

        items = session.execute(stmt).scalars().all()
        return self.enrich_media_items(items)
