"""models package — imports all ORM models so SQLAlchemy discovers them.

Import order matters: leaf tables first, then tables that reference them.
"""
from app.models.enums import (  # noqa: F401
    ActionTag,
    ActionType,
    AlertType,
    CaseStatus,
    HardDeadlineType,
    LinkType,
    OverlapState,
    OverlapTier,
    Priority,
    Role,
    SourceChannel,
    action_tag_col,
    action_type_col,
    alert_type_col,
    case_status_col,
    hard_deadline_type_col,
    link_type_col,
    overlap_state_col,
    overlap_tier_col,
    priority_col,
    role_col,
    source_channel_col,
)
from app.models.base import Base  # noqa: F401

# Reference tables (no FK deps)
from app.models.region import Region  # noqa: F401
from app.models.bureau import Bureau  # noqa: F401
from app.models.category import Category  # noqa: F401

# Tables with FK deps
from app.models.institution import Institution  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.sla_rule import SlaRule  # noqa: F401

# Core case tables
from app.models.case import Case  # noqa: F401
from app.models.attachment import Attachment  # noqa: F401
from app.models.case_action import CaseAction  # noqa: F401
from app.models.case_link import CaseLink  # noqa: F401

# Overlap / alert
from app.models.overlap_flag import OverlapFlag  # noqa: F401
from app.models.alert import Alert  # noqa: F401

# API access
from app.models.api_key import ApiKey  # noqa: F401

__all__ = [
    "Base",
    # enums
    "Role", "CaseStatus", "Priority", "SourceChannel", "HardDeadlineType",
    "ActionType", "ActionTag", "OverlapTier", "OverlapState", "LinkType", "AlertType",
    # models
    "Region", "Bureau", "Category", "Institution", "User", "SlaRule",
    "Case", "Attachment", "CaseAction", "CaseLink", "OverlapFlag", "Alert", "ApiKey",
]
