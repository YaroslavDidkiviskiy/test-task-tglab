import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User, Role
from app.expeditions.models import (
    Expedition, ExpeditionMember, ExpeditionStatus,
    MemberState, ALLOWED_TRANSITIONS,
)
from app.expeditions.schemas import ExpeditionCreate


async def create_expedition(db: AsyncSession, body: ExpeditionCreate, chief: User) -> Expedition:
    expedition = Expedition(
        title=body.title,
        description=body.description,
        start_at=body.start_at,
        end_at=body.end_at,
        capacity=body.capacity,
        chief_id=chief.id,
    )
    db.add(expedition)
    await db.commit()
    await db.refresh(expedition)
    return expedition


async def get_expedition_or_404(db: AsyncSession, expedition_id: uuid.UUID) -> Expedition:
    expedition = await db.scalar(select(Expedition).where(Expedition.id == expedition_id))
    if not expedition:
        raise HTTPException(404, "Expedition not found")
    return expedition


async def list_expeditions(db: AsyncSession, user: User) -> list[Expedition]:
    if user.role == Role.chief:
        result = await db.execute(select(Expedition).where(Expedition.chief_id == user.id))
        return list(result.scalars().all())
    else:
        result = await db.execute(
            select(Expedition)
            .join(ExpeditionMember, ExpeditionMember.expedition_id == Expedition.id)
            .where(ExpeditionMember.user_id == user.id)
        )
        return list(result.scalars().all())


async def transition_status(
    db: AsyncSession,
    expedition: Expedition,
    target: ExpeditionStatus,
    chief: User,
) -> Expedition:
    if expedition.chief_id != chief.id:
        raise HTTPException(403, "Only chief can change expedition status")

    allowed = ALLOWED_TRANSITIONS.get(expedition.status)
    if allowed != target:
        raise HTTPException(400, f"Cannot transition from {expedition.status} to {target}")

    if target == ExpeditionStatus.active:
        await _check_active_conditions(db, expedition)

    expedition.status = target
    await db.commit()
    await db.refresh(expedition)
    return expedition


async def _check_active_conditions(db: AsyncSession, expedition: Expedition) -> None:
    now = datetime.now(timezone.utc)

    if expedition.start_at.replace(tzinfo=timezone.utc) > now:
        raise HTTPException(400, "start_at must be <= now")

    result = await db.execute(
        select(ExpeditionMember).where(
            and_(
                ExpeditionMember.expedition_id == expedition.id,
                ExpeditionMember.state == MemberState.confirmed,
            )
        )
    )
    confirmed = list(result.scalars().all())
    confirmed_count = len(confirmed)

    if confirmed_count < 2:
        raise HTTPException(400, "At least 2 confirmed members required")

    if confirmed_count > expedition.capacity:
        raise HTTPException(400, "Confirmed members exceed capacity")

    confirmed_user_ids = [m.user_id for m in confirmed]
    result = await db.execute(
        select(ExpeditionMember).join(
            Expedition, Expedition.id == ExpeditionMember.expedition_id
        ).where(
            and_(
                ExpeditionMember.user_id.in_(confirmed_user_ids),
                Expedition.status == ExpeditionStatus.active,
                Expedition.id != expedition.id,
            )
        )
    )
    conflicts = result.scalars().first()
    if conflicts:
        raise HTTPException(400, "Some confirmed members are in another active expedition")


async def invite_member(
    db: AsyncSession,
    expedition: Expedition,
    user_id: uuid.UUID,
    chief: User,
) -> ExpeditionMember:
    if expedition.chief_id != chief.id:
        raise HTTPException(403, "Only chief can invite members")

    if expedition.status not in (ExpeditionStatus.draft, ExpeditionStatus.ready):
        raise HTTPException(400, "Cannot invite to active or finished expedition")

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    if user.role != Role.member:
        raise HTTPException(400, "Can only invite users with role 'member'")

    existing = await db.scalar(
        select(ExpeditionMember).where(
            and_(
                ExpeditionMember.expedition_id == expedition.id,
                ExpeditionMember.user_id == user_id,
            )
        )
    )
    if existing:
        raise HTTPException(409, "User already invited to this expedition")

    member = ExpeditionMember(expedition_id=expedition.id, user_id=user_id)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def confirm_membership(
    db: AsyncSession,
    expedition: Expedition,
    current_user: User,
) -> ExpeditionMember:
    member = await db.scalar(
        select(ExpeditionMember).where(
            and_(
                ExpeditionMember.expedition_id == expedition.id,
                ExpeditionMember.user_id == current_user.id,
            )
        )
    )
    if not member:
        raise HTTPException(404, "You are not invited to this expedition")

    if member.state != MemberState.invited:
        raise HTTPException(400, "Already confirmed")

    member.state = MemberState.confirmed
    member.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(member)
    return member
