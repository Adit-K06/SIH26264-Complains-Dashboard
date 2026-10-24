import type { CaseStatus, Priority } from '../lib/constants'

// Envelope from AGENTS.md: {"items":[...],"total":N,"page":1,"page_size":20}
export interface Paged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/* ------------------------------------------------------------------
 * ASSUMED RESPONSE SHAPES.
 * AGENTS.md lists the endpoints but not their JSON bodies.
 * Everything below is an assumption. The person doing integration only
 * needs to adjust THIS file and the files in src/api/ to match what
 * P1's /cases and /overlaps and P4's /dashboard/* really return.
 * ------------------------------------------------------------------ */

export interface MonthlyPoint {
  month: string // "2026-03"
  received: number
  disposed: number
}

// GET /dashboard/summary
export interface DashboardSummary {
  total: number
  by_status: Partial<Record<CaseStatus, number>>
  beyond_sla: number
  open_overlaps: number
  confirmed_groups: number
  monthly?: MonthlyPoint[] // monthly trend; endpoint/location not in contract yet
}

// GET /dashboard/workload  (bureau x status)
export interface WorkloadRow {
  bureau: string // bureau code: RB, PGRC, APPROVAL, ACADEMIC, FINANCE
  counts: Partial<Record<CaseStatus, number>>
}
export interface Workload {
  items: WorkloadRow[]
}

// GET /dashboard/ageing  (buckets 0-7, 8-15, 16-30, 31-60, 60+)
export interface AgeingBucket {
  bucket: string
  count: number
}
export interface Ageing {
  items: AgeingBucket[]
}

// GET /cases  (one row of the list; column names follow the cases table in AGENTS.md)
export interface CaseRow {
  id: number
  case_no: string
  status: CaseStatus
  institution_id?: number | null
  institution_name?: string | null
  bureau_id?: number | null
  bureau_code?: string | null
  region_id?: number | null
  category_id?: number | null
  category_name?: string | null
  priority?: Priority | null
  received_on?: string | null // YYYY-MM-DD
  last_action_on?: string | null
  expected_disposal_on?: string | null
  link_group_id?: number | null // not null = linked with other cases
}

// GET /overlaps?state=OPEN
export interface OverlapFlag {
  id: number
  institution_id: number
  institution_name?: string | null
  tier: 'A' | 'B'
  score: number | null // null for Tier A
  reasons: string[] // reason codes from AGENTS.md
  state: 'OPEN' | 'CONFIRMED' | 'DISMISSED'
}
