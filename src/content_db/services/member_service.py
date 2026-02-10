# src/content_db/services/member_service.py

from datetime import date
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from ..models import Member, MemberNameHistory


class MemberService:
    """CRUD operations for members and their name history"""

    @staticmethod
    def create_member(
        session: Session,
        id_member: str,
        current_first_name: str,
        current_last_name: str,
        birth_date: Optional[date] = None,
        gdpr_permission: int = 1,
        notes: Optional[str] = None,
    ) -> Member:
        """Create a new member"""
        if not id_member or not current_first_name or not current_last_name:
            raise ValueError("id_member, first_name and last_name are required")

        member = Member(
            id_member=id_member.strip(),
            current_first_name=current_first_name.strip(),
            current_last_name=current_last_name.strip(),
            birth_date=birth_date,
            gdpr_permission=gdpr_permission,
            notes=notes,
        )
        session.add(member)
        session.flush()  # get id if needed, but not necessary here
        return member

    @staticmethod
    def get_member(session: Session, id_member: str) -> Optional[Member]:
        """Get member by ID with eager-loaded name history"""
        stmt = (
            select(Member)
            .where(Member.id_member == id_member)
            .options(selectinload(Member.name_history))
        )
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def list_members(
        session: Session, gdpr_only: bool = True, limit: int = 100, offset: int = 0
    ) -> List[Member]:
        """List members, optionally only public ones"""
        stmt = select(Member)
        if gdpr_only:
            stmt = stmt.where(Member.gdpr_permission == 1)
        stmt = stmt.order_by(Member.current_last_name, Member.current_first_name)
        stmt = stmt.limit(limit).offset(offset)
        result = session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def update_member(
        session: Session,
        id_member: str,
        current_first_name: Optional[str] = None,
        current_last_name: Optional[str] = None,
        birth_date: Optional[date] = None,
        gdpr_permission: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[Member]:
        """Partial update"""
        stmt = (
            update(Member)
            .where(Member.id_member == id_member)
            .values(
                current_first_name=current_first_name.strip()
                if current_first_name
                else None,
                current_last_name=current_last_name.strip()
                if current_last_name
                else None,
                birth_date=birth_date,
                gdpr_permission=gdpr_permission,
                notes=notes,
            )
            .returning(Member)
        )
        result = session.execute(stmt)
        updated = result.scalar_one_or_none()
        return updated

    @staticmethod
    def delete_member(session: Session, id_member: str) -> bool:
        """Delete member (will fail if referenced)"""
        stmt = delete(Member).where(Member.id_member == id_member)
        result = session.execute(stmt)
        return result.rowcount > 0

    # ─── Name History ────────────────────────────────────────────────

    @staticmethod
    def add_name_history(
        session: Session,
        id_member: str,
        first_name: str,
        last_name: str,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        change_reason: Optional[str] = None,
        source: Optional[str] = None,
        display_priority: int = 10,
        notes: Optional[str] = None,
    ) -> MemberNameHistory:
        member = MemberService.get_member(session, id_member)
        if not member:
            raise ValueError(f"Member {id_member} not found")

        history = MemberNameHistory(
            id_member=id_member,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            valid_from=valid_from,
            valid_to=valid_to,
            change_reason=change_reason,
            source=source,
            display_priority=display_priority,
            notes=notes,
        )
        session.add(history)
        return history

    @staticmethod
    def get_name_history(session: Session, id_member: str) -> List[MemberNameHistory]:
        stmt = (
            select(MemberNameHistory)
            .where(MemberNameHistory.id_member == id_member)
            .order_by(
                MemberNameHistory.valid_from.desc(), MemberNameHistory.display_priority
            )
        )
        result = session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def quick_create_member(
        session: Session,
        first_name: str,
        last_name: str,
        id_lid: Optional[str] = None
    ) -> Member:
        """
        Quick create a member with auto-generated ID if not provided
        Used during workflow when discovering new members
        
        Args:
            session: Database session
            first_name: First name
            last_name: Last name  
            id_lid: Optional custom ID, auto-generated from name if not provided
            
        Returns:
            Created Member instance
        """
        from slugify import slugify
        
        # Generate ID if not provided
        if not id_lid:
            # Format: lastname-firstname (slugified)
            id_lid = slugify(f"{last_name}-{first_name}")
            
            # Check for duplicates and add number suffix if needed
            base_id = id_lid
            counter = 1
            while session.query(Member).filter(Member.id_member == id_lid).first():
                id_lid = f"{base_id}-{counter}"
                counter += 1
        
        return MemberService.create_member(
            session=session,
            id_member=id_lid,
            current_first_name=first_name,
            current_last_name=last_name,
            gdpr_permission=1,  # Default to visible
        )

