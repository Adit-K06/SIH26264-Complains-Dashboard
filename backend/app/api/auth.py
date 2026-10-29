"""Login and current-user API."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import create_access_token, get_current_user, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    username = payload.username.strip()
    user = db.scalar(
        select(User).where(
            or_(User.email == username, User.email.startswith(f"{username}@"))
        )
    )
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Username or password is incorrect."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


@router.get("/auth/me")
def me(user: Annotated[User, Depends(get_current_user)]):
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": role,
        "bureau_id": str(user.bureau_id) if user.bureau_id else None,
        "region_id": str(user.region_id) if user.region_id else None,
    }