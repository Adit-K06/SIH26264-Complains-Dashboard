"""Domain enums strictly matching AGENTS.md."""
import enum


class RoleEnum(str, enum.Enum):
    BUREAU_OFFICER = "BUREAU_OFFICER"
    REGIONAL_OFFICER = "REGIONAL_OFFICER"
    SENIOR_MGMT = "SENIOR_MGMT"
    ADMIN = "ADMIN"


class CaseStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_PROCESS = "UNDER_PROCESS"
    DISPOSED = "DISPOSED"
    TRANSFERRED = "TRANSFERRED"
    ESCALATED = "ESCALATED"


class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ActionTypeEnum(str, enum.Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    ACTION = "ACTION"
    TRANSFERRED = "TRANSFERRED"
    ESCALATED = "ESCALATED"
    LINKED = "LINKED"
    NOTE = "NOTE"
    DISPOSED = "DISPOSED"
    REOPENED = "REOPENED"


class OverlapTierEnum(str, enum.Enum):
    A = "A"
    B = "B"


class OverlapStateEnum(str, enum.Enum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"


class AlertTypeEnum(str, enum.Enum):
    OVERLAP = "OVERLAP"
    REMINDER = "REMINDER"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"
    ESCALATION = "ESCALATION"


class ReasonCodeEnum(str, enum.Enum):
    HIGH_TEXT_SIMILARITY = "HIGH_TEXT_SIMILARITY"
    SAME_CATEGORY = "SAME_CATEGORY"
    WITHIN_30_DAYS = "WITHIN_30_DAYS"
    SHARED_REFERENCE = "SHARED_REFERENCE"
    SHARED_COMPLAINANT_REF = "SHARED_COMPLAINANT_REF"
    DIFFERENT_BUREAU = "DIFFERENT_BUREAU"


OPEN_CASE_STATUSES = frozenset({
    CaseStatusEnum.PENDING,
    CaseStatusEnum.UNDER_PROCESS,
    CaseStatusEnum.ESCALATED,
    CaseStatusEnum.TRANSFERRED,
})
