"""Python enums — EXACT strings from AGENTS.md ENUMS section.

Each enum also has a paired SQLAlchemy Enum column type (create_type=False
because the PG ENUM types are created explicitly in migration 0001).
"""
from __future__ import annotations

import enum

import sqlalchemy as sa


# ── Role ─────────────────────────────────────────────────────────────────────
class Role(str, enum.Enum):
    BUREAU_OFFICER = "BUREAU_OFFICER"
    REGIONAL_OFFICER = "REGIONAL_OFFICER"
    SENIOR_MGMT = "SENIOR_MGMT"
    ADMIN = "ADMIN"


# ── CaseStatus ───────────────────────────────────────────────────────────────
class CaseStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_PROCESS = "UNDER_PROCESS"
    DISPOSED = "DISPOSED"
    TRANSFERRED = "TRANSFERRED"
    ESCALATED = "ESCALATED"


# ── Priority ─────────────────────────────────────────────────────────────────
class Priority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ── SourceChannel ────────────────────────────────────────────────────────────
class SourceChannel(str, enum.Enum):
    DIRECT = "DIRECT"
    CPGRAMS = "CPGRAMS"
    ANTI_RAGGING_PORTAL = "ANTI_RAGGING_PORTAL"
    COURT = "COURT"
    PARLIAMENT_QUESTION = "PARLIAMENT_QUESTION"
    RTI = "RTI"
    VIP_REFERENCE = "VIP_REFERENCE"
    CSV_IMPORT = "CSV_IMPORT"
    API = "API"


# ── HardDeadlineType ─────────────────────────────────────────────────────────
class HardDeadlineType(str, enum.Enum):
    CPGRAMS_21D = "CPGRAMS_21D"
    COURT_ORDER = "COURT_ORDER"
    PARLIAMENT_QUESTION = "PARLIAMENT_QUESTION"
    RTI_30D = "RTI_30D"
    VIP_REFERENCE = "VIP_REFERENCE"
    NONE = "NONE"


# ── ActionType ───────────────────────────────────────────────────────────────
class ActionType(str, enum.Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    ACTION = "ACTION"
    TRANSFERRED = "TRANSFERRED"
    TRANSFER_ACCEPTED = "TRANSFER_ACCEPTED"
    TRANSFER_REJECTED = "TRANSFER_REJECTED"
    ESCALATED = "ESCALATED"
    LINKED = "LINKED"
    NOTE = "NOTE"
    DISPOSED = "DISPOSED"
    REOPENED = "REOPENED"


# ── ActionTag ────────────────────────────────────────────────────────────────
class ActionTag(str, enum.Enum):
    SHOW_CAUSE_NOTICE = "SHOW_CAUSE_NOTICE"
    INSPECTION_ORDERED = "INSPECTION_ORDERED"
    HEARING_SCHEDULED = "HEARING_SCHEDULED"
    CLARIFICATION_SOUGHT = "CLARIFICATION_SOUGHT"
    REPLY_RECEIVED = "REPLY_RECEIVED"
    PENALTY_PROPOSED = "PENALTY_PROPOSED"
    OTHER = "OTHER"


# ── OverlapTier ──────────────────────────────────────────────────────────────
class OverlapTier(str, enum.Enum):
    A = "A"
    B = "B"


# ── OverlapState ─────────────────────────────────────────────────────────────
class OverlapState(str, enum.Enum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"


# ── LinkType ─────────────────────────────────────────────────────────────────
class LinkType(str, enum.Enum):
    CROSS_BUREAU = "CROSS_BUREAU"
    SAME_BUREAU_DUPLICATE = "SAME_BUREAU_DUPLICATE"


# ── AlertType ────────────────────────────────────────────────────────────────
class AlertType(str, enum.Enum):
    OVERLAP = "OVERLAP"
    DUPLICATE = "DUPLICATE"
    REMINDER = "REMINDER"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"
    ESCALATION = "ESCALATION"
    HARD_DEADLINE = "HARD_DEADLINE"
    TRANSFER_UNACKED = "TRANSFER_UNACKED"


# ── SA column types (create_type=False — PG types created in migration 0001) ──
role_col = sa.Enum(Role, name="role", create_type=False)
case_status_col = sa.Enum(CaseStatus, name="case_status", create_type=False)
priority_col = sa.Enum(Priority, name="priority", create_type=False)
source_channel_col = sa.Enum(SourceChannel, name="source_channel", create_type=False)
hard_deadline_type_col = sa.Enum(HardDeadlineType, name="hard_deadline_type", create_type=False)
action_type_col = sa.Enum(ActionType, name="action_type", create_type=False)
action_tag_col = sa.Enum(ActionTag, name="action_tag", create_type=False)
overlap_tier_col = sa.Enum(OverlapTier, name="overlap_tier", create_type=False)
overlap_state_col = sa.Enum(OverlapState, name="overlap_state", create_type=False)
link_type_col = sa.Enum(LinkType, name="link_type", create_type=False)
alert_type_col = sa.Enum(AlertType, name="alert_type", create_type=False)
