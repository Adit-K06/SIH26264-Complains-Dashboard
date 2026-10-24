"""Auth router — POST /auth/login, POST /auth/refresh, GET /auth/me.

Spec: AGENTS.md §API  Auth: POST /auth/login, POST /auth/refresh, GET /auth/me
Error envelope: {"error":{"code":"STRING","message":"text"}}
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.models.enums import RoleEnum
from app.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: RoleEnum
    bureau_id: int | None
    region_id: int | None
    active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lookup_active_user(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email, User.active.is_(True)).first()


def _make_tokens(user: User) -> TokenResponse:
    subject = str(user.id)
    access = create_access_token(subject)
    refresh = create_refresh_token(subject)
    return TokenResponse(access_token=access, refresh_token=refresh)


# ---------------------------------------------------------------------------
# POST /auth/login
# Accepts OAuth2 password-form (username field holds the email address).
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Issue access + refresh tokens for valid email / password credentials."""
    user = _lookup_active_user(db, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Invalid credentials"}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _make_tokens(user)


# ---------------------------------------------------------------------------
# POST /auth/refresh
# Accepts a JSON body with a refresh_token field.
# ---------------------------------------------------------------------------

class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": str(exc)}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "malformed token subject"}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    user: User | None = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "user not found or inactive"}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _make_tokens(user)


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user
