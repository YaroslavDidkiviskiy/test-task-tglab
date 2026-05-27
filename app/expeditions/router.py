import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user, require_role
from app.auth.models import Role, User
from app.db import get_db
from app.expeditions import service
from app.expeditions.models import ExpeditionStatus
from app.expeditions.schemas import ExpeditionCreate, ExpeditionRead, InviteRequest, MemberRead
from app.ws.manager import manager

router = APIRouter(prefix="/expeditions", tags=["expeditions"])


@router.post("", response_model=ExpeditionRead, status_code=201)
async def create_expedition(
    body: ExpeditionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.chief)),
):
    return await service.create_expedition(db, body, current_user)


@router.get("", response_model=list[ExpeditionRead])
async def list_expeditions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.list_expeditions(db, current_user)


@router.get("/{expedition_id}", response_model=ExpeditionRead)
async def get_expedition(
    expedition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_expedition_or_404(db, expedition_id)


@router.post("/{expedition_id}/status/ready", response_model=ExpeditionRead)
async def set_ready(
    expedition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.chief)),
):
    expedition = await service.get_expedition_or_404(db, expedition_id)
    updated = await service.transition_status(db, expedition, ExpeditionStatus.ready, current_user)
    await manager.broadcast_expedition(updated.id, {
        "event": "expedition_status",
        "expedition_id": str(updated.id),
        "status": updated.status.value,
    })
    return updated


@router.post("/{expedition_id}/status/active", response_model=ExpeditionRead)
async def set_active(
    expedition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.chief)),
):
    expedition = await service.get_expedition_or_404(db, expedition_id)
    updated = await service.transition_status(db, expedition, ExpeditionStatus.active, current_user)
    await manager.broadcast_expedition(updated.id, {
        "event": "expedition_status",
        "expedition_id": str(updated.id),
        "status": updated.status.value,
    })
    return updated


@router.post("/{expedition_id}/status/finished", response_model=ExpeditionRead)
async def set_finished(
    expedition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.chief)),
):
    expedition = await service.get_expedition_or_404(db, expedition_id)
    updated = await service.transition_status(db, expedition, ExpeditionStatus.finished, current_user)
    await manager.broadcast_expedition(updated.id, {
        "event": "expedition_status",
        "expedition_id": str(updated.id),
        "status": updated.status.value,
    })
    return updated


@router.post("/{expedition_id}/members", response_model=MemberRead, status_code=201)
async def invite_member(
    expedition_id: uuid.UUID,
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.chief)),
):
    expedition = await service.get_expedition_or_404(db, expedition_id)
    member = await service.invite_member(db, expedition, body.user_id, current_user)
    await manager.broadcast_expedition(expedition_id, {
        "event": "member_invited",
        "expedition_id": str(expedition_id),
        "user_id": str(member.user_id),
    })
    return member


@router.post("/{expedition_id}/members/confirm", response_model=MemberRead)
async def confirm_membership(
    expedition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.member)),
):
    expedition = await service.get_expedition_or_404(db, expedition_id)
    member = await service.confirm_membership(db, expedition, current_user)
    await manager.broadcast_expedition(expedition_id, {
        "event": "member_confirmed",
        "expedition_id": str(expedition_id),
        "user_id": str(current_user.id),
    })
    return member
