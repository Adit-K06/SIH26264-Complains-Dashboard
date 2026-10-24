"""FastAPI authentication and authorisation dependencies.

Roles and access rules come directly from AGENTS.md:
  BUREAU_OFFICER   – read all case status; create/update/act only in own bureau.
  REGIONAL_OFFICER – act only for institutions in own region.
  SENIOR_MGMT      – read all + escalate only.
  ADMIN            – users, roles, SLA config.

complainant_ref is masked outside own bureau/region scope (ADMIN sees all).

Never trust user-supplied role IDs or bureau IDs as proof of authorisation.
Enforcement is always driven by the JWT-derived user record fetched from the DB.
"""
from typing import Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.database import get_db
from app.models import User
from app.models.enums import RoleEnum
from app.security import TokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

_ERR_401 = {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}
_ERR_403 = {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}
_ERR_INACTIVE = {"error": {"code": "FORBIDDEN", "message": "Account is inactive"}}


def _unauthorized(msg: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "UNAUTHORIZED", "message": msg}},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(msg: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": {"code": "FORBIDDEN", "message": msg}},
    )


# ---------------------------------------------------------------------------
# Core dependency: authenticated user
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> User:
    """Resolve the Bearer token to a live, active User DB row.

    Raises 401 on any token problem; 403 if the account is inactive.
    """
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise _unauthorized(str(exc))

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise _unauthorized("malformed token subject")

    user: User | None = db.get(User, user_id)
    if user is None:
        raise _unauthorized("user not found")
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Account is inactive"}},
        )
    return user


# ---------------------------------------------------------------------------
# Role-based guards (return dependency callables)
# ---------------------------------------------------------------------------

def require_roles(*roles: RoleEnum):
    """Dependency factory: passes only if current user's role is in *roles*."""
    role_set = set(roles)

    def _dep(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in role_set:
            raise _forbidden()
        return current_user

    return _dep


# ---------------------------------------------------------------------------
# Convenience role-specific dependencies (pre-built)
# ---------------------------------------------------------------------------

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow only ADMIN."""
    if current_user.role != RoleEnum.ADMIN:
        raise _forbidden()
    return current_user


def require_senior_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow SENIOR_MGMT or ADMIN."""
    if current_user.role not in {RoleEnum.SENIOR_MGMT, RoleEnum.ADMIN}:
        raise _forbidden()
    return current_user


def require_any_authenticated(current_user: User = Depends(get_current_user)) -> User:
    """Allow any authenticated, active user (all four roles)."""
    return current_user


# ---------------------------------------------------------------------------
# Bureau / region scope helpers (used by case endpoints in later phases)
# ---------------------------------------------------------------------------

def assert_bureau_scope(user: User, bureau_id: int | None) -> None:
    """Raise 403 if BUREAU_OFFICER tries to act on a different bureau's resource."""
    if user.role == RoleEnum.BUREAU_OFFICER and user.bureau_id != bureau_id:
        raise _forbidden("Bureau officers may only act within their own bureau")


def assert_region_scope(user: User, region_id: int | None) -> None:
    """Raise 403 if REGIONAL_OFFICER tries to act on a different region's resource."""
    if user.role == RoleEnum.REGIONAL_OFFICER and user.region_id != region_id:
        raise _forbidden("Regional officers may only act for institutions in their own region")


def should_mask_complainant_ref(user: User, case_bureau_id: int | None, case_region_id: int | None) -> bool:
    """Return True when complainant_ref must be masked for this user.

    ADMIN always sees the reference.
    BUREAU_OFFICER sees it only for their own bureau's cases.
    REGIONAL_OFFICER sees it only for cases in their own region.
    SENIOR_MGMT never sees the masked value per AGENTS.md contract.
    """
    if user.role == RoleEnum.ADMIN:
        return False
    if user.role == RoleEnum.BUREAU_OFFICER:
        return user.bureau_id != case_bureau_id
    if user.role == RoleEnum.REGIONAL_OFFICER:
        return user.region_id != case_region_id
    # SENIOR_MGMT: mask always
    return True
