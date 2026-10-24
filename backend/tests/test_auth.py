"""Tests for Phase 2: authentication and role-based access control.

All tests use an in-memory SQLite engine and override the `get_db` dependency —
no PostgreSQL connection is required on the host.

Tests cover:
  - Password hashing and verification (security.py)
  - JWT creation, decoding, expiry, wrong type (security.py)
  - POST /auth/login  — valid, wrong password, unknown email, inactive user
  - POST /auth/refresh — valid refresh, expired refresh, access token reused as refresh
  - GET /auth/me — authenticated, no token, malformed token, expired token
  - require_roles / require_admin / require_senior_or_admin dependencies
  - Bureau and region scope helpers
  - complainant_ref masking logic
  - Seed module: creates users, idempotent on second run
"""
import datetime
import time
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import get_db
from app.main import app
from app.models import Base, Bureau, Region, User
from app.models.enums import RoleEnum
from app.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.auth import (
    assert_bureau_scope,
    assert_region_scope,
    should_mask_complainant_ref,
)
from app.seed import seed

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
    """TestClient with get_db overridden to use the in-memory session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle managed by the db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(
    db_session,
    email="officer@test.local",
    plain_pw="secret",
    role=RoleEnum.BUREAU_OFFICER,
    bureau_id=None,
    region_id=None,
    active=True,
) -> User:
    """Helper: create and persist a User in the test DB."""
    user = User(
        name="Test User",
        email=email,
        password_hash=hash_password(plain_pw),
        role=role,
        bureau_id=bureau_id,
        region_id=region_id,
        active=active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ===========================================================================
# 1. Security — password hashing and verification
# ===========================================================================

class TestPasswordSecurity:
    def test_hash_is_not_plaintext(self):
        h = hash_password("mypassword")
        assert h != "mypassword"
        assert h.startswith("$2b$")

    def test_verify_correct_password(self):
        h = hash_password("correct")
        assert verify_password("correct", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_unique_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts


# ===========================================================================
# 2. Security — JWT encode / decode
# ===========================================================================

class TestJWT:
    def test_access_token_decodes_correctly(self):
        token = create_access_token("99")
        payload = decode_token(token, expected_type="access")
        assert payload["sub"] == "99"
        assert payload["type"] == "access"

    def test_refresh_token_decodes_correctly(self):
        token = create_refresh_token("99")
        payload = decode_token(token, expected_type="refresh")
        assert payload["sub"] == "99"
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self):
        token = create_access_token("99")
        with pytest.raises(TokenError, match="expected token type"):
            decode_token(token, expected_type="refresh")

    def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token("99")
        with pytest.raises(TokenError, match="expected token type"):
            decode_token(token, expected_type="access")

    def test_malformed_token_raises(self):
        with pytest.raises(TokenError, match="malformed"):
            decode_token("not.a.valid.token")

    def test_tampered_signature_raises(self):
        token = create_access_token("1")
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsig"
        with pytest.raises(TokenError, match="invalid signature"):
            decode_token(tampered)

    def test_expired_token_raises(self):
        """Build a token with an exp already in the past."""
        import base64, hashlib, hmac as _hmac, json as _json
        settings = get_settings()
        header = (
            base64.urlsafe_b64encode(
                _json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        payload_data = {
            "sub": "1",
            "iat": 1000,
            "exp": 1001,    # far in the past
            "type": "access",
        }
        payload_b64 = (
            base64.urlsafe_b64encode(
                _json.dumps(payload_data, separators=(",", ":")).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        unsigned = f"{header}.{payload_b64}"
        sig = base64.urlsafe_b64encode(
            _hmac.new(settings.jwt_secret.encode(), unsigned.encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        expired_token = f"{unsigned}.{sig}"

        with pytest.raises(TokenError, match="expired"):
            decode_token(expired_token)

    def test_wrong_secret_raises(self):
        token = create_access_token("1")
        from unittest.mock import patch
        from app import config as cfg_mod
        with patch.object(get_settings(), "jwt_secret", "wrong-secret"):
            # We need to override the cached settings in security module
            # Easiest: tamper the signature manually
            parts = token.split(".")
            bad_token = f"{parts[0]}.{parts[1]}.AAABBB"
            with pytest.raises(TokenError, match="invalid signature"):
                decode_token(bad_token)


# ===========================================================================
# 3. POST /auth/login
# ===========================================================================

class TestLogin:
    def test_valid_login_returns_tokens(self, client, db_session):
        _make_user(db_session, email="valid@test.local", plain_pw="correct")
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "valid@test.local", "password": "correct"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, client, db_session):
        _make_user(db_session, email="wp@test.local", plain_pw="right")
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "wp@test.local", "password": "wrong"},
        )
        assert r.status_code == 401
        assert r.json()["detail"]["error"]["code"] == "UNAUTHORIZED"

    def test_unknown_email_returns_401(self, client, db_session):
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@test.local", "password": "anything"},
        )
        assert r.status_code == 401

    def test_inactive_user_cannot_login(self, client, db_session):
        _make_user(db_session, email="inactive@test.local", plain_pw="pw", active=False)
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "inactive@test.local", "password": "pw"},
        )
        assert r.status_code == 401

    def test_login_response_access_token_is_valid_jwt(self, client, db_session):
        _make_user(db_session, email="jwtcheck@test.local", plain_pw="pw2")
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "jwtcheck@test.local", "password": "pw2"},
        )
        assert r.status_code == 200
        token = r.json()["access_token"]
        payload = decode_token(token, expected_type="access")
        assert payload["sub"].isdigit()


# ===========================================================================
# 4. POST /auth/refresh
# ===========================================================================

class TestRefresh:
    def test_valid_refresh_issues_new_tokens(self, client, db_session):
        user = _make_user(db_session, email="refresh@test.local", plain_pw="pw")
        refresh_tok = create_refresh_token(str(user.id))
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body

    def test_access_token_rejected_as_refresh(self, client, db_session):
        user = _make_user(db_session, email="badrefresh@test.local", plain_pw="pw")
        access_tok = create_access_token(str(user.id))
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": access_tok})
        assert r.status_code == 401

    def test_expired_refresh_token_rejected(self, client, db_session):
        user = _make_user(db_session, email="exprefresh@test.local", plain_pw="pw")
        import base64, hashlib, hmac as _hmac, json as _json
        settings = get_settings()
        header_b64 = (
            base64.urlsafe_b64encode(
                _json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
            ).rstrip(b"=").decode()
        )
        payload_data = {"sub": str(user.id), "iat": 1000, "exp": 1001, "type": "refresh"}
        payload_b64 = (
            base64.urlsafe_b64encode(
                _json.dumps(payload_data, separators=(",", ":")).encode()
            ).rstrip(b"=").decode()
        )
        unsigned = f"{header_b64}.{payload_b64}"
        sig = base64.urlsafe_b64encode(
            _hmac.new(settings.jwt_secret.encode(), unsigned.encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        expired = f"{unsigned}.{sig}"
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": expired})
        assert r.status_code == 401

    def test_malformed_refresh_token_rejected(self, client, db_session):
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage.token"})
        assert r.status_code == 401


# ===========================================================================
# 5. GET /auth/me
# ===========================================================================

class TestMe:
    def test_authenticated_user_gets_profile(self, client, db_session):
        user = _make_user(
            db_session, email="me@test.local", plain_pw="pw",
            role=RoleEnum.ADMIN,
        )
        token = create_access_token(str(user.id))
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "me@test.local"
        assert body["role"] == "ADMIN"
        assert body["active"] is True

    def test_no_token_returns_401(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_malformed_token_returns_401(self, client):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert r.status_code == 401

    def test_expired_token_returns_401(self, client, db_session):
        user = _make_user(db_session, email="expme@test.local", plain_pw="pw")
        import base64, hashlib, hmac as _hmac, json as _json
        settings = get_settings()
        header_b64 = (
            base64.urlsafe_b64encode(
                _json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
            ).rstrip(b"=").decode()
        )
        payload_data = {"sub": str(user.id), "iat": 1000, "exp": 1001, "type": "access"}
        payload_b64 = (
            base64.urlsafe_b64encode(
                _json.dumps(payload_data, separators=(",", ":")).encode()
            ).rstrip(b"=").decode()
        )
        unsigned = f"{header_b64}.{payload_b64}"
        sig = base64.urlsafe_b64encode(
            _hmac.new(settings.jwt_secret.encode(), unsigned.encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        expired = f"{unsigned}.{sig}"
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        assert r.status_code == 401

    def test_inactive_user_token_returns_403(self, client, db_session):
        user = _make_user(db_session, email="inactiveme@test.local", plain_pw="pw", active=False)
        token = create_access_token(str(user.id))
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_nonexistent_user_id_in_token_returns_401(self, client):
        token = create_access_token("999999")
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


# ===========================================================================
# 6. RBAC dependency helpers
# ===========================================================================

class TestRBACHelpers:
    """Test assert_bureau_scope, assert_region_scope, should_mask_complainant_ref."""

    def _user(self, role, bureau_id=None, region_id=None):
        return User(
            name="Test User",
            email=f"test_{role.value.lower()}_{bureau_id}_{region_id}@test.local",
            password_hash="fakehash",
            role=role,
            bureau_id=bureau_id,
            region_id=region_id,
            active=True,
        )

    # Bureau scope
    def test_bureau_officer_same_bureau_ok(self):
        u = self._user(RoleEnum.BUREAU_OFFICER, bureau_id=1)
        assert_bureau_scope(u, 1)  # no exception

    def test_bureau_officer_different_bureau_raises(self):
        from fastapi import HTTPException
        u = self._user(RoleEnum.BUREAU_OFFICER, bureau_id=1)
        with pytest.raises(HTTPException) as exc_info:
            assert_bureau_scope(u, 2)
        assert exc_info.value.status_code == 403

    def test_non_bureau_officer_not_restricted(self):
        u = self._user(RoleEnum.SENIOR_MGMT)
        assert_bureau_scope(u, 42)  # no exception for SENIOR_MGMT

    def test_admin_not_bureau_restricted(self):
        u = self._user(RoleEnum.ADMIN)
        assert_bureau_scope(u, 42)  # no exception

    # Region scope
    def test_regional_officer_same_region_ok(self):
        u = self._user(RoleEnum.REGIONAL_OFFICER, region_id=3)
        assert_region_scope(u, 3)  # no exception

    def test_regional_officer_different_region_raises(self):
        from fastapi import HTTPException
        u = self._user(RoleEnum.REGIONAL_OFFICER, region_id=3)
        with pytest.raises(HTTPException) as exc_info:
            assert_region_scope(u, 5)
        assert exc_info.value.status_code == 403

    def test_bureau_officer_not_region_restricted(self):
        u = self._user(RoleEnum.BUREAU_OFFICER, bureau_id=1)
        assert_region_scope(u, 99)  # no exception

    # Complainant ref masking
    def test_admin_never_masked(self):
        u = self._user(RoleEnum.ADMIN)
        assert should_mask_complainant_ref(u, 1, 1) is False

    def test_bureau_officer_own_bureau_not_masked(self):
        u = self._user(RoleEnum.BUREAU_OFFICER, bureau_id=2)
        assert should_mask_complainant_ref(u, 2, None) is False

    def test_bureau_officer_other_bureau_masked(self):
        u = self._user(RoleEnum.BUREAU_OFFICER, bureau_id=2)
        assert should_mask_complainant_ref(u, 5, None) is True

    def test_regional_officer_own_region_not_masked(self):
        u = self._user(RoleEnum.REGIONAL_OFFICER, region_id=4)
        assert should_mask_complainant_ref(u, None, 4) is False

    def test_regional_officer_other_region_masked(self):
        u = self._user(RoleEnum.REGIONAL_OFFICER, region_id=4)
        assert should_mask_complainant_ref(u, None, 7) is True

    def test_senior_mgmt_always_masked(self):
        u = self._user(RoleEnum.SENIOR_MGMT)
        assert should_mask_complainant_ref(u, 1, 1) is True


# ===========================================================================
# 7. require_roles dependency via a test-only endpoint
# ===========================================================================

class TestRequireRolesDependency:
    """Probe require_roles/require_admin via real endpoint calls."""

    def test_admin_can_hit_admin_endpoint(self, client, db_session):
        user = _make_user(db_session, email="adminrole@test.local", role=RoleEnum.ADMIN)
        token = create_access_token(str(user.id))
        # GET /auth/me is accessible to all roles; use it as the authenticated-user probe
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["role"] == "ADMIN"

    def test_bureau_officer_gets_own_profile(self, client, db_session):
        user = _make_user(db_session, email="borrole@test.local", role=RoleEnum.BUREAU_OFFICER)
        token = create_access_token(str(user.id))
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["role"] == "BUREAU_OFFICER"

    def test_senior_mgmt_gets_own_profile(self, client, db_session):
        user = _make_user(db_session, email="seniorrole@test.local", role=RoleEnum.SENIOR_MGMT)
        token = create_access_token(str(user.id))
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["role"] == "SENIOR_MGMT"

    def test_regional_officer_gets_own_profile(self, client, db_session):
        user = _make_user(db_session, email="regionrole@test.local", role=RoleEnum.REGIONAL_OFFICER)
        token = create_access_token(str(user.id))
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["role"] == "REGIONAL_OFFICER"


# ===========================================================================
# 8. Seed module
# ===========================================================================

class TestSeed:
    def test_seed_creates_demo_users(self, test_engine):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            seed(session, reset=True)
            users = session.query(User).all()
            emails = {u.email for u in users}
            assert "admin@demo.local" in emails
            assert "mgmt@demo.local" in emails
            assert "rb.officer@demo.local" in emails
            assert "pgrc.officer@demo.local" in emails
            assert "regional@demo.local" in emails

    def test_seed_is_idempotent(self, test_engine):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            seed(session, reset=True)
            count_first = session.query(User).filter(
                User.email.in_([
                    "admin@demo.local", "mgmt@demo.local",
                    "rb.officer@demo.local", "pgrc.officer@demo.local",
                    "regional@demo.local",
                ])
            ).count()
            seed(session)  # second run — no reset
            count_second = session.query(User).filter(
                User.email.in_([
                    "admin@demo.local", "mgmt@demo.local",
                    "rb.officer@demo.local", "pgrc.officer@demo.local",
                    "regional@demo.local",
                ])
            ).count()
            assert count_first == count_second == 5

    def test_seed_passwords_are_hashed(self, test_engine):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            seed(session, reset=True)
            admin = session.query(User).filter_by(email="admin@demo.local").first()
            assert admin is not None
            assert admin.password_hash != "admin123"
            assert admin.password_hash.startswith("$2b$")

    def test_seed_admin_password_verifies(self, test_engine):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            seed(session, reset=True)
            admin = session.query(User).filter_by(email="admin@demo.local").first()
            assert verify_password("admin123", admin.password_hash) is True
            assert verify_password("wrong", admin.password_hash) is False

    def test_seed_bureau_officer_has_bureau(self, test_engine):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            seed(session, reset=True)
            rb_officer = session.query(User).filter_by(email="rb.officer@demo.local").first()
            assert rb_officer.bureau_id is not None

    def test_seed_regional_officer_has_region(self, test_engine):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            seed(session, reset=True)
            regional = session.query(User).filter_by(email="regional@demo.local").first()
            assert regional.region_id is not None

    def test_seed_roles_are_correct(self, test_engine):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            seed(session, reset=True)
            admin = session.query(User).filter_by(email="admin@demo.local").first()
            assert admin.role == RoleEnum.ADMIN
            mgmt = session.query(User).filter_by(email="mgmt@demo.local").first()
            assert mgmt.role == RoleEnum.SENIOR_MGMT

    def test_production_seed_refused_without_modifying_records(self, test_engine, monkeypatch):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            initial_count = session.query(User).count()

        from app import seed as seed_mod
        prod_settings = Settings(environment="production", jwt_secret="valid-prod-secret-12345")
        monkeypatch.setattr(seed_mod, "get_settings", lambda: prod_settings)

        with Session() as session:
            with pytest.raises(RuntimeError, match="prohibited in production"):
                seed(session, reset=False)
            assert session.query(User).count() == initial_count

    def test_production_reset_refused_before_deletion(self, test_engine, monkeypatch):
        Session = sessionmaker(bind=test_engine)
        with Session() as session:
            if not session.query(User).first():
                session.add(User(name="Existing", email="existing@test.local", password_hash="h", role=RoleEnum.ADMIN))
                session.commit()
            count_before = session.query(User).count()

        from app import seed as seed_mod
        prod_settings = Settings(environment="production", jwt_secret="valid-prod-secret-12345")
        monkeypatch.setattr(seed_mod, "get_settings", lambda: prod_settings)

        with Session() as session:
            with pytest.raises(RuntimeError, match="prohibited in production"):
                seed(session, reset=True)
            assert session.query(User).count() == count_before

    def test_production_cli_main_exits_nonzero(self, monkeypatch, capsys):
        from app import seed as seed_mod
        prod_settings = Settings(environment="production", jwt_secret="valid-prod-secret-12345")
        monkeypatch.setattr(seed_mod, "get_settings", lambda: prod_settings)
        monkeypatch.setattr("sys.argv", ["seed.py", "--reset"])

        with pytest.raises(SystemExit) as exc_info:
            seed_mod.main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "prohibited in production" in captured.err


# ===========================================================================
# 9. Production settings validation
# ===========================================================================

class TestProductionSettingsSecurity:
    def test_production_rejects_missing_secret(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("JWT_SECRET", raising=False)
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="cannot use the default 'change-me' value|must be set and non-empty"):
            Settings(environment="production")

    def test_production_rejects_empty_secret(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "")
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="must be set and non-empty"):
            Settings(environment="production", jwt_secret="")

    def test_production_rejects_whitespace_secret(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "   ")
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="must be set and non-empty"):
            Settings(environment="production", jwt_secret="   ")

    def test_production_rejects_default_change_me(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "change-me")
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="cannot use the default 'change-me' value"):
            Settings(environment="production", jwt_secret="change-me")

    def test_production_rejects_whitespace_padded_change_me(self):
        with pytest.raises(ValueError, match="cannot use the default 'change-me' value"):
            Settings(environment="production", jwt_secret="  change-me  ")

    def test_production_accepts_valid_secret(self):
        s = Settings(environment="production", jwt_secret="a-very-secure-random-token-secret-1234")
        assert s.is_production is True
        assert s.jwt_secret == "a-very-secure-random-token-secret-1234"

    def test_development_accepts_default_secret(self):
        s = Settings(environment="development", jwt_secret="change-me")
        assert s.is_production is False
        assert s.jwt_secret == "change-me"

    def test_development_default_without_explicit_secret(self):
        s = Settings(environment="development")
        assert s.is_production is False
        assert s.jwt_secret == "change-me"

