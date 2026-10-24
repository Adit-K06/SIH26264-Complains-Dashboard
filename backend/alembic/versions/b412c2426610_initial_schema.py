"""Initial database schema with all 13 core tables, constraints, and indexes.

Revision ID: b412c2426610
Revises: 
Create Date: 2026-10-24 16:24:46.677805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b412c2426610'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. PostgreSQL specific extensions
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Independent dimension tables
    op.create_table(
        'bureaus',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bureaus_code'), 'bureaus', ['code'], unique=True)

    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=True)

    op.create_table(
        'regions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_regions_name'), 'regions', ['name'], unique=True)

    # 3. Tables dependent on regions / bureaus
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bureau_id', sa.Integer(), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['bureau_id'], ['bureaus.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_api_keys_bureau_id'), 'api_keys', ['bureau_id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)

    op.create_table(
        'institutions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('aicte_permanent_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('region_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['region_id'], ['regions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_institutions_aicte_permanent_id'), 'institutions', ['aicte_permanent_id'], unique=True)
    op.create_index(op.f('ix_institutions_name'), 'institutions', ['name'], unique=False)
    op.create_index('ix_institutions_name_trgm', 'institutions', ['name'], unique=False, postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('ix_institutions_region_id', 'institutions', ['region_id'], unique=False)

    op.create_table(
        'sla_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='priorityenum', native_enum=False, length=50), nullable=False),
        sa.Column('days_to_dispose', sa.Integer(), nullable=False),
        sa.Column('warn_at_pct', sa.Integer(), nullable=False),
        sa.Column('reminder_after_days', sa.Integer(), nullable=False),
        sa.Column('escalate_after_days', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'priority', name='uq_sla_rules_category_priority'),
    )
    op.create_index(op.f('ix_sla_rules_category_id'), 'sla_rules', ['category_id'], unique=False)
    op.create_index(op.f('ix_sla_rules_priority'), 'sla_rules', ['priority'], unique=False)

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('BUREAU_OFFICER', 'REGIONAL_OFFICER', 'SENIOR_MGMT', 'ADMIN', name='roleenum', native_enum=False, length=50), nullable=False),
        sa.Column('bureau_id', sa.Integer(), nullable=True),
        sa.Column('region_id', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['bureau_id'], ['bureaus.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_bureau_id'), 'users', ['bureau_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_region_id'), 'users', ['region_id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # 4. Cases table
    op.create_table(
        'cases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_no', sa.String(length=100), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=True),
        sa.Column('bureau_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'UNDER_PROCESS', 'DISPOSED', 'TRANSFERRED', 'ESCALATED', name='casestatusenum', native_enum=False, length=50), nullable=False),
        sa.Column('assigned_officer_id', sa.Integer(), nullable=True),
        sa.Column('received_on', sa.Date(), nullable=False),
        sa.Column('last_action_on', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_action_text', sa.Text(), nullable=True),
        sa.Column('next_action_text', sa.Text(), nullable=True),
        sa.Column('expected_disposal_on', sa.Date(), nullable=True),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='priorityenum', native_enum=False, length=50), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('complainant_ref', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('link_group_id', sa.String(length=36), nullable=True),
        sa.Column('needs_institution_review', sa.Boolean(), nullable=False),
        sa.Column('text_vector', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.ForeignKeyConstraint(['assigned_officer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bureau_id'], ['bureaus.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_no', 'bureau_id', name='uq_cases_case_no_bureau_id'),
    )
    op.create_index(op.f('ix_cases_assigned_officer_id'), 'cases', ['assigned_officer_id'], unique=False)
    op.create_index(op.f('ix_cases_bureau_id'), 'cases', ['bureau_id'], unique=False)
    op.create_index('ix_cases_bureau_id_status', 'cases', ['bureau_id', 'status'], unique=False)
    op.create_index(op.f('ix_cases_category_id'), 'cases', ['category_id'], unique=False)
    op.create_index('ix_cases_expected_disposal_on', 'cases', ['expected_disposal_on'], unique=False)
    op.create_index(op.f('ix_cases_institution_id'), 'cases', ['institution_id'], unique=False)
    op.create_index('ix_cases_institution_id_status', 'cases', ['institution_id', 'status'], unique=False)
    op.create_index(op.f('ix_cases_link_group_id'), 'cases', ['link_group_id'], unique=False)
    op.create_index(op.f('ix_cases_priority'), 'cases', ['priority'], unique=False)
    op.create_index('ix_cases_received_on', 'cases', ['received_on'], unique=False)
    op.create_index(op.f('ix_cases_status'), 'cases', ['status'], unique=False)

    # 5. Alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type', sa.Enum('OVERLAP', 'REMINDER', 'DUE_SOON', 'OVERDUE', 'ESCALATION', name='alerttypeenum', native_enum=False, length=50), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('institution_id', sa.Integer(), nullable=True),
        sa.Column('target_role', sa.Enum('BUREAU_OFFICER', 'REGIONAL_OFFICER', 'SENIOR_MGMT', 'ADMIN', name='roleenum', native_enum=False, length=50), nullable=True),
        sa.Column('target_bureau_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('due_on', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_bureau_id'], ['bureaus.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_alerts_case_id'), 'alerts', ['case_id'], unique=False)
    op.create_index('ix_alerts_case_id_type_created_at', 'alerts', ['case_id', 'type', 'created_at'], unique=False)
    op.create_index(op.f('ix_alerts_created_at'), 'alerts', ['created_at'], unique=False)
    op.create_index(op.f('ix_alerts_due_on'), 'alerts', ['due_on'], unique=False)
    op.create_index('ix_alerts_institution_id', 'alerts', ['institution_id'], unique=False)
    op.create_index(op.f('ix_alerts_read_at'), 'alerts', ['read_at'], unique=False)
    op.create_index(op.f('ix_alerts_target_bureau_id'), 'alerts', ['target_bureau_id'], unique=False)
    op.create_index(op.f('ix_alerts_target_role'), 'alerts', ['target_role'], unique=False)
    op.create_index(op.f('ix_alerts_type'), 'alerts', ['type'], unique=False)

    # 6. Attachments
    op.create_table(
        'attachments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime', sa.String(length=100), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('stored_path', sa.String(length=500), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_attachments_case_id'), 'attachments', ['case_id'], unique=False)
    op.create_index(op.f('ix_attachments_sha256'), 'attachments', ['sha256'], unique=False)
    op.create_index(op.f('ix_attachments_uploaded_by'), 'attachments', ['uploaded_by'], unique=False)

    # 7. Case links
    op.create_table(
        'case_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('linked_by', sa.Integer(), nullable=False),
        sa.Column('lead_bureau_id', sa.Integer(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_bureau_id'], ['bureaus.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['linked_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_case_links_case_id', 'case_links', ['case_id'], unique=False)
    op.create_index('ix_case_links_group_id', 'case_links', ['group_id'], unique=False)
    op.create_index(op.f('ix_case_links_lead_bureau_id'), 'case_links', ['lead_bureau_id'], unique=False)
    op.create_index(op.f('ix_case_links_linked_by'), 'case_links', ['linked_by'], unique=False)

    # 8. Overlap flags (Tier A partial unique & Tier B unique)
    op.create_table(
        'overlap_flags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('case_a', sa.Integer(), nullable=True),
        sa.Column('case_b', sa.Integer(), nullable=True),
        sa.Column('tier', sa.Enum('A', 'B', name='overlaptierenum', native_enum=False, length=10), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('reasons', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('state', sa.Enum('OPEN', 'CONFIRMED', 'DISMISSED', name='overlapstateenum', native_enum=False, length=50), nullable=False),
        sa.Column('decided_by', sa.Integer(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_a'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_b'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_overlap_flags_case_a'), 'overlap_flags', ['case_a'], unique=False)
    op.create_index(op.f('ix_overlap_flags_case_b'), 'overlap_flags', ['case_b'], unique=False)
    op.create_index(op.f('ix_overlap_flags_decided_by'), 'overlap_flags', ['decided_by'], unique=False)
    op.create_index(op.f('ix_overlap_flags_institution_id'), 'overlap_flags', ['institution_id'], unique=False)
    op.create_index(op.f('ix_overlap_flags_state'), 'overlap_flags', ['state'], unique=False)
    op.create_index(op.f('ix_overlap_flags_tier'), 'overlap_flags', ['tier'], unique=False)
    op.create_index(
        'uq_overlap_flags_case_a_case_b',
        'overlap_flags',
        ['case_a', 'case_b'],
        unique=True,
        postgresql_where=sa.text('case_a IS NOT NULL AND case_b IS NOT NULL'),
        sqlite_where=sa.text('case_a IS NOT NULL AND case_b IS NOT NULL'),
    )
    op.create_index(
        'uq_overlap_flags_tier_a_institution',
        'overlap_flags',
        ['institution_id'],
        unique=True,
        postgresql_where=sa.text('case_a IS NULL AND case_b IS NULL'),
        sqlite_where=sa.text('case_a IS NULL AND case_b IS NULL'),
    )

    # 9. Case actions (append-only audit trail)
    op.create_table(
        'case_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('bureau_id', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.Enum('CREATED', 'ASSIGNED', 'ACTION', 'TRANSFERRED', 'ESCALATED', 'LINKED', 'NOTE', 'DISPOSED', 'REOPENED', name='actiontypeenum', native_enum=False, length=50), nullable=False),
        sa.Column('from_status', sa.Enum('PENDING', 'UNDER_PROCESS', 'DISPOSED', 'TRANSFERRED', 'ESCALATED', name='casestatusenum', native_enum=False, length=50), nullable=True),
        sa.Column('to_status', sa.Enum('PENDING', 'UNDER_PROCESS', 'DISPOSED', 'TRANSFERRED', 'ESCALATED', name='casestatusenum', native_enum=False, length=50), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('attachment_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['attachment_id'], ['attachments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bureau_id'], ['bureaus.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_case_actions_action_type'), 'case_actions', ['action_type'], unique=False)
    op.create_index(op.f('ix_case_actions_actor_id'), 'case_actions', ['actor_id'], unique=False)
    op.create_index(op.f('ix_case_actions_attachment_id'), 'case_actions', ['attachment_id'], unique=False)
    op.create_index(op.f('ix_case_actions_bureau_id'), 'case_actions', ['bureau_id'], unique=False)
    op.create_index(op.f('ix_case_actions_case_id'), 'case_actions', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_actions_created_at'), 'case_actions', ['created_at'], unique=False)

    # 10. PostgreSQL Trigger for append-only case_actions
    if bind.dialect.name == "postgresql":
        op.execute("""
        CREATE OR REPLACE FUNCTION prevent_case_actions_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'case_actions is append-only: updates and deletes are prohibited';
        END;
        $$ LANGUAGE plpgsql;
        """)
        op.execute("""
        CREATE TRIGGER trg_case_actions_append_only
        BEFORE UPDATE OR DELETE ON case_actions
        FOR EACH ROW EXECUTE FUNCTION prevent_case_actions_modification();
        """)


def downgrade() -> None:
    bind = op.get_bind()

    # Drop PostgreSQL append-only trigger
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_case_actions_append_only ON case_actions;")
        op.execute("DROP FUNCTION IF EXISTS prevent_case_actions_modification();")

    op.drop_index(op.f('ix_case_actions_created_at'), table_name='case_actions')
    op.drop_index(op.f('ix_case_actions_case_id'), table_name='case_actions')
    op.drop_index(op.f('ix_case_actions_bureau_id'), table_name='case_actions')
    op.drop_index(op.f('ix_case_actions_attachment_id'), table_name='case_actions')
    op.drop_index(op.f('ix_case_actions_actor_id'), table_name='case_actions')
    op.drop_index(op.f('ix_case_actions_action_type'), table_name='case_actions')
    op.drop_table('case_actions')

    op.drop_index('uq_overlap_flags_tier_a_institution', table_name='overlap_flags', postgresql_where=sa.text('case_a IS NULL AND case_b IS NULL'), sqlite_where=sa.text('case_a IS NULL AND case_b IS NULL'))
    op.drop_index('uq_overlap_flags_case_a_case_b', table_name='overlap_flags', postgresql_where=sa.text('case_a IS NOT NULL AND case_b IS NOT NULL'), sqlite_where=sa.text('case_a IS NOT NULL AND case_b IS NOT NULL'))
    op.drop_index(op.f('ix_overlap_flags_tier'), table_name='overlap_flags')
    op.drop_index(op.f('ix_overlap_flags_state'), table_name='overlap_flags')
    op.drop_index(op.f('ix_overlap_flags_institution_id'), table_name='overlap_flags')
    op.drop_index(op.f('ix_overlap_flags_decided_by'), table_name='overlap_flags')
    op.drop_index(op.f('ix_overlap_flags_case_b'), table_name='overlap_flags')
    op.drop_index(op.f('ix_overlap_flags_case_a'), table_name='overlap_flags')
    op.drop_table('overlap_flags')

    op.drop_index(op.f('ix_case_links_linked_by'), table_name='case_links')
    op.drop_index(op.f('ix_case_links_lead_bureau_id'), table_name='case_links')
    op.drop_index('ix_case_links_group_id', table_name='case_links')
    op.drop_index('ix_case_links_case_id', table_name='case_links')
    op.drop_table('case_links')

    op.drop_index(op.f('ix_attachments_uploaded_by'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_sha256'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_case_id'), table_name='attachments')
    op.drop_table('attachments')

    op.drop_index(op.f('ix_alerts_type'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_target_role'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_target_bureau_id'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_read_at'), table_name='alerts')
    op.drop_index('ix_alerts_institution_id', table_name='alerts')
    op.drop_index(op.f('ix_alerts_due_on'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_created_at'), table_name='alerts')
    op.drop_index('ix_alerts_case_id_type_created_at', table_name='alerts')
    op.drop_index(op.f('ix_alerts_case_id'), table_name='alerts')
    op.drop_table('alerts')

    op.drop_index(op.f('ix_cases_status'), table_name='cases')
    op.drop_index('ix_cases_received_on', table_name='cases')
    op.drop_index(op.f('ix_cases_priority'), table_name='cases')
    op.drop_index(op.f('ix_cases_link_group_id'), table_name='cases')
    op.drop_index('ix_cases_institution_id_status', table_name='cases')
    op.drop_index(op.f('ix_cases_institution_id'), table_name='cases')
    op.drop_index('ix_cases_expected_disposal_on', table_name='cases')
    op.drop_index(op.f('ix_cases_category_id'), table_name='cases')
    op.drop_index('ix_cases_bureau_id_status', table_name='cases')
    op.drop_index(op.f('ix_cases_bureau_id'), table_name='cases')
    op.drop_index(op.f('ix_cases_assigned_officer_id'), table_name='cases')
    op.drop_table('cases')

    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_region_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_bureau_id'), table_name='users')
    op.drop_table('users')

    op.drop_index(op.f('ix_sla_rules_priority'), table_name='sla_rules')
    op.drop_index(op.f('ix_sla_rules_category_id'), table_name='sla_rules')
    op.drop_table('sla_rules')

    op.drop_index('ix_institutions_region_id', table_name='institutions')
    op.drop_index('ix_institutions_name_trgm', table_name='institutions', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.drop_index(op.f('ix_institutions_name'), table_name='institutions')
    op.drop_index(op.f('ix_institutions_aicte_permanent_id'), table_name='institutions')
    op.drop_table('institutions')

    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_bureau_id'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index(op.f('ix_regions_name'), table_name='regions')
    op.drop_table('regions')

    op.drop_index(op.f('ix_categories_name'), table_name='categories')
    op.drop_table('categories')

    op.drop_index(op.f('ix_bureaus_code'), table_name='bureaus')
    op.drop_table('bureaus')

    # Drop pg_trgm extension if PostgreSQL
    if bind.dialect.name == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
