# models.py
from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Member(Base):
    __tablename__ = "member"

    id_member = Column(String, primary_key=True)
    current_first_name = Column(String, nullable=False)
    current_last_name = Column(String, nullable=False)
    birth_date = Column(Date)
    gdpr_permission = Column(Integer, default=1, nullable=False)  # 1 = visible
    notes = Column(Text)

    name_history = relationship("MemberNameHistory", back_populates="member")
    membership_periods = relationship("MembershipPeriod", back_populates="member")
    roles = relationship("Role", back_populates="member")
    appearances = relationship("MediaAppearance", back_populates="member")
    media_mentions = relationship("MentionMember", back_populates="member")

    __table_args__ = (
        Index("idx_member_name", "current_last_name", "current_first_name"),
        Index("idx_member_gdpr", "gdpr_permission"),
    )


class MemberNameHistory(Base):
    __tablename__ = "member_name_history"

    id_name_history = Column(Integer, primary_key=True, autoincrement=True)
    id_member = Column(String, ForeignKey("member.id_member"), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    valid_from = Column(Date)
    valid_to = Column(Date)
    change_reason = Column(String(100))   # marriage, divorce, stage name, etc.
    source = Column(String(200))
    display_priority = Column(Integer, default=10)
    notes = Column(Text)

    member = relationship("Member", back_populates="name_history")

    __table_args__ = (
        Index("idx_name_history_member_time", "id_member", "valid_from", postgresql_ops={"valid_from": "DESC"}),
    )


class MembershipPeriod(Base):
    __tablename__ = "membership_period"

    id_period = Column(Integer, primary_key=True, autoincrement=True)
    id_member = Column(String, ForeignKey("member.id_member"), nullable=False)
    join_date = Column(Date)
    leave_date = Column(Date)
    status = Column(String(50))           # active, alumni, guest, etc.
    notes = Column(Text)

    member = relationship("Member", back_populates="membership_periods")


class Activity(Base):
    __tablename__ = "activity"

    id_activity = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    type = Column(String(50), nullable=False)   # performance, event, meeting, ...
    start_date = Column(Date)
    end_date = Column(Date)
    year = Column(Integer)
    author = Column(String(150))
    director = Column(String(150))
    folder = Column(String(200))
    description = Column(Text)

    roles = relationship("Role", back_populates="activity")
    media_items = relationship("MediaItem", back_populates="activity")
    appearances = relationship("MediaAppearance", back_populates="activity")
    media_mentions = relationship("MentionActivity", back_populates="activity")

    __table_args__ = (
        Index("idx_activity_year", "year", postgresql_ops={"year": "DESC"}),
        Index("idx_activity_type_date", "type", "start_date"),
    )


class Location(Base):
    __tablename__ = "location"

    id_location = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String(200))
    city = Column(String(100))
    country = Column(String(100))
    venue_type = Column(String(80))
    coordinates = Column(String(100))     # e.g. "52.3676,4.9041"


class ActivityLocation(Base):
    __tablename__ = "activity_location"

    id_activity = Column(String, ForeignKey("activity.id_activity"), primary_key=True)
    id_location = Column(String, ForeignKey("location.id_location"), primary_key=True)


class Role(Base):
    __tablename__ = "role"

    id_role = Column(Integer, primary_key=True, autoincrement=True)
    id_activity = Column(String, ForeignKey("activity.id_activity"), nullable=False)
    id_member = Column(String, ForeignKey("member.id_member"), nullable=False)
    role_name = Column(String(150), nullable=True, default=None)
    character_name = Column(String(150))
    role_type = Column(String(50))        # lead, supporting, ensemble, crew, ...
    notes = Column(Text)

    activity = relationship("Activity", back_populates="roles")
    member = relationship("Member", back_populates="roles")
    appearances = relationship("MediaAppearance", back_populates="role")

    __table_args__ = (
        Index("idx_role_activity", "id_activity"),
        Index("idx_role_member", "id_member"),
    )


class MediaType(Base):
    __tablename__ = "media_type"

    type_code = Column(String(50), primary_key=True)
    description = Column(String(200))


class MediaItem(Base):
    __tablename__ = "media_item"

    id_media = Column(Integer, primary_key=True, autoincrement=True)
    id_activity = Column(String, ForeignKey("activity.id_activity"), nullable=False)
    filename = Column(String(300), nullable=False)
    type_media = Column(String(50), ForeignKey("media_type.type_code"), nullable=False)
    file_extension = Column(String(20))
    storage_path = Column(String(500))
    capture_date = Column(Date)
    caption = Column(Text)
    credit = Column(String(200))
    display_order = Column(Integer, default=0)

    activity = relationship("Activity", back_populates="media_items")
    appearances = relationship("MediaAppearance", back_populates="media_item")
    mentions = relationship("MentionMediaItem", back_populates="media_item")

    __table_args__ = (
        Index("idx_media_activity", "id_activity"),
        Index("idx_media_type_order", "type_media", "display_order"),
    )


class MediaAppearance(Base):
    __tablename__ = "media_appearance"

    id_appearance = Column(Integer, primary_key=True, autoincrement=True)

    id_media    = Column(Integer, ForeignKey("media_item.id_media"), nullable=False)
    id_member   = Column(String, ForeignKey("member.id_member"), nullable=False)
    id_role     = Column(Integer, ForeignKey("role.id_role"), nullable=True)

    id_activity = Column(String, ForeignKey("activity.id_activity"), nullable=False)

    appearance_context = Column(String(200))
    display_order      = Column(Integer, default=0)
    notes              = Column(Text)

    media_item = relationship("MediaItem",   back_populates="appearances")
    member     = relationship("Member",      back_populates="appearances")
    role       = relationship("Role",        back_populates="appearances")
    activity   = relationship("Activity",    back_populates="appearances")

    __table_args__ = (
        Index("idx_appearance_media", "id_media"),
        Index("idx_appearance_member", "id_member"),
        Index("idx_appearance_role", "id_role"),
    )


class MediaMention(Base):
    __tablename__ = "media_mention"

    id_mention = Column(Integer, primary_key=True, autoincrement=True)
    mention_date = Column(Date)
    source = Column(String(200))
    title = Column(String(300))
    url = Column(String(500))
    media_type = Column(String(80))
    description = Column(Text)
    notes = Column(Text)

    # Many-to-many relationships
    mentioned_members     = relationship("MentionMember", back_populates="mention", cascade="all, delete-orphan")
    mentioned_activities  = relationship("MentionActivity", back_populates="mention", cascade="all, delete-orphan")
    referenced_media_items = relationship("MentionMediaItem", back_populates="mention", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_mention_date", "mention_date", postgresql_ops={"mention_date": "DESC"}),
        Index("idx_mention_source_type", "source", "media_type"),
    )

# === Association tables ===

class MentionMember(Base):
    __tablename__ = "mention_member"

    mention_id = Column(Integer, ForeignKey("media_mention.id_mention"), primary_key=True)
    member_id  = Column(String, ForeignKey("member.id_member"), primary_key=True)

    # optional qualifiers
    role_context = Column(Text)     # e.g. "mentioned as director", "photo of this person"
    notes        = Column(Text)

    # relationships (bidirectional)
    mention = relationship("MediaMention", back_populates="mentioned_members")
    member  = relationship("Member", back_populates="media_mentions")

    __table_args__ = (
        Index("idx_mention_member_member", "member_id"),
    )


class MentionActivity(Base):
    __tablename__ = "mention_activity"

    mention_id   = Column(Integer, ForeignKey("media_mention.id_mention"), primary_key=True)
    activity_id  = Column(String, ForeignKey("activity.id_activity"), primary_key=True)

    relevance = Column(Text)        # e.g. "main subject", "brief reference", "photo included"
    notes     = Column(Text)

    mention  = relationship("MediaMention", back_populates="mentioned_activities")
    activity = relationship("Activity", back_populates="media_mentions")

    __table_args__ = (
        Index("idx_mention_activity_act", "activity_id"),
    )


class MentionMediaItem(Base):
    __tablename__ = "mention_media_item"

    mention_id    = Column(Integer, ForeignKey("media_mention.id_mention"), primary_key=True)
    media_item_id = Column(Integer, ForeignKey("media_item.id_media"), primary_key=True)

    page_number = Column(Integer)   # if mention is in a book/magazine
    notes       = Column(Text)

    mention    = relationship("MediaMention", back_populates="referenced_media_items")
    media_item = relationship("MediaItem", back_populates="mentions")

    __table_args__ = (
        Index("idx_mention_media_item", "media_item_id"),
    )


# ──────────────────────────────────────────────────────────────
# Create database function
# ──────────────────────────────────────────────────────────────

def create_database(db_path="data/kna_archive.db"):
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.drop_all(engine)    # optional: clean start
    Base.metadata.create_all(engine)
    print(f"Database created at: {db_path}")
    return engine


if __name__ == "__main__":
    create_database()