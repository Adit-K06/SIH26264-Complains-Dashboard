import type { Actor, Role, WorkflowKind } from '../api/caseDetailTypes'
import type { CaseStatus } from './constants'

export interface CurrentUser extends Actor {
  role: Role
  region_id: number | null
}

type CaseScope = { status: CaseStatus; bureau_id?: number | null; region_id?: number | null }

export const isOpen = (s: CaseStatus) => s !== 'DISPOSED'

/**
 * Which workflow buttons to SHOW. This is only UX: the backend enforces RBAC
 * and the transition table (anything else -> HTTP 409/403).
 * AGENTS.md: BUREAU_OFFICER acts only in own bureau; REGIONAL_OFFICER only for
 * own region; SENIOR_MGMT read + escalate only; ADMIN everything.
 */
export function allowedActions(user: CurrentUser, c: CaseScope): WorkflowKind[] {
  const own =
    user.role === 'ADMIN' ||
    (user.role === 'BUREAU_OFFICER' && user.bureau_id != null && user.bureau_id === c.bureau_id) ||
    (user.role === 'REGIONAL_OFFICER' && user.region_id != null && user.region_id === c.region_id)
  const open = isOpen(c.status)
  const out: WorkflowKind[] = []
  if (own && open) out.push('action', 'transfer')
  if ((own || user.role === 'SENIOR_MGMT') && open && c.status !== 'ESCALATED') out.push('escalate')
  if (own && c.status === 'UNDER_PROCESS') out.push('dispose')
  if (own && c.status === 'DISPOSED') out.push('reopen')
  return out
}

/** Upload is shown to anyone who may act on the case (not read-only / escalate-only users). */
export function canUpload(user: CurrentUser, c: CaseScope): boolean {
  return user.role !== 'SENIOR_MGMT' && allowedActions(user, c).length > 0
}
