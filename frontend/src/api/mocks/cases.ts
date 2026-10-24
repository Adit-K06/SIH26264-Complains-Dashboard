// Mock data lives ONLY in src/api/mocks. 240 deterministic SYNTHETIC cases.
// mockQueryCases applies the same filters the real GET /cases should, so the
// filter UI can be tested properly before a backend exists.
import type { CaseFilters } from '../../lib/caseFilters'
import { BUREAUS, CATEGORIES, REGIONS } from '../../lib/lookups'
import type { CaseStatus, Priority } from '../../lib/constants'
import type { CaseRow, Paged } from '../types'

const DAY = 86_400_000
const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10)
const todayMs = new Date().setHours(0, 0, 0, 0)
const addDays = (baseMs: number, n: number) => baseMs + n * DAY
const parse = (s: string) => new Date(`${s}T00:00:00`).getTime()

function rng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 4294967296
  }
}

const TYPES = ['College of Engineering', 'Institute of Technology', 'Polytechnic', 'Institute of Management']
const SLA_DAYS: Record<Priority, number> = { HIGH: 15, MEDIUM: 30, LOW: 45 } // PLACEHOLDER

const rand = rng(42)
const pick = <T>(arr: readonly T[]): T => arr[Math.floor(rand() * arr.length)]

function makeCase(i: number): CaseRow {
  const bureau = pick(BUREAUS)
  const r = rand()
  const status: CaseStatus =
    r < 0.2 ? 'PENDING' : r < 0.5 ? 'UNDER_PROCESS' : r < 0.8 ? 'DISPOSED' : r < 0.88 ? 'TRANSFERRED' : 'ESCALATED'
  const priority: Priority = pick(['LOW', 'MEDIUM', 'HIGH'] as const)
  const agoDays = Math.floor(rand() * 540) + 1
  const received = addDays(todayMs, -agoDays)
  const lastActionAgo = Math.floor(rand() * Math.min(agoDays, 60))
  const institutionId = 1 + Math.floor(rand() * 60)
  const category = pick(CATEGORIES)
  return {
    id: i + 1,
    case_no: `${bureau.label}/${new Date(received).getFullYear()}/${String(i + 1).padStart(6, '0')}`,
    status,
    institution_id: institutionId,
    institution_name: `Synthetic ${TYPES[institutionId % TYPES.length]} ${institutionId}`,
    bureau_id: bureau.id,
    bureau_code: bureau.label,
    region_id: pick(REGIONS).id,
    category_id: category.id,
    category_name: category.label,
    priority,
    received_on: iso(received),
    last_action_on: iso(addDays(todayMs, -lastActionAgo)),
    expected_disposal_on: iso(addDays(received, SLA_DAYS[priority])),
    link_group_id: rand() < 0.08 ? 100 + i : null,
  }
}

const ALL: CaseRow[] = Array.from({ length: 240 }, (_, i) => makeCase(i)).sort((a, b) =>
  (b.received_on ?? '').localeCompare(a.received_on ?? ''),
)

const aicteIdOf = (institutionId: number) => `SYN-${String(10000 + institutionId).padStart(5, '0')}`

export function mockQueryCases(f: CaseFilters): Paged<CaseRow> {
  const q = f.q.trim().toLowerCase()
  const rows = ALL.filter((c) => {
    const open = c.status !== 'DISPOSED'
    if (q) {
      const hay = `${c.case_no} ${c.institution_name ?? ''}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    if (f.status && c.status !== f.status) return false
    if (f.priority && c.priority !== f.priority) return false
    if (f.bureau_id && c.bureau_id !== f.bureau_id) return false
    if (f.region_id && c.region_id !== f.region_id) return false
    if (f.category_id && c.category_id !== f.category_id) return false
    if (f.institution_id && c.institution_id !== f.institution_id) return false
    if (f.aicte_id && c.institution_id && aicteIdOf(c.institution_id) !== f.aicte_id.toUpperCase()) return false
    if (f.from_date && (c.received_on ?? '') < f.from_date) return false
    if (f.to_date && (c.received_on ?? '') > f.to_date) return false
    if (f.beyond_sla && !(open && c.expected_disposal_on && parse(c.expected_disposal_on) < todayMs)) return false
    if (f.linked !== undefined && (c.link_group_id !== null) !== f.linked) return false
    if (f.no_recent_action_days) {
      const idle = c.last_action_on ? (todayMs - parse(c.last_action_on)) / DAY : Infinity
      if (!open || idle < f.no_recent_action_days) return false
    }
    return true
  })
  const start = (f.page - 1) * f.page_size
  return {
    items: rows.slice(start, start + f.page_size),
    total: rows.length,
    page: f.page,
    page_size: f.page_size,
  }
}
