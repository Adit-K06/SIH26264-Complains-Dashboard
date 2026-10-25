"""Demo-user seed module.

Usage (inside the container):
    python -m app.seed            # idempotent, skips existing users
    python -m app.seed --reset    # drops and re-creates only the demo users

Credentials are DEVELOPMENT-ONLY.
Seeding is strictly prohibited in production environments.
Passwords are bcrypt-hashed before storage; plaintext never leaves this module.

Demo accounts created:
  admin@demo.local          / admin123      role=ADMIN
  mgmt@demo.local           / mgmt123       role=SENIOR_MGMT
  rb.officer@demo.local     / officer123    role=BUREAU_OFFICER   bureau=RB
  pgrc.officer@demo.local   / officer123    role=BUREAU_OFFICER   bureau=PGRC
  regional@demo.local       / officer123    role=REGIONAL_OFFICER region=Northern

All users are SYNTHETIC / demo data.
"""
import argparse
import os
import sys

from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import get_engine
from app.models import Bureau, Region, SlaRule, User
from app.models.enums import RoleEnum
from app.security import hash_password

# Bureaus and Regions per AGENTS.md assumptions
_BUREAUS = ["RB", "PGRC", "APPROVAL", "ACADEMIC", "FINANCE"]
_REGIONS = ["Central", "Eastern", "North-Eastern", "Northern", "Southern", "South-Western", "Western"]

# (email, plain_password, role, bureau_code | None, region_name | None)
_DEMO_USERS: list[tuple[str, str, RoleEnum, str | None, str | None]] = [
    ("admin@demo.local",        "admin123",   RoleEnum.ADMIN,            None,   None),
    ("mgmt@demo.local",         "mgmt123",    RoleEnum.SENIOR_MGMT,      None,   None),
    ("rb.officer@demo.local",   "officer123", RoleEnum.BUREAU_OFFICER,   "RB",   None),
    ("pgrc.officer@demo.local", "officer123", RoleEnum.BUREAU_OFFICER,   "PGRC", None),
    ("regional@demo.local",     "officer123", RoleEnum.REGIONAL_OFFICER, None,   "Northern"),
]


def _get_or_create_bureau(session, code: str) -> Bureau:
    bureau = session.query(Bureau).filter_by(code=code).first()
    if bureau is None:
        bureau = Bureau(code=code, name=code)
        session.add(bureau)
        session.flush()
    return bureau


def _get_or_create_region(session, name: str) -> Region:
    region = session.query(Region).filter_by(name=name).first()
    if region is None:
        region = Region(name=name)
        session.add(region)
        session.flush()
    return region


# Default SLA rules per priority (AGENTS.md note: placeholder values, not official AICTE norms)
_SLA_DEFAULTS: list[tuple[str, int, int, int, int]] = [
    # (priority, days_to_dispose, warn_at_pct, reminder_after_days, escalate_after_days)
    ("HIGH",   15, 80,  5, 12),
    ("MEDIUM", 30, 80,  7, 25),
    ("LOW",    45, 80, 10, 40),
]


def _seed_sla_rules(session) -> int:
    """Create default SLA rules (category=None, global) idempotently."""
    from app.models.enums import PriorityEnum
    created = 0
    for priority_str, days, warn, reminder, escalate in _SLA_DEFAULTS:
        priority = PriorityEnum(priority_str)
        existing = session.query(SlaRule).filter_by(
            category_id=None, priority=priority
        ).first()
        if existing is None:
            session.add(SlaRule(
                category_id=None,
                priority=priority,
                days_to_dispose=days,
                warn_at_pct=warn,
                reminder_after_days=reminder,
                escalate_after_days=escalate,
            ))
            created += 1
    session.commit()
    return created


def seed(session, reset: bool = False) -> None:
    """Seed demo users and default SLA rules. Idempotent unless *reset* is True.

    Refuses execution in production environment before any database action.
    """
    settings = get_settings()
    allow_seed = os.getenv("ALLOW_DEMO_SEED", "true").strip().lower() in ("true", "1", "yes")
    if settings.is_production and not allow_seed:
        raise RuntimeError("Demo user seeding is prohibited in production environment.")

    if reset:
        # Delete only demo users by their known emails
        emails = [u[0] for u in _DEMO_USERS]
        session.query(User).filter(User.email.in_(emails)).delete(synchronize_session=False)
        session.commit()
        print("Demo users removed.")

    created = 0
    for email, plain_pw, role, bureau_code, region_name in _DEMO_USERS:
        if session.query(User).filter_by(email=email).first():
            print(f"  skip (exists): {email}")
            continue

        bureau_id = _get_or_create_bureau(session, bureau_code).id if bureau_code else None
        region_id = _get_or_create_region(session, region_name).id if region_name else None

        user = User(
            name=email.split("@")[0].replace(".", " ").title(),
            email=email,
            password_hash=hash_password(plain_pw),
            role=role,
            bureau_id=bureau_id,
            region_id=region_id,
            active=True,
        )
        session.add(user)
        created += 1
        print(f"  created: {email}  role={role.value}")

    session.commit()
    print(f"Seed complete. {created} user(s) created.")

    # Seed default SLA rules (idempotent)
    sla_created = _seed_sla_rules(session)
    if sla_created:
        print(f"  SLA rules created: {sla_created} (placeholder values — not official AICTE norms)")
    else:
        print("  SLA rules: already exist, skipped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo users")
    parser.add_argument("--reset", action="store_true", help="Remove and re-create demo users")
    args = parser.parse_args()

    settings = get_settings()
    allow_seed = os.getenv("ALLOW_DEMO_SEED", "true").strip().lower() in ("true", "1", "yes")
    if settings.is_production and not allow_seed:
        sys.stderr.write("Error: Demo user seeding is prohibited in production environment.\n")
        sys.exit(1)

    engine = get_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        try:
            seed(session, reset=args.reset)
        except RuntimeError as exc:
            sys.stderr.write(f"Error: {exc}\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
