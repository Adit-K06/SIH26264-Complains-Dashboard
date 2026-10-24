import type { CaseStatus } from '../lib/constants'
import type { CaseRow } from './types'

/* ------------------------------------------------------------------
 * ASSUMED RESPONSE / REQUEST SHAPES for the Case detail page.
 * AGENTS.md lists the endpoints but not their JSON bodies.
 * ASSUMPTION: GET /cases/{id} returns the case plus its `actions`
 * (case_actions rows) and `attachments` embedded. If P1 serves them
 * from separate endpoints, adjust ONLY this file and src/api/caseDetail.ts.
 * ------------------------------------------------------------------ */

export const ROLES = ['BUREAU_OFFICER', 'REGIONAL_OFFICER', 'SENIOR_MGMT', 'ADMIN'] as const
export type Role = (typeof ROLES)[number]

// Exact strings from AGENTS.md
export const ACTION_TYPES = [
  'CREATED',
  'ASSIGNED',
  'ACTION',
  'TRANSFERRED',
  'ESCALATED',
  'LINKED',
  'NOTE',
  'DISPOSED',
  'REOPENED',
] as const
export type ActionType = (typeof ACTION_TYPES)[number]

export interface CaseAction {
  id: number
  case_id: number
  actor_id?: number | null // null = system
  actor_name?: string | null
  bureau_id?: number | null
  bureau_code?: string | null
  action_type: ActionType
  from_status?: CaseStatus | null
  to_status?: CaseStatus | null
  remarks?: string | null
  attachment_id?: number | null
  created_at: string // ISO datetime
}

export interface Attachment {
  id: number
  filename: string
  mime: string
  size: number // bytes
  uploaded_by_name?: string | null
  created_at?: string | null
}

export interface LinkedCase {
  id: number
  case_no: string
  bureau_code?: string | null
}

export interface OverlapInfo {
  id: number
  tier: 'A' | 'B'
  score: number | null
  other_case_id?: number | null
  other_case_no?: string | null
  other_bureau_code?: string | null
}

export interface CaseDetail extends CaseRow {
  aicte_permanent_id?: string | null
  region_name?: string | null
  assigned_officer_name?: string | null
  last_action_text?: string | null
  next_action_text?: string | null
  summary?: string | null
  complainant_ref?: string | null // already masked by the backend when out of scope
  source?: string | null
  needs_institution_review?: boolean
  linked_cases?: LinkedCase[]
  lead_bureau_code?: string | null
  link_note?: string | null
  overlaps?: OverlapInfo[]
  actions: CaseAction[]
  attachments: Attachment[]
}

// Workflow buttons -> POST /cases/{id}/actions | /transfer | /escalate | /dispose | /reopen
export type WorkflowKind = 'action' | 'transfer' | 'escalate' | 'dispose' | 'reopen'

export interface WorkflowFields {
  remarks?: string
  next_action_text?: string
  start_processing?: boolean // action only: PENDING -> UNDER_PROCESS
  to_bureau_id?: number // transfer only
}
export interface WorkflowInput extends WorkflowFields {
  kind: WorkflowKind
}

export interface Actor {
  id: number
  name: string
  bureau_id: number | null
}
