import type { CaseStatus } from './constants'

export type SlaState =
  | { kind: 'closed' }
  | { kind: 'none' }
  | { kind: 'overdue'; days: number }
  | { kind: 'warn'; days: number }
  | { kind: 'ok'; days: number }

const DAY = 86_400_000
const at = (iso: string) => new Date(`${iso}T00:00:00`).getTime()

// PLACEHOLDER thresholds (not AICTE norms): warn once 75% of the allowed window has passed
// (matches the SLA design in AGENTS.md); if received_on is unknown, warn in the last 7 days.
// "Overdue" mirrors the backend rule beyond_sla = expected_disposal_on < today AND open.
export function slaState(
  c: { status: CaseStatus; expected_disposal_on?: string | null; received_on?: string | null },
  now: number = Date.now(),
): SlaState {
  if (c.status === 'DISPOSED') return { kind: 'closed' }
  if (!c.expected_disposal_on) return { kind: 'none' }

  const due = at(c.expected_disposal_on)
  const today = new Date(now).setHours(0, 0, 0, 0)
  const left = Math.round((due - today) / DAY)
  if (left < 0) return { kind: 'overdue', days: -left }

  let warn = left <= 7
  if (c.received_on) {
    const start = at(c.received_on)
    const total = due - start
    if (total > 0) warn = (today - start) / total >= 0.75
  }
  return { kind: warn ? 'warn' : 'ok', days: left }
}
