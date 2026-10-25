"""Background worker — APScheduler jobs for SLA alerts and overlap scans.

Jobs:
  sla_alert_job    – runs every hour: creates DUE_SOON / OVERDUE / ESCALATION / REMINDER alerts
  overlap_scan_job – runs every 6 hours: runs AI scan and creates OVERLAP alerts

All jobs are idempotent (dedup: one alert per (case_id, type, day)).
"""
import logging
from datetime import date, datetime, time, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)


def _get_session():
    from app.database import SessionLocal, get_engine
    if SessionLocal.kw.get("bind") is None:
        SessionLocal.configure(bind=get_engine())
    return SessionLocal()


def _open_statuses():
    try:
        from app.models.enums import OPEN_CASE_STATUSES
        return list(OPEN_CASE_STATUSES)
    except Exception:
        return ["PENDING", "UNDER_PROCESS", "ESCALATED", "TRANSFERRED"]


def _alert_exists_today(db, Alert, case_id, alert_type, today: date) -> bool:
    """One alert per (case_id, type, day) — dedup rule from AGENTS.md."""
    start = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(today, time.max).replace(tzinfo=timezone.utc)
    return db.query(Alert.id).filter(
        Alert.case_id == case_id,
        Alert.type == alert_type,
        Alert.created_at >= start,
        Alert.created_at <= end,
    ).first() is not None


# ---------------------------------------------------------------------------
# SLA alert job
# ---------------------------------------------------------------------------

def sla_alert_job():
    """Create DUE_SOON, OVERDUE, REMINDER, and ESCALATION alerts for open cases."""
    db = _get_session()
    try:
        from app.models import Alert, Case, SlaRule
        from app.models.enums import AlertTypeEnum, CaseStatusEnum, RoleEnum

        today = date.today()
        now = datetime.now(timezone.utc)
        FALLBACK_DAYS = {"HIGH": 15, "MEDIUM": 30, "LOW": 45}

        rules = db.query(SlaRule).all()
        rule_map = {(r.category_id, r.priority): r for r in rules}

        open_cases = db.query(Case).filter(
            Case.status.in_(_open_statuses()),
        ).all()

        created = 0
        alerts_to_add = []

        for c in open_cases:
            prio_val = getattr(c.priority, "value", str(c.priority))
            rule = (
                rule_map.get((c.category_id, c.priority))
                or rule_map.get((None, c.priority))
            )
            days_to_dispose = rule.days_to_dispose if rule else FALLBACK_DAYS.get(prio_val, 30)
            warn_pct = rule.warn_at_pct if rule else 80
            reminder_days = rule.reminder_after_days if rule else 7
            escalate_days = rule.escalate_after_days if rule else 30

            exp_date = c.expected_disposal_on or (c.received_on + timedelta(days=days_to_dispose))
            elapsed = (today - c.received_on).days if c.received_on else 0
            remaining = (exp_date - today).days if exp_date else None

            if c.last_action_on:
                lad = c.last_action_on.date() if isinstance(c.last_action_on, datetime) else c.last_action_on
                days_since_action = (today - lad).days
            else:
                days_since_action = elapsed

            def add(atype, msg):
                nonlocal created
                if not _alert_exists_today(db, Alert, c.id, atype, today):
                    alerts_to_add.append(Alert(
                        type=atype,
                        case_id=c.id,
                        institution_id=c.institution_id,
                        target_role=RoleEnum.BUREAU_OFFICER,
                        target_bureau_id=c.bureau_id,
                        message=msg,
                        due_on=exp_date,
                        created_at=now,
                    ))
                    created += 1

            if exp_date and exp_date < today:
                overdue_days = abs((today - exp_date).days)
                add(AlertTypeEnum.OVERDUE,
                    f"Case {c.case_no} is overdue by {overdue_days} day(s) (was due {exp_date}).")
                if elapsed >= escalate_days:
                    add(AlertTypeEnum.ESCALATION,
                        f"Case {c.case_no} requires escalation: open for {elapsed} day(s).")
            else:
                total_window = (exp_date - c.received_on).days if (exp_date and c.received_on and exp_date > c.received_on) else days_to_dispose
                pct = (elapsed / total_window * 100) if total_window > 0 else 0
                if pct >= warn_pct or (remaining is not None and remaining <= 3):
                    add(AlertTypeEnum.DUE_SOON,
                        f"Case {c.case_no} is due soon on {exp_date} ({remaining} day(s) remaining).")

            if days_since_action >= reminder_days:
                add(AlertTypeEnum.REMINDER,
                    f"Case {c.case_no} has had no action for {days_since_action} day(s).")

            if elapsed >= escalate_days or getattr(c.status, "value", c.status) == "ESCALATED":
                add(AlertTypeEnum.ESCALATION,
                    f"Case {c.case_no} requires escalation: open for {elapsed} day(s).")

        if alerts_to_add:
            db.add_all(alerts_to_add)
            db.commit()
        log.info("sla_alert_job: %d alert(s) created for %d case(s)", created, len(open_cases))
    except Exception:
        db.rollback()
        log.exception("sla_alert_job failed")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Overlap scan job
# ---------------------------------------------------------------------------

def overlap_scan_job():
    """Run the AI overlap scanner and create OVERLAP alerts for new flags."""
    db = _get_session()
    try:
        from app.ai.overlap import scan_overlaps
        from app.models import Alert, OverlapFlag
        from app.models.enums import AlertTypeEnum, OverlapStateEnum, RoleEnum

        new_flags = scan_overlaps(db)
        log.info("overlap_scan_job: %d new overlap flag(s)", new_flags)

        # Create OVERLAP alerts for all open flags without a today-alert
        today = date.today()
        now = datetime.now(timezone.utc)
        open_flags = (
            db.query(OverlapFlag)
            .filter(OverlapFlag.state == OverlapStateEnum.OPEN)
            .all()
        )
        alerts_to_add = []
        for flag in open_flags:
            # Use case_a as the linked case (or None for Tier A)
            case_id = flag.case_a

            # dedup: one OVERLAP alert per flag per day (use institution_id check)
            start = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)
            end = datetime.combine(today, time.max).replace(tzinfo=timezone.utc)
            existing = db.query(Alert.id).filter(
                Alert.type == AlertTypeEnum.OVERLAP,
                Alert.institution_id == flag.institution_id,
                Alert.created_at >= start,
                Alert.created_at <= end,
            ).first()
            if existing:
                continue

            inst_name = flag.institution.name if flag.institution else f"Institution #{flag.institution_id}"
            tier_label = f"Tier {getattr(flag.tier, 'value', flag.tier)}"
            alerts_to_add.append(Alert(
                type=AlertTypeEnum.OVERLAP,
                case_id=case_id,
                institution_id=flag.institution_id,
                target_role=RoleEnum.BUREAU_OFFICER,
                target_bureau_id=None,
                message=f"{tier_label} overlap detected for {inst_name}. Coordination required.",
                due_on=None,
                created_at=now,
            ))

        if alerts_to_add:
            db.add_all(alerts_to_add)
            db.commit()
        log.info("overlap_scan_job: %d OVERLAP alert(s) created", len(alerts_to_add))
    except Exception:
        db.rollback()
        log.exception("overlap_scan_job failed")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    scheduler = BlockingScheduler(timezone="UTC")

    # SLA alerts: every hour at minute 0
    scheduler.add_job(
        sla_alert_job,
        CronTrigger(minute=0),
        id="sla_alert_job",
        name="SLA Alert Generator",
        replace_existing=True,
        misfire_grace_time=120,
    )

    # Overlap scan: every 6 hours at minute 5
    scheduler.add_job(
        overlap_scan_job,
        CronTrigger(hour="*/6", minute=5),
        id="overlap_scan_job",
        name="AI Overlap Scanner",
        replace_existing=True,
        misfire_grace_time=300,
    )

    log.info("Worker started. SLA alerts every hour, overlap scan every 6 hours.")

    # Run both jobs immediately on startup so the DB is always fresh
    sla_alert_job()
    overlap_scan_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Worker stopped.")
