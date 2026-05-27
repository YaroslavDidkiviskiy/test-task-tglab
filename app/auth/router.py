from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.db import get_db
from app.auth.models import RefreshToken, User
from app.auth.schemas import LoginResponse, RegisterRequest
from app.auth.security import create_access_token, create_refresh_token, hash_password, verify_password

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=body.email, name=body.name, password=hash_password(body.password), role=body.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.email == form.username))
    if not user or not user.password or not verify_password(form.password, user.password):
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(403, "Inactive user")

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token()
    db.add(RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_expire_days),
    ))
    await db.commit()
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=not settings.debug, samesite="lax", max_age=settings.refresh_expire_days * 86400)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(401, "Refresh token not found")
    db_token = await db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token, RefreshToken.revoked == False))  # noqa: E712
    if not db_token or db_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid refresh token")

    user = await db.scalar(select(User).where(User.id == db_token.user_id))
    db_token.revoked = True
    new_token = create_refresh_token()
    db.add(RefreshToken(
        token=new_token,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_expire_days),
    ))
    await db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    response.set_cookie("refresh_token", new_token, httponly=True, secure=not settings.debug, samesite="lax", max_age=settings.refresh_expire_days * 86400)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        db_token = await db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
        if db_token:
            db_token.revoked = True
            await db.commit()
    response.delete_cookie("refresh_token")
    return {"ok": True}
