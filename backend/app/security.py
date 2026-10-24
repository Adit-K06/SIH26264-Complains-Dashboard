"""Password hashing and JWT token utilities.

JWT implementation uses stdlib (hmac + hashlib) for HS256, compatible with
the python-jose tokens the container uses when requirements.txt is installed.

Never log raw tokens, passwords, or the jwt_secret value.
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

from app.config import get_settings


# ---------------------------------------------------------------------------
# Password hashing  (bcrypt via the pinned bcrypt==4.0.1 package)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*. Use cost factor 12."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when *plain* matches the stored *hashed* value."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT  (stdlib HS256 — no third-party JWT library required on host)
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"
_JWT_HEADER = (
    base64.urlsafe_b64encode(
        json.dumps({"alg": _ALGORITHM, "typ": "JWT"}).encode()
    )
    .rstrip(b"=")
    .decode()
)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def _sign(header_payload: str, secret: str) -> str:
    return _b64_encode(
        hmac.new(secret.encode("utf-8"), header_payload.encode("utf-8"), hashlib.sha256).digest()
    )


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed HS256 JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_minutes)).timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    unsigned = f"{_JWT_HEADER}.{payload_b64}"
    sig = _sign(unsigned, settings.jwt_secret)
    return f"{unsigned}.{sig}"


def create_refresh_token(subject: str) -> str:
    """Create a signed HS256 JWT refresh token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.jwt_refresh_days)).timestamp()),
        "type": "refresh",
    }
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    unsigned = f"{_JWT_HEADER}.{payload_b64}"
    sig = _sign(unsigned, settings.jwt_secret)
    return f"{unsigned}.{sig}"


class TokenError(Exception):
    """Raised when a token is missing, malformed, or expired."""


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and verify a JWT token.  Raises TokenError on any problem."""
    settings = get_settings()
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise TokenError("malformed token")
        header_payload = f"{parts[0]}.{parts[1]}"
        expected_sig = _sign(header_payload, settings.jwt_secret)
        if not hmac.compare_digest(parts[2], expected_sig):
            raise TokenError("invalid signature")
        payload = json.loads(_b64_decode(parts[1]))
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise TokenError("malformed token") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"expected token type '{expected_type}'")
    exp = payload.get("exp")
    if exp is None or datetime.now(timezone.utc).timestamp() > exp:
        raise TokenError("token expired")
    return payload
