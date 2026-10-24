// Exact strings from AGENTS.md. Do not rename.
export const STATUSES = [
  'PENDING',
  'UNDER_PROCESS',
  'DISPOSED',
  'TRANSFERRED',
  'ESCALATED',
] as const
export type CaseStatus = (typeof STATUSES)[number]

export const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH'] as const
export type Priority = (typeof PRIORITIES)[number]

export const STATUS_LABEL: Record<CaseStatus, string> = {
  PENDING: 'Pending',
  UNDER_PROCESS: 'Under process',
  DISPOSED: 'Disposed',
  TRANSFERRED: 'Transferred',
  ESCALATED: 'Escalated',
}

// Pending amber, Under process blue, Disposed green, Transferred purple, Escalated red.
export const STATUS_COLOR: Record<CaseStatus, string> = {
  PENDING: '#d97706',
  UNDER_PROCESS: '#2563eb',
  DISPOSED: '#16a34a',
  TRANSFERRED: '#7c3aed',
  ESCALATED: '#dc2626',
}

export const STATUS_BADGE_CLASS: Record<CaseStatus, string> = {
  PENDING: 'bg-amber-50 text-amber-700 border-amber-200',
  UNDER_PROCESS: 'bg-blue-50 text-blue-700 border-blue-200',
  DISPOSED: 'bg-green-50 text-green-700 border-green-200',
  TRANSFERRED: 'bg-purple-50 text-purple-700 border-purple-200',
  ESCALATED: 'bg-red-50 text-red-700 border-red-200',
}

export const OVERLAP_HEADING = 'Potential Overlapping Cases - Coordination Required'
