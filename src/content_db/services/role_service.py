"""Service layer for Role operations"""
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models import Role, Member, Activity


class RoleService:
    """Service for managing theatre roles and cast assignments"""

    @staticmethod
    def create_role(
        session: Session,
        id_activity: str,
        id_member: str,
        role_name: Optional[str] = None,
        character_name: Optional[str] = None,
        role_type: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Role:
        """
        Create a new role assignment
        
        Args:
            session: Database session
            id_activity: Activity ID
            id_member: Member ID
            role_name: Name of the role (e.g., "Hamlet", "Director", "Lighting Designer")
            character_name: Character name if role_name is generic
            role_type: Type of role (lead/supporting/ensemble/crew/staff)
            notes: Additional notes
            
        Returns:
            Created Role instance
        """
        role = Role(
            id_activity=id_activity,
            id_member=id_member,
            role_name=role_name,
            character_name=character_name,
            role_type=role_type,
            notes=notes
        )
        session.add(role)
        session.flush()
        return role

    @staticmethod
    def get_role(session: Session, id_role: int) -> Optional[Role]:
        """Get a role by ID"""
        return session.query(Role).filter(Role.id_role == id_role).first()

    @staticmethod
    def get_roles_for_activity(
        session: Session, 
        id_activity: str,
        role_type: Optional[str] = None
    ) -> List[Role]:
        """
        Get all roles for an activity, optionally filtered by type
        
        Args:
            session: Database session
            id_activity: Activity ID
            role_type: Optional filter by role type
            
        Returns:
            List of Role instances with member relationships loaded
        """
        query = session.query(Role).filter(Role.id_activity == id_activity)
        
        if role_type:
            query = query.filter(Role.role_type == role_type)
            
        return query.order_by(Role.role_name).all()

    @staticmethod
    def get_roles_for_member(
        session: Session,
        id_member: str,
        limit: Optional[int] = None
    ) -> List[Role]:
        """
        Get all roles for a member across all activities
        
        Args:
            session: Database session
            id_member: Member ID
            limit: Optional limit on results
            
        Returns:
            List of Role instances ordered by activity year (descending)
        """
        query = (
            session.query(Role)
            .join(Activity)
            .filter(Role.id_member == id_member)
            .order_by(Activity.year.desc())
        )
        
        if limit:
            query = query.limit(limit)
            
        return query.all()

    @staticmethod
    def update_role(
        session: Session,
        id_role: int,
        role_name: Optional[str] = None,
        character_name: Optional[str] = None,
        role_type: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Role]:
        """
        Update a role
        
        Args:
            session: Database session
            id_role: Role ID to update
            role_name: New role name
            character_name: New character name
            role_type: New role type
            notes: New notes
            
        Returns:
            Updated Role instance or None if not found
        """
        role = RoleService.get_role(session, id_role)
        if not role:
            return None
            
        if role_name is not None:
            role.role_name = role_name
        if character_name is not None:
            role.character_name = character_name
        if role_type is not None:
            role.role_type = role_type
        if notes is not None:
            role.notes = notes
            
        session.flush()
        return role

    @staticmethod
    def delete_role(session: Session, id_role: int) -> bool:
        """
        Delete a role
        
        Args:
            session: Database session
            id_role: Role ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        role = RoleService.get_role(session, id_role)
        if not role:
            return False
            
        session.delete(role)
        session.flush()
        return True

    @staticmethod
    def find_or_create_member_by_name(
        session: Session,
        full_name: str
    ) -> Member:
        """
        Find existing member by name or create a new one
        Uses fuzzy matching to find existing members
        
        Args:
            session: Database session
            full_name: Full name string (will be split into first/last)
            
        Returns:
            Member instance (existing or newly created)
        """
        from .member_service import MemberService
        
        # Try to find existing member
        # Simple approach: check if name contains the search term
        parts = full_name.strip().split()
        if len(parts) >= 2:
            first_name = " ".join(parts[:-1])
            last_name = parts[-1]
        else:
            first_name = full_name
            last_name = ""
            
        # Search for existing member (case-insensitive)
        member = session.query(Member).filter(
            Member.current_first_name.ilike(f"%{first_name}%"),
            Member.current_last_name.ilike(f"%{last_name}%")
        ).first()
        
        if member:
            return member
            
        # Create new member
        return MemberService.quick_create_member(
            session,
            first_name=first_name,
            last_name=last_name
        )

    @staticmethod
    def bulk_create_from_text(
        session: Session,
        id_activity: str,
        program_text: str,
        delimiter: str = "–"
    ) -> tuple[int, List[str]]:
        """
        Parse program text and create multiple role assignments
        
        Expected format:
            Role Name – Actor Full Name
            Director – John Doe
            Hamlet – Jane Smith
            
        Args:
            session: Database session
            id_activity: Activity ID
            program_text: Multi-line text with role assignments
            delimiter: Character separating role from actor name
            
        Returns:
            Tuple of (created_count, errors_list)
        """
        lines = [line.strip() for line in program_text.splitlines() if line.strip()]
        created = 0
        errors = []
        
        for line in lines:
            if delimiter not in line:
                errors.append(f"Skipped (no delimiter): {line}")
                continue
                
            parts = line.split(delimiter, 1)
            role_name = parts[0].strip()
            actor_name = parts[1].strip()
            
            if not role_name or not actor_name:
                errors.append(f"Skipped (empty field): {line}")
                continue
                
            try:
                # Find or create member
                member = RoleService.find_or_create_member_by_name(session, actor_name)
                
                # Check if role already exists
                existing = session.query(Role).filter(
                    Role.id_activity == id_activity,
                    Role.id_member == member.id_member,
                    Role.role_name == role_name
                ).first()
                
                if existing:
                    errors.append(f"Already exists: {role_name} – {actor_name}")
                    continue
                
                # Create role
                RoleService.create_role(
                    session,
                    id_activity=id_activity,
                    id_member=member.id_member,
                    role_name=role_name
                )
                created += 1
                
            except Exception as e:
                errors.append(f"Error processing '{line}': {str(e)}")
                
        session.flush()
        return created, errors
