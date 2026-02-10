"""
KNA Data Reader Service

Reads and formats data from the new KNA content database for display.
Uses SQLAlchemy ORM instead of raw SQL / pandas where possible.
"""

import binascii
import os
from datetime import date
from typing import List, Dict, Optional, Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from ..config import BaseConfig
from ..database import get_session
from ..models import (
    Member, Activity, Role, MediaItem, MediaAppearance, MediaType, MemberNameHistory
)




class ReaderService:
    """
    Data access service for KNA content database (new structure).

    Provides methods to query and format data for web display.
    """

    def __init__(self, config: BaseConfig):
        """Initialize with configuration"""
        self.config = config
        self.dir_resources = config.DIR_RESOURCES
        logger.info(f"KnaDataReader initialized: {config.SQLITE_KNA_PATH}")

    # ─── Path encoding/decoding (unchanged) ─────────────────────────────────

    def encode(self, folder: str, file: str) -> str:
        path = os.path.join(folder, file)
        return binascii.hexlify(path.encode("utf-8")).decode()

    def decode(self, hex_path: str) -> str:
        return binascii.unhexlify(hex_path.encode("utf-8")).decode()

    # ─── Media enrichment (adapted) ─────────────────────────────────────────

    def enrich_media_items(self, items: List[MediaItem]) -> List[Dict[str, Any]]:
        """
        Enrich media items with thumbnail/media paths and display info.
        Works with ORM objects instead of DataFrame.
        """
        enriched = []
        for item in items:
            folder = item.activity.folder if item.activity else "unknown"
            file_ext = item.file_extension.lower() if item.file_extension else ""

            dir_media = os.path.join(self.dir_resources, folder)
            dir_thumbnail = os.path.join(dir_media, "thumbnails")

            # Special cases for non-image types
            if file_ext in ["pdf", "mp4"]:
                dir_thumbnail = os.path.join(self.dir_resources, "static/images")
                file_thumbnail = f"media_type_{'booklet' if file_ext == 'pdf' else 'video'}.png"
            else:
                file_thumbnail = item.filename

            path_thumbnail = self.encode(dir_thumbnail, file_thumbnail)
            path_media = self.encode(dir_media, item.filename)

            enriched.append({
                "id_media": item.id_media,
                "filename": item.filename,
                "type_media": item.type_media.capitalize(),
                "caption": item.caption,
                "credit": item.credit,
                "path_thumbnail": path_thumbnail,
                "path_media": path_media,
                "display_order": item.display_order,
                # Add more fields as needed (activity title, etc.)
                "activity_title": item.activity.title if item.activity else None,
            })

        return enriched

    # ─── Member info ────────────────────────────────────────────────────────

    def lid_info(self, id_lid: str) -> Optional[Dict[str, Any]]:
        """
        Get basic member information + media count.
        """
        with get_session() as session:
            stmt = (
                select(
                    Member,
                    func.count(MediaAppearance.id_appearance).label("qty_media")
                )
                .outerjoin(MediaAppearance, MediaAppearance.id_member == Member.id_member)
                .where(
                    (Member.id_member == id_lid) &
                    (Member.gdpr_permission == 1)
                )
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
                "Geboortedatum": member.birth_date.isoformat() if member.birth_date else None,
                "qty_media": qty_media or 0,
                # Add more fields if needed (e.g. name history, roles)
            }

    # ─── Timeline ───────────────────────────────────────────────────────────

    def timeline(self) -> List[Dict[str, Any]]:
        """
        Get chronological overview of productions/events and new members by year.
        """
        with get_session() as session:
            events = self._load_timeline_events(session)
            new_members = self._load_timeline_members(session)
            return self._build_timeline(events, new_members)

    def _load_timeline_events(self, session: Session) -> List[Dict[str, Any]]:
        """
        Load activities (productions/events) for timeline.
        """
        stmt = (
            select(
                Activity.id_activity,
                Activity.title,
                Activity.type,
                Activity.year,
                Activity.start_date,
                Activity.end_date,
                Activity.description
            )
            .order_by(Activity.year, Activity.start_date)
        )
        result = session.execute(stmt)
        return [dict(row._mapping) for row in result]

    def _load_timeline_members(self, session: Session) -> List[Dict[str, Any]]:
        """
        Load members who joined in specific years (GDPR-approved).
        """
        stmt = (
            select(
                Member.id_member,
                Member.current_first_name,
                Member.current_last_name,
                MemberNameHistory.valid_from.label("join_year")  # approximate from first name period
            )
            .join(MemberNameHistory, MemberNameHistory.id_member == Member.id_member)
            .where(Member.gdpr_permission == 1)
            .order_by(MemberNameHistory.valid_from)
        )
        result = session.execute(stmt)
        return [dict(row._mapping) for row in result]

    def _build_timeline(self, events: List[Dict], members: List[Dict]) -> List[Dict]:
        """
        Group events and new members by year.
        """
        from collections import defaultdict

        by_year = defaultdict(lambda: {"events": [], "new_members": []})

        # Group events
        for ev in events:
            year = ev.get("year") or (ev["start_date"].year if ev["start_date"] else None)
            if year:
                by_year[year]["events"].append(ev)

        # Group new members (using earliest valid_from as join year)
        for m in members:
            year = m.get("join_year") and m["join_year"].year
            if year:
                by_year[year]["new_members"].append({
                    "id_lid": m["id_member"],
                    "Voornaam": m["current_first_name"],
                    "Achternaam": m["current_last_name"],
                })

        # Build sorted result
        timeline = []
        for year in sorted(by_year.keys()):
            timeline.append({
                "jaar": year,
                "nieuwe_leden": by_year[year]["new_members"],
                "events": by_year[year]["events"],
            })

        return timeline

    # ─── Medium / file detail ───────────────────────────────────────────────

    def medium(self, dir_medium: str, file_medium: str) -> Optional[Dict]:
        """
        Get detailed info for a specific media file, including linked members.
        dir_medium and file_medium are decoded path parts.
        """
        with get_session() as session:
            # Find matching MediaItem (assuming folder is activity.folder)
            stmt = (
                select(MediaItem)
                .join(Activity, Activity.id_activity == MediaItem.id_activity)
                .where(
                    Activity.folder == dir_medium,
                    MediaItem.filename == file_medium
                )
                .options(selectinload(MediaItem.appearances).selectinload(MediaAppearance.member))
            )

            item = session.execute(stmt).scalar_one_or_none()
            if not item:
                return None

            appearances = [
                {
                    "id_lid": app.member.id_member,
                    "Voornaam": app.member.current_first_name,
                    "Achternaam": app.member.current_last_name,
                    "context": app.appearance_context
                }
                for app in item.appearances
            ]

            return {
                "id_media": item.id_media,
                "filename": item.filename,
                "type_media": item.type_media.capitalize(),
                "caption": item.caption,
                "credit": item.credit,
                "activity_title": item.activity.title if item.activity else None,
                "leden": appearances
            }