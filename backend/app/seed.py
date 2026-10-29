"""Create the deterministic synthetic demo dataset with python -m app.seed."""
from __future__ import annotations

import argparse
import csv
import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import func, select

from app.db import Base, SessionLocal, create_tables, engine
from app.models import Bureau, Case, CaseAction, Category, Institution, OverlapFlag, Region, SlaRule, User
from app.models.enums import ActionType, CaseStatus, HardDeadlineType, OverlapState, OverlapTier, Priority, Role, SourceChannel

SEED = 42
SEED_TODAY = date(2026, 10, 29)  # fixed anchor for reproducible 12-month sample
SOURCE = "SYNTHETIC"
PASSWORD = "Demo@12345"
NAMESPACE = uuid.UUID("5a7558a1-87d6-4bf9-982f-7c301e56e219")
PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")

BUREAUS = (
    ("RB", "Regional Bureau"),
    ("PGRC", "Public Grievance Redressal Cell"),
    ("APPROVAL", "Approval Bureau"),
    ("ACADEMIC", "Academic Bureau"),
    ("FINANCE", "Finance Bureau"),
)
REGIONS = ("North", "South", "East", "West", "Central", "North-East", "Union Territories")
CATEGORIES = (
    "Admissions",
    "Examination Services",
    "Faculty",
    "Infrastructure",
    "Scholarships",
    "Approval Process",
    "Other",
)
LABEL_FIELDS = ("case_a_id", "case_b_id", "case_a_no", "case_b_no", "label", "split", "kind", "source")
OPEN_STATUSES = {
    CaseStatus.PENDING.value,
    CaseStatus.UNDER_PROCESS.value,
    CaseStatus.TRANSFERRED.value,
    CaseStatus.ESCALATED.value,
}
POSITIVE_ISSUES = (
    (0, "Students reported delayed merit scholarship payments for the current academic year.", "A complaint says merit scholarship funds for this academic year remain pending."),
    (1, "Applicants reported an admission fee mismatch against the published schedule.", "Students requested review of charges that differ from the admission fee schedule."),
    (2, "Students requested correction of examination results for the recent semester.", "A complaint asks the bureau to review recent semester examination result errors."),
    (3, "Students reported unsafe laboratory equipment and requested an inspection.", "A complaint asks for inspection of laboratory equipment reported as unsafe."),
    (4, "Residents reported interrupted hostel water supply and requested a review.", "A complaint describes repeated hostel water interruptions and asks for review."),
    (5, "The institution requested a status update on its pending approval application.", "A complaint asks about the delayed decision on an approval application."),
    (6, "Students reported unfilled teaching posts in a programme and requested review.", "A complaint asks the bureau to review reported teaching vacancies in a programme."),
    (0, "Applicants reported that submitted scholarship documents were not reviewed.", "A complaint says scholarship applications remain pending despite document submission."),
    (1, "Applicants requested correction of errors in their admission records.", "A complaint asks for review of incorrect admission record details."),
    (2, "Students reported conflicting examination schedule notices for the semester.", "A complaint requests clarification because semester examination notices conflict."),
    (3, "Students reported that an accessible campus route is unavailable.", "A complaint requests review of the missing accessible route on campus."),
    (5, "The institution reported that its approval portal submission has no status update.", "A complaint asks for an update on the institution approval portal submission."),
)
HARD_NEGATIVE_TOPICS = (
    ("admission document review", "laboratory equipment repair"),
    ("semester exam timetable", "hostel meal service"),
    ("faculty appointment records", "scholarship payment status"),
    ("campus access route", "student fee receipt correction"),
    ("approval portal access", "library opening hours"),
    ("examination answer sheet copy", "water supply maintenance"),
    ("admission waitlist clarification", "staff attendance records"),
    ("student aid eligibility", "classroom projector repair"),
    ("course transfer request", "parking permit renewal"),
    ("faculty workload review", "transcript delivery delay"),
    ("hostel room allocation", "approval application receipt"),
    ("exam result publication", "campus sanitation schedule"),
    ("fee refund processing", "faculty qualification records"),
    ("accessibility ramp request", "scholarship bank detail update"),
    ("admission counselling notice", "laboratory inventory update"),
)
NEAR_DUPLICATE_TOPICS = (
    "student transcript verification",
    "admission record correction",
    "semester result review",
    "scholarship form status",
    "laboratory access schedule",
)


def stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


def utc_at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)


def write_labels(labels: list[dict[str, str]]) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "data" / "labels.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(labels)
    return path


def record_label(labels, case_a, case_b, label: int, kind: str, index: int) -> None:
    labels.append(
        {
            "case_a_id": str(case_a.id),
            "case_b_id": str(case_b.id),
            "case_a_no": case_a.case_no,
            "case_b_no": case_b.case_no,
            "label": str(label),
            "split": "test" if index % 5 == 0 else "train",
            "kind": kind,
            "source": SOURCE,
        }
    )


def add_case(
    session,
    counters: dict[str, int],
    today: date,
    institution: Institution,
    bureau: Bureau,
    category: Category,
    actor_id: uuid.UUID,
    received_on: date,
    status: str,
    priority: str,
    summary: str,
    complainant_ref: str,
    source_channel: str,
) -> Case:
    counters[bureau.code] += 1
    case_no = f"{bureau.code}-{received_on.year}-{counters[bureau.code]:05d}"
    case_id = stable_id("case", case_no)
    age_days = max(0, (today - received_on).days)

    action_specs = [
        (ActionType.CREATED.value, None, CaseStatus.PENDING.value, "Synthetic demo complaint recorded.", 0, 8)
    ]
    if status == CaseStatus.UNDER_PROCESS.value:
        action_specs.append(
            (ActionType.ACTION.value, CaseStatus.PENDING.value, CaseStatus.UNDER_PROCESS.value, "Initial review started.", min(1, age_days), 11)
        )
    elif status == CaseStatus.DISPOSED.value:
        action_specs.extend(
            [
                (ActionType.ACTION.value, CaseStatus.PENDING.value, CaseStatus.UNDER_PROCESS.value, "Initial review started.", min(1, age_days), 11),
                (ActionType.DISPOSED.value, CaseStatus.UNDER_PROCESS.value, CaseStatus.DISPOSED.value, "Disposed in synthetic demo history.", min(5, age_days), 15),
            ]
        )
    elif status == CaseStatus.TRANSFERRED.value:
        action_specs.append(
            (ActionType.TRANSFERRED.value, CaseStatus.PENDING.value, CaseStatus.TRANSFERRED.value, "Transferred for synthetic coordination.", min(2, age_days), 13)
        )
    elif status == CaseStatus.ESCALATED.value:
        action_specs.append(
            (ActionType.ESCALATED.value, CaseStatus.PENDING.value, CaseStatus.ESCALATED.value, "Escalated in synthetic demo history.", min(2, age_days), 13)
        )

    action_times = []
    for index, (action_type, from_status, to_status, remarks, offset, hour) in enumerate(action_specs):
        action_time = utc_at(received_on + timedelta(days=min(offset, age_days)), hour)
        action_times.append(action_time)
        session.add(
            CaseAction(
                id=stable_id("action", f"{case_no}:{index}"),
                case_id=case_id,
                actor_id=actor_id,
                bureau_id=bureau.id,
                action_type=action_type,
                from_status=from_status,
                to_status=to_status,
                remarks=remarks,
                created_at=action_time,
            )
        )

    case = Case(
        id=case_id,
        case_no=case_no,
        institution_id=institution.id,
        bureau_id=bureau.id,
        category_id=category.id,
        status=status,
        assigned_officer_id=actor_id,
        received_on=received_on,
        last_action_on=action_times[-1],
        last_action_text=action_specs[-1][3],
        next_action_text="Review submissions and coordinate next steps." if status != CaseStatus.DISPOSED.value else None,
        expected_disposal_on=received_on + timedelta(days=30),
        priority=priority,
        summary=summary,
        complainant_ref=complainant_ref,
        source_channel=source_channel,
        hard_deadline_on=None,
        hard_deadline_type=HardDeadlineType.NONE.value,
        link_group_id=None,
        needs_institution_review=institution.name.startswith("Demo Inst."),
        text_vector=None,
        source=SOURCE,
        created_at=utc_at(received_on, 8),
    )
    session.add(case)
    return case


def seed_database(reset: bool = False) -> None:
    rng = random.Random(SEED)
    today = SEED_TODAY
    if reset:
        Base.metadata.drop_all(bind=engine)
    create_tables()

    with SessionLocal() as session:
        existing = session.scalar(select(func.count()).select_from(Institution)) or 0
        if existing and not reset:
            print(f"Database already has {existing} institutions; left unchanged. Use --reset to rebuild.")
            return

        regions = [Region(id=stable_id("region", name), name=name) for name in REGIONS]
        region_by_name = {row.name: row for row in regions}
        bureaus = [Bureau(id=stable_id("bureau", code), code=code, name=name) for code, name in BUREAUS]
        bureau_by_code = {row.code: row for row in bureaus}
        categories = [Category(id=stable_id("category", name), name=name) for name in CATEGORIES]
        category_by_name = {row.name: row for row in categories}
        session.add_all([*regions, *bureaus, *categories])
        session.flush()

        definitions = (
            ("admin", "Demo Administrator", Role.ADMIN.value, None, None),
            ("senior", "Demo Senior Manager", Role.SENIOR_MGMT.value, None, None),
            ("rb_officer", "Demo RB Officer", Role.BUREAU_OFFICER.value, bureau_by_code["RB"].id, None),
            ("pgrc_officer", "Demo PGRC Officer", Role.BUREAU_OFFICER.value, bureau_by_code["PGRC"].id, None),
            ("regional_north", "Demo North Regional Officer", Role.REGIONAL_OFFICER.value, None, region_by_name["North"].id),
        )
        password_hash = PASSWORD_CONTEXT.hash(PASSWORD, salt="C6UzMDM.H6dfI/f/IKcEe.")
        users = [
            User(
                id=stable_id("user", username),
                name=name,
                email=f"{username}@demo.aicte.invalid",
                password_hash=password_hash,
                role=role,
                bureau_id=bureau_id,
                region_id=region_id,
                active=True,
            )
            for username, name, role, bureau_id, region_id in definitions
        ]
        user_by_name = {definitions[index][0]: user for index, user in enumerate(users)}
        priorities = (Priority.LOW.value, Priority.MEDIUM.value, Priority.HIGH.value)
        sla_rules = [
            SlaRule(
                id=stable_id("sla", priority),
                category_id=None,
                priority=priority,
                days_to_dispose=30,
                warn_at_pct=0.75,
                reminder_after_days=7,
                escalate_after_days=10,
            )
            for priority in priorities
        ]
        session.add_all([*users, *sla_rules])
        session.flush()

        descriptors = (
            "Aster", "Blue Cedar", "Cobalt", "Dawnridge", "Evergreen", "Foxglove",
            "Granite Bay", "Harborview", "Indigo", "Juniper", "Keystone", "Larkspur",
            "Maple Crest", "Northwind", "Oak Valley", "Pinebridge", "Quartz Hill",
            "Redwood", "Silver Fern", "Topaz", "Umber", "Valleybrook", "Willowbend",
            "Xenia", "Yellowstone", "Zephyr", "Amberfield", "Brightwater",
            "Clearbrook", "Driftwood", "Elmstone", "Fairhaven",
        )
        suffixes = (
            "Institute of Engineering",
            "College of Applied Technology",
            "Technical University",
            "Polytechnic Institute",
        )
        messy_names = (
            "Demo Inst. of Engg & Tech - Unit 33",
            "Demo Tech. Coll. (Unit 34)",
            "Demo Univ. Institute of Engg. (Unit 35)",
            "Demo Instt of Technology - Unit 36",
            "Demo College of Engg & Applied Tech - Unit 37",
            "Demo Inst. of Tech., Unit 38",
            "Demo Univ. Coll. of Engineering - Unit 39",
            "Demo Institute, Engg. & Tech Unit 40",
        )
        institutions = []
        institution_by_number = {}
        for number in range(1, 41):
            region_name = REGIONS[(number - 1) % len(REGIONS)]
            if number <= 32:
                name = f"Synthetic {descriptors[number - 1]} {suffixes[(number - 1) % len(suffixes)]} {number:02d}"
            else:
                name = messy_names[number - 33]
            institution = Institution(
                id=stable_id("institution", f"SYN-{number:05d}"),
                aicte_permanent_id=f"SYN-{number:05d}",
                name=name,
                address=f"Synthetic Campus {number:02d}, {region_name}",
                district=f"Demo District {(number - 1) % 20 + 1:02d}",
                state=region_name,
                region_id=region_by_name[region_name].id,
                type=suffixes[(number - 1) % len(suffixes)],
                status="ACTIVE",
                source=SOURCE,
            )
            institutions.append(institution)
            institution_by_number[number] = institution
        session.add_all(institutions)
        session.flush()

        counters = {code: 0 for code, _ in BUREAUS}
        all_cases = []
        labels: list[dict[str, str]] = []
        positive_pairs = []
        officer_by_bureau = {
            "RB": user_by_name["rb_officer"].id,
            "PGRC": user_by_name["pgrc_officer"].id,
        }
        direct = SourceChannel.DIRECT.value
        for index, (category_index, summary_a, summary_b) in enumerate(POSITIVE_ISSUES):
            institution = institution_by_number[index + 1]
            category = category_by_name[CATEGORIES[category_index]]
            reference = f"SYN-REF-{index + 1:04d}"
            complainant = f"SYN-CMP-{index + 1:04d}"
            offset = 15 + index * 2
            case_a = add_case(
                session, counters, today, institution, bureau_by_code["RB"], category,
                officer_by_bureau["RB"], today - timedelta(days=offset),
                CaseStatus.PENDING.value, Priority.MEDIUM.value,
                f"{summary_a} Synthetic reference {reference}.", complainant, direct,
            )
            case_b = add_case(
                session, counters, today, institution, bureau_by_code["PGRC"], category,
                officer_by_bureau["PGRC"], today - timedelta(days=offset - 4),
                CaseStatus.UNDER_PROCESS.value, Priority.MEDIUM.value,
                f"{summary_b} Reference {reference}.", complainant, SourceChannel.CPGRAMS.value,
            )
            all_cases.extend((case_a, case_b))
            positive_pairs.append((case_a, case_b))
            labels.append(
                {
                    "case_a_id": str(case_a.id),
                    "case_b_id": str(case_b.id),
                    "case_a_no": case_a.case_no,
                    "case_b_no": case_b.case_no,
                    "label": "1",
                    "split": "test" if index % 5 == 0 else "train",
                    "kind": "planted_overlap",
                    "source": SOURCE,
                }
            )

        negative_pairs = []
        for index, (topic_a, topic_b) in enumerate(HARD_NEGATIVE_TOPICS):
            institution = institution_by_number[13 + index]
            category_a = category_by_name[CATEGORIES[index % len(CATEGORIES)]]
            category_b = category_by_name[CATEGORIES[(index + 3) % len(CATEGORIES)]]
            offset = 70 + index * 2
            case_a = add_case(
                session, counters, today, institution, bureau_by_code["RB"], category_a,
                officer_by_bureau["RB"], today - timedelta(days=offset),
                CaseStatus.PENDING.value, Priority.LOW.value,
                f"Students at this synthetic institution requested bureau review of {topic_a} for the current academic year. Internal reference SYN-NEG-{index + 1:04d}A.",
                f"SYN-CMP-NEG-A-{index + 1:03d}", direct,
            )
            case_b = add_case(
                session, counters, today, institution, bureau_by_code["PGRC"], category_b,
                officer_by_bureau["PGRC"], today - timedelta(days=offset - 2),
                CaseStatus.UNDER_PROCESS.value, Priority.HIGH.value,
                f"Students at this synthetic institution requested bureau review of {topic_b} for the current academic year. Internal reference SYN-NEG-{index + 1:04d}B.",
                f"SYN-CMP-NEG-B-{index + 1:03d}", SourceChannel.CSV_IMPORT.value,
            )
            all_cases.extend((case_a, case_b))
            negative_pairs.append((case_a, case_b))
            labels.append(
                {
                    "case_a_id": str(case_a.id),
                    "case_b_id": str(case_b.id),
                    "case_a_no": case_a.case_no,
                    "case_b_no": case_b.case_no,
                    "label": "0",
                    "split": "test" if index % 5 == 0 else "train",
                    "kind": "hard_negative",
                    "source": SOURCE,
                }
            )

        same_bureau_pairs = []
        for index, topic in enumerate(NEAR_DUPLICATE_TOPICS):
            institution = institution_by_number[28 + index]
            category = category_by_name[CATEGORIES[index % len(CATEGORIES)]]
            offset = 120 + index * 7
            case_a = add_case(
                session, counters, today, institution, bureau_by_code["RB"], category,
                officer_by_bureau["RB"], today - timedelta(days=offset),
                CaseStatus.UNDER_PROCESS.value, Priority.MEDIUM.value,
                f"Students requested review of {topic} records at the synthetic institution.",
                f"SYN-CMP-DUP-A-{index + 1:03d}", direct,
            )
            case_b = add_case(
                session, counters, today, institution, bureau_by_code["RB"], category,
                officer_by_bureau["RB"], today - timedelta(days=offset - 3),
                CaseStatus.PENDING.value, Priority.MEDIUM.value,
                f"Students asked the bureau to check the {topic} records at this synthetic institution.",
                f"SYN-CMP-DUP-B-{index + 1:03d}", SourceChannel.API.value,
            )
            all_cases.extend((case_a, case_b))
            same_bureau_pairs.append((case_a, case_b))
            labels.append(
                {
                    "case_a_id": str(case_a.id),
                    "case_b_id": str(case_b.id),
                    "case_a_no": case_a.case_no,
                    "case_b_no": case_b.case_no,
                    "label": "0",
                    "split": "test" if index % 5 == 0 else "train",
                    "kind": "same_bureau_near_duplicate",
                    "source": SOURCE,
                }
            )

        filler_topics = (
            "a synthetic admission record question",
            "a synthetic examination service request",
            "a synthetic faculty information concern",
            "a synthetic campus maintenance request",
            "a synthetic scholarship processing question",
            "a synthetic approval status request",
            "a synthetic student service concern",
        )
        filler_count = 300 - len(all_cases)
        for index in range(filler_count):
            if index < 7:
                institution_number = 33 + index
            elif index == 7:
                institution_number = 40
            else:
                institution_number = rng.randint(1, 39)
            if index < len(BUREAUS):
                bureau_code = BUREAUS[index][0]
            elif index == 7:
                bureau_code = "PGRC"
            else:
                bureau_code = rng.choice([code for code, _ in BUREAUS])
            if institution_number == 40:
                bureau_code = "PGRC"
            status = rng.choices(
                [item.value for item in CaseStatus],
                weights=(28, 34, 24, 8, 6),
                k=1,
            )[0]
            age = rng.randint(0, 365)
            if status == CaseStatus.DISPOSED.value:
                age = max(age, 5)
            institution = institution_by_number[institution_number]
            bureau = bureau_by_code[bureau_code]
            actor = officer_by_bureau.get(bureau_code, user_by_name["admin"].id)
            case = add_case(
                session, counters, today, institution, bureau, rng.choice(categories),
                actor, today - timedelta(days=age), status, rng.choice(tuple(p.value for p in Priority)),
                f"{rng.choice(filler_topics).capitalize()} reported for {institution.name}; synthetic case for dashboard demonstration.",
                f"SYN-CMP-FILL-{index + 1:04d}",
                rng.choice(tuple(channel.value for channel in SourceChannel)),
            )
            all_cases.append(case)

        session.flush()
        open_bureaus_by_institution = {}
        cases_by_institution = {}
        for case in all_cases:
            cases_by_institution.setdefault(case.institution_id, []).append(case)
            if case.status in OPEN_STATUSES:
                open_bureaus_by_institution.setdefault(case.institution_id, set()).add(case.bureau_id)

        tier_a_count = 0
        for institution_id, bureau_ids in open_bureaus_by_institution.items():
            if len(bureau_ids) < 2:
                continue
            oldest = min(case.received_on for case in cases_by_institution[institution_id])
            session.add(
                OverlapFlag(
                    id=stable_id("overlap-a", str(institution_id)),
                    institution_id=institution_id,
                    case_a=None,
                    case_b=None,
                    tier=OverlapTier.A.value,
                    score=None,
                    reasons=["DIFFERENT_BUREAU"],
                    state=OverlapState.OPEN.value,
                    created_at=utc_at(oldest, 16),
                )
            )
            tier_a_count += 1

        for case_a, case_b in positive_pairs:
            session.add(
                OverlapFlag(
                    id=stable_id("overlap-b", f"{case_a.id}:{case_b.id}"),
                    institution_id=case_a.institution_id,
                    case_a=case_a.id,
                    case_b=case_b.id,
                    tier=OverlapTier.B.value,
                    score=None,
                    reasons=[
                        "HIGH_TEXT_SIMILARITY",
                        "SAME_CATEGORY",
                        "WITHIN_30_DAYS",
                        "SHARED_REFERENCE",
                        "SHARED_COMPLAINANT_REF",
                        "DIFFERENT_BUREAU",
                    ],
                    state=OverlapState.OPEN.value,
                    created_at=utc_at(max(case_a.received_on, case_b.received_on), 16),
                )
            )

        session.commit()
        counts = {
            "users": session.scalar(select(func.count()).select_from(User)) or 0,
            "institutions": session.scalar(select(func.count()).select_from(Institution)) or 0,
            "cases": session.scalar(select(func.count()).select_from(Case)) or 0,
            "case_actions": session.scalar(select(func.count()).select_from(CaseAction)) or 0,
            "sla_rules": session.scalar(select(func.count()).select_from(SlaRule)) or 0,
            "overlap_flags": session.scalar(select(func.count()).select_from(OverlapFlag)) or 0,
        }

    labels_path = write_labels(labels)
    train_count = sum(row["split"] == "train" for row in labels)
    test_count = len(labels) - train_count
    print(
        f"Seed complete (seed={SEED}, source={SOURCE}): "
        f"bureaus={len(BUREAUS)}, regions={len(REGIONS)}, categories={len(CATEGORIES)}, "
        f"sla_rules={counts['sla_rules']}, users={counts['users']}, "
        f"institutions={counts['institutions']}, cases={counts['cases']}, "
        f"case_actions={counts['case_actions']}, overlap_flags={counts['overlap_flags']} "
        f"(tier_a={tier_a_count}, tier_b={len(positive_pairs)}), "
        f"labels={len(labels)} (train={train_count}, test={test_count})."
    )
    print(f"Labels written to {labels_path.relative_to(Path(__file__).resolve().parents[2])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic synthetic AICTE demo data.")
    parser.add_argument("--reset", action="store_true", help="drop and recreate all mapped tables")
    args = parser.parse_args()
    seed_database(reset=args.reset)


if __name__ == "__main__":
    main()