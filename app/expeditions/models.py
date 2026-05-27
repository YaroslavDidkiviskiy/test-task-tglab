import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class ExpeditionStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    active = "active"
    finished = "finished"


class MemberState(str, Enum):
    invited = "invited"
    confirmed = "confirmed"


ALLOWED_TRANSITIONS = {
    ExpeditionStatus.draft: ExpeditionStatus.ready,
    ExpeditionStatus.ready: ExpeditionStatus.active,
    ExpeditionStatus.active: ExpeditionStatus.finished,
}


class Expedition(Base):
    __tablename__ = "expeditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ExpeditionStatus] = mapped_column(default=ExpeditionStatus.draft)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    chief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chief: Mapped["User"] = relationship(back_populates="led_expeditions", foreign_keys=[chief_id])  # noqa: F821
    members: Mapped[list["ExpeditionMember"]] = relationship(back_populates="expedition", cascade="all, delete-orphan")


class ExpeditionMember(Base):
    __tablename__ = "expedition_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expedition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    state: Mapped[MemberState] = mapped_column(default=MemberState.invited)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    expedition: Mapped["Expedition"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")  # noqa: F821
