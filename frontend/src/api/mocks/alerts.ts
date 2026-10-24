// Mock data lives ONLY in src/api/mocks. Alerts are derived from the same 240 SYNTHETIC cases.
// Timings below (due soon at 75% of the window, reminder after 7 idle days) are PLACEHOLDERS,
// not official norms. Read state mutates in memory (resets on page reload).
import { parseFilters } from '../../lib/caseFilters'
import type { AlertFilters } from '../../lib/alerts'
import type { Alert } from '../alertTypes'
import type { Paged } from '../types'
import { mockQueryCases } from './cases'
import { mockQueryOverlaps } from './overlaps'

const DAY = 86_400_000
const dayMs = (s?: string | null) => (s ? new Date(`${s}T00:00:00`).getTime() : Number.NaN)

let cache: Alert[] | null = null
const readNow = new Map<number, string>()

function build(): Alert[] {
  const todayMs = new Date().setHours(0, 0, 0, 0)
  const rows = mockQueryCases({ ...parseFilters(new URLSearchParams()), page: 1, page_size: 1000 }).items
  const drafts: Array<Omit<Alert, 'id'>> = []
  const at = (n: number) => new Date(todayMs - (n % 9) * DAY + 9 * 3_600_000).toISOString()

  for (const c of rows) {
    if (c.status === 'DISPOSED') continue
    const due = dayMs(c.expected_disposal_on)
    const rec = dayMs(c.received_on)
    if (Number.isNaN(due) || Number.isNaN(rec)) continue
    const base = {
      case_id: c.id,
      case_no: c.case_no,
      institution_id: c.institution_id ?? null,
      institution_name: c.institution_name ?? null,
      target_bureau_id: c.bureau_id ?? null,
      due_on: c.expected_disposal_on ?? null,
    }
    const over = Math.floor((todayMs - due) / DAY)
    if (over > 0) {
      drafts.push({
        ...base,
        type: 'OVERDUE',
        message: `${c.case_no} is ${over} day${over === 1 ? '' : 's'} beyond its expected disposal date.`,
        created_at: at(c.id),
      })
      if (c.status === 'ESCALATED') {
        drafts.push({
          ...base,
          type: 'ESCALATION',
          target_role: 'SENIOR_MGMT',
          message: `${c.case_no} was escalated after remaining overdue.`,
          created_at: at(c.id + 3),
        })
      }
    } else if (due > rec && (todayMs - rec) / (due - rec) >= 0.75) {
      drafts.push({
        ...base,
        type: 'DUE_SOON',
        message: `${c.case_no} is approaching its expected disposal date.`,
        created_at: at(c.id + 1),
      })
    }
    const idle = Math.floor((todayMs - dayMs(c.last_action_on)) / DAY)
    if (Number.isFinite(idle) && idle >= 7) {
      drafts.push({
        ...base,
        type: 'REMINDER',
        message: `${c.case_no} has had no action for ${idle} days.`,
        created_at: at(c.id + 2),
      })
    }
  }

  // Tier A overlap flags still open -> one OVERLAP alert each (needs the Overlap Center pack).
  for (const o of mockQueryOverlaps({ state: 'OPEN', tier: 'A', page: 1, page_size: 1000 }).items) {
    const first = o.cases?.[0]
    drafts.push({
      type: 'OVERLAP',
      case_id: first?.id ?? null,
      case_no: first?.case_no ?? null,
      institution_id: o.institution_id,
      institution_name: o.institution_name ?? null,
      message: `Potential overlapping cases at ${o.institution_name ?? `institution ${o.institution_id}`}: open in ${(o.bureaus ?? []).join(' + ')}.`,
      created_at: at(o.id + 4),
    })
  }

  drafts.sort((a, b) => b.created_at.localeCompare(a.created_at))
  return drafts.map((d, i) => ({ ...d, id: i + 1, read_at: (i + 1) % 5 === 0 ? d.created_at : null }))
}

function all(): Alert[] {
  if (!cache) cache = build()
  return cache
}

const withRead = (a: Alert): Alert => ({ ...a, read_at: readNow.get(a.id) ?? a.read_at ?? null })

export function mockQueryAlerts(f: AlertFilters): Paged<Alert> {
  const rows = all()
    .map(withRead)
    .filter((a) => (!f.unread || !a.read_at) && (!f.type || a.type === f.type))
  const start = (f.page - 1) * f.page_size
  return { items: rows.slice(start, start + f.page_size), total: rows.length, page: f.page, page_size: f.page_size }
}

export function mockMarkRead(id: number): void {
  if (!all().some((a) => a.id === id)) throw new Error('Alert not found')
  readNow.set(id, new Date().toISOString())
}
