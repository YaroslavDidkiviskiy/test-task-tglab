import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.auth.models import User
from app.auth.security import decode_access_token
from app.expeditions.models import Expedition, ExpeditionMember
from app.ws.manager import manager
from jose import JWTError

router = APIRouter(tags=["ws"])


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(401, "Invalid token")
    user = await db.scalar(select(User).where(User.id == payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found")
    return user


async def check_expedition_access(db: AsyncSession, expedition_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    expedition = await db.scalar(select(Expedition).where(Expedition.id == expedition_id))
    if not expedition:
        return False
    if expedition.chief_id == user_id:
        return True
    member = await db.scalar(
        select(ExpeditionMember).where(
            ExpeditionMember.expedition_id == expedition_id,
            ExpeditionMember.user_id == user_id,
        )
    )
    return member is not None


@router.websocket("/ws/expeditions/{expedition_id}")
async def expedition_ws(
    websocket: WebSocket,
    expedition_id: uuid.UUID,
    token: str = Query(...),
):
    async with AsyncSessionLocal() as db:
        try:
            user = await get_user_from_token(token, db)
        except HTTPException:
            await websocket.close(code=4001)
            return

        has_access = await check_expedition_access(db, expedition_id, user.id)
        if not has_access:
            await websocket.close(code=4003)
            return

    await websocket.accept()
    manager.connect(expedition_id, user.id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(expedition_id, user.id)
