"""SQLite schema tests and application-level append-only checks."""
from __future__ import annotations

import ast
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.db as db_module
import app.models
from app.db import Base
from app.models import Bureau, Case, CaseAction, Category, Institution, OverlapFlag, Region
from app.models.enums import ActionType, CaseStatus, Priority, Role, SourceChannel

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
EXPECTED_TABLES = {
    "regions",
    "bureaus",
    "categories",
    "institutions",
    "users",
    "sla_rules",
    "cases",
    "attachments",
    "case_actions",
    "case_links",
    "overlap_flags",
    "alerts",
    "api_keys",
}


def _sqlite_engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def sqlite_engine():
    test_engine = _sqlite_engine()

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def _add_reference_rows(session: Session):
    suffix = uuid.uuid4().hex[:10]
    region = Region(id=uuid.uuid4(), name=f"Test Region {suffix}")
    bureau = Bureau(id=uuid.uuid4(), code=f"B-{suffix}", name="Synthetic Test Bureau")
    category = Category(id=uuid.uuid4(), name=f"Test Category {suffix}")
    institution = Institution(
        id=uuid.uuid4(),
        aicte_permanent_id=f"SYN-TEST-{suffix}",
        name="Synthetic Test Institution",
        region_id=region.id,
        source="SYNTHETIC",
    )
    session.add_all([region, bureau, category])
    session.flush()
    session.add(institution)
    session.flush()
    return region, bureau, category, institution


def _add_case(session: Session, bureau: Bureau, category: Category, institution: Institution, case_no: str):
    case = Case(
        id=uuid.uuid4(),
        case_no=case_no,
        institution_id=institution.id,
        bureau_id=bureau.id,
        category_id=category.id,
        status=CaseStatus.PENDING.value,
        received_on=date(2025, 1, 1),
        priority=Priority.MEDIUM.value,
        complainant_ref="SYN-CMP-TEST",
        source_channel=SourceChannel.DIRECT.value,
        hard_deadline_type="NONE",
        summary="Synthetic schema test case.",
        source="SYNTHETIC",
        created_at=datetime(2025, 1, 1, 8, tzinfo=timezone.utc),
    )
    session.add(case)
    return case


def test_create_all_builds_the_complete_sqlite_schema(sqlite_engine):
    actual = set(inspect(sqlite_engine).get_table_names())
    assert actual == EXPECTED_TABLES


def test_startup_helper_creates_tables_from_model_metadata(monkeypatch):
    test_engine = _sqlite_engine()
    monkeypatch.setattr(db_module, "engine", test_engine)
    db_module.create_tables()
    assert set(inspect(test_engine).get_table_names()) == EXPECTED_TABLES
    test_engine.dispose()


def test_sqlite_engine_options_omit_queue_pool_overrides():
    options = db_module._engine_options("sqlite:///./aicte.db")
    assert "pool_size" not in options
    assert "max_overflow" not in options
    assert options["connect_args"] == {"check_same_thread": False}

    non_sqlite_options = db_module._engine_options("postgresql://example/db")
    assert non_sqlite_options["pool_size"] == 10
    assert non_sqlite_options["max_overflow"] == 20


def test_case_and_overlap_json_columns_use_generic_json():
    assert type(Case.__table__.c.text_vector.type) is sa.JSON
    assert type(OverlapFlag.__table__.c.reasons.type) is sa.JSON


def test_enum_values_are_available_without_database_specific_types():
    assert [role.value for role in Role] == [
        "BUREAU_OFFICER",
        "REGIONAL_OFFICER",
        "SENIOR_MGMT",
        "ADMIN",
    ]
    assert [status.value for status in CaseStatus] == [
        "PENDING",
        "UNDER_PROCESS",
        "DISPOSED",
        "TRANSFERRED",
        "ESCALATED",
    ]
    assert [priority.value for priority in Priority] == ["LOW", "MEDIUM", "HIGH"]
    assert [action.value for action in ActionType] == [
        "CREATED",
        "ASSIGNED",
        "ACTION",
        "TRANSFERRED",
        "TRANSFER_ACCEPTED",
        "TRANSFER_REJECTED",
        "ESCALATED",
        "LINKED",
        "NOTE",
        "DISPOSED",
        "REOPENED",
    ]


def test_case_number_is_unique_per_bureau(sqlite_engine):
    with Session(sqlite_engine) as session:
        _, bureau, category, institution = _add_reference_rows(session)
        session.add(_add_case(session, bureau, category, institution, "RB-TEST-001"))
        session.commit()

        session.add(_add_case(session, bureau, category, institution, "RB-TEST-001"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_institution_permanent_id_is_unique(sqlite_engine):
    with Session(sqlite_engine) as session:
        region = Region(name="Unique ID Region")
        session.add(region)
        session.flush()
        permanent_id = f"SYN-{uuid.uuid4().hex[:12]}"
        session.add(
            Institution(
                aicte_permanent_id=permanent_id,
                name="Synthetic Institution A",
                region_id=region.id,
                source="SYNTHETIC",
            )
        )
        session.commit()
        session.add(
            Institution(
                aicte_permanent_id=permanent_id,
                name="Synthetic Institution B",
                region_id=region.id,
                source="SYNTHETIC",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_case_actions_allow_inserts(sqlite_engine):
    with Session(sqlite_engine) as session:
        _, bureau, category, institution = _add_reference_rows(session)
        case = _add_case(session, bureau, category, institution, "RB-TEST-ACTION-001")
        session.flush()
        session.add(
            CaseAction(
                id=uuid.uuid4(),
                case_id=case.id,
                actor_id=None,
                bureau_id=bureau.id,
                action_type=ActionType.CREATED.value,
                from_status=None,
                to_status=CaseStatus.PENDING.value,
                remarks="Initial synthetic action.",
            )
        )
        session.commit()
        assert session.scalar(select(sa.func.count()).select_from(CaseAction)) == 1


def test_case_actions_reject_object_and_sql_mutations(sqlite_engine):
    with Session(sqlite_engine) as session:
        _, bureau, category, institution = _add_reference_rows(session)
        case = _add_case(session, bureau, category, institution, "RB-TEST-ACTION-002")
        session.flush()
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            bureau_id=bureau.id,
            action_type=ActionType.CREATED.value,
            to_status=CaseStatus.PENDING.value,
            remarks="Keep this history row.",
        )
        session.add(action)
        session.commit()
        action_id = action.id

        action.remarks = "Attempted ORM mutation."
        with pytest.raises(ValueError, match="append-only"):
            session.flush()
        session.rollback()

        with pytest.raises(ValueError, match="append-only"):
            session.execute(
                sa.update(CaseAction)
                .where(CaseAction.id == action_id)
                .values(remarks="Attempted bulk mutation.")
            )
        session.rollback()

        with pytest.raises(ValueError, match="append-only"):
            session.execute(sa.delete(CaseAction).where(CaseAction.id == action_id))
        session.rollback()

        persisted = session.get(CaseAction, action_id)
        assert persisted is not None
        assert persisted.remarks == "Keep this history row."


def test_application_code_has_no_case_action_update_or_delete_paths():
    sql_mutation = re.compile(
        r"\bUPDATE\s+(?:[\w\"\[\]]+\.)?[\"\[]?case_actions[\"\]]?\b"
        r"|\bDELETE\s+FROM\s+(?:[\w\"\[\]]+\.)?[\"\[]?case_actions[\"\]]?\b",
        re.IGNORECASE,
    )
    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if sql_mutation.search(source):
            violations.append(f"{path}: direct SQL mutation")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            else:
                function_name = ""
            if function_name not in {"update", "delete"}:
                continue
            fragments = [ast.unparse(argument).lower() for argument in node.args]
            if isinstance(node.func, ast.Attribute):
                fragments.append(ast.unparse(node.func.value).lower())
            if any("caseaction" in fragment or "case_actions" in fragment for fragment in fragments):
                violations.append(f"{path}:{node.lineno}: ORM mutation")
    assert violations == []