# content_db/services/activity_service.py

from datetime import date
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload


# Adjust imports based on your folder structure
from ..models import Activity, Member, Role


class ActivityService:
    """CRUD operations for Activities (performances, events, meetings, etc.) and their Roles"""

    # ─── Activity CRUD ───────────────────────────────────────────────────────

    @staticmethod
    def create_activity(
        session: Session,
        id_activity: str,
        title: str,
        type_: str = "Uitvoering",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        year: Optional[int] = None,
        author: Optional[str] = None,
        director: Optional[str] = None,
        folder: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Activity:
        """Create a new activity (performance, event, etc.)"""
        if not id_activity or not title:
            raise ValueError("id_activity and title are required")

        activity = Activity(
            id_activity=id_activity.strip(),
            title=title.strip(),
            type=type_.strip(),
            start_date=start_date,
            end_date=end_date,
            year=year,
            author=author.strip() if author else None,
            director=director.strip() if director else None,
            folder=folder.strip() if folder else None,
            description=description,
        )
        session.add(activity)
        session.flush()
        return activity

    @staticmethod
    def get_activity(
        session: Session, id_activity: str, load_roles: bool = False
    ) -> Optional[Activity]:
        """Get activity by ID, optionally with eager-loaded roles"""
        stmt = select(Activity).where(Activity.id_activity == id_activity)
        if load_roles:
            stmt = stmt.options(selectinload(Activity.roles).selectinload(Role.member))
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def list_activities(
        session: Session,
        year: Optional[int] = None,
        type_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Activity]:
        """List activities with optional filters"""
        stmt = select(Activity)
        if year is not None:
            stmt = stmt.where(Activity.year == year)
        if type_filter:
            stmt = stmt.where(Activity.type == type_filter)
        stmt = stmt.order_by(Activity.year.desc(), Activity.title)
        stmt = stmt.limit(limit).offset(offset)
        result = session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def update_activity(
        session: Session,
        id_activity: str,
        title: Optional[str] = None,
        type_: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        year: Optional[int] = None,
        author: Optional[str] = None,
        director: Optional[str] = None,
        folder: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Activity]:
        """Partial update of an activity"""
        values = {}
        if title is not None:
            values["title"] = title.strip()
        if type_ is not None:
            values["type"] = type_.strip()
        if start_date is not None:
            values["start_date"] = start_date
        if end_date is not None:
            values["end_date"] = end_date
        if year is not None:
            values["year"] = year
        if author is not None:
            values["author"] = author.strip() if author else None
        if director is not None:
            values["director"] = director.strip() if director else None
        if folder is not None:
            values["folder"] = folder.strip() if folder else None
        if description is not None:
            values["description"] = description

        if not values:
            return None

        stmt = (
            update(Activity)
            .where(Activity.id_activity == id_activity)
            .values(**values)
            .returning(Activity)
        )
        result = session.execute(stmt)
        updated = result.scalar_one_or_none()
        return updated

    @staticmethod
    def delete_activity(session: Session, id_activity: str) -> bool:
        """Delete activity (will fail if roles or media exist unless cascading is set)"""
        stmt = delete(Activity).where(Activity.id_activity == id_activity)
        result = session.execute(stmt)
        return result.rowcount > 0

    # ─── Role CRUD ───────────────────────────────────────────────────────────

    @staticmethod
    def create_role(
        session: Session,
        id_activity: str,
        id_member: str,
        role_name: str,
        character_name: Optional[str] = None,
        role_type: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Role:
        """Add a role to an existing activity and member"""
        activity = ActivityService.get_activity(session, id_activity)
        if not activity:
            raise ValueError(f"Activity {id_activity} not found")

        member = session.get(Member, id_member)
        if not member:
            raise ValueError(f"Member {id_member} not found")

        role = Role(
            id_activity=id_activity,
            id_member=id_member,
            role_name=role_name.strip(),
            character_name=character_name.strip() if character_name else None,
            role_type=role_type.strip() if role_type else None,
            notes=notes,
        )
        session.add(role)
        session.flush()
        return role

    @staticmethod
    def get_role(session: Session, id_role: int) -> Optional[Role]:
        """Get single role by its auto-increment ID"""
        return session.get(Role, id_role)

    @staticmethod
    def list_roles_for_activity(
        session: Session, id_activity: str, load_members: bool = False
    ) -> List[Role]:
        """Get all roles for a given activity"""
        stmt = select(Role).where(Role.id_activity == id_activity)
        if load_members:
            stmt = stmt.options(selectinload(Role.member))
        stmt = stmt.order_by(Role.role_name)
        result = session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def update_role(
        session: Session,
        id_role: int,
        role_name: Optional[str] = None,
        character_name: Optional[str] = None,
        role_type: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Role]:
        """Partial update of a role"""
        values = {}
        if role_name is not None:
            values["role_name"] = role_name.strip()
        if character_name is not None:
            values["character_name"] = (
                character_name.strip() if character_name else None
            )
        if role_type is not None:
            values["role_type"] = role_type.strip() if role_type else None
        if notes is not None:
            values["notes"] = notes

        if not values:
            return None

        stmt = (
            update(Role).where(Role.id_role == id_role).values(**values).returning(Role)
        )
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def delete_role(session: Session, id_role: int) -> bool:
        """Delete a single role"""
        stmt = delete(Role).where(Role.id_role == id_role)
        result = session.execute(stmt)
        return result.rowcount > 0

    # ─── Convenience: bulk add roles ────────────────────────────────────────

    @staticmethod
    def add_roles_to_activity(
        session: Session, id_activity: str, roles_data: List[dict]
    ) -> List[Role]:
        """Bulk add multiple roles (each dict: {'id_member': ..., 'role_name': ..., ...})"""
        created = []
        for data in roles_data:
            role = ActivityService.create_role(
                session=session,
                id_activity=id_activity,
                id_member=data["id_member"],
                role_name=data["role_name"],
                character_name=data.get("character_name"),
                role_type=data.get("role_type"),
                notes=data.get("notes"),
            )
            created.append(role)
        return created
