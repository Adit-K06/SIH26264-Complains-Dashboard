import type { CaseRow } from '../api/types'
import { STATUSES } from './constants'
import type { CaseStatus } from './constants'

/* ---------- list filters (URL is the source of truth) ---------- */
export interface InstitutionFilters {
  q: string
  region_id?: number
  page: number
  page_size: number
}

export const DEFAULT_PAGE_SIZE = 20

export function parseInstitutionFilters(p: URLSearchParams): InstitutionFilters {
  const posInt = (key: string): number | undefined => {
    const n = Number(p.get(key))
    return Number.isInteger(n) && n > 0 ? n : undefined
  }
  return {
    q: (p.get('q') ?? '').trim(),
    region_id: posInt('region_id'),
    page: posInt('page') ?? 1,
    page_size: Math.min(posInt('page_size') ?? DEFAULT_PAGE_SIZE, 100),
  }
}

export function toSearchParams(f: InstitutionFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.q) p.set('q', f.q)
  if (f.region_id) p.set('region_id', String(f.region_id))
  if (f.page > 1) p.set('page', String(f.page))
  if (f.page_size !== DEFAULT_PAGE_SIZE) p.set('page_size', String(f.page_size))
  return p
}

export function toApiParams(f: InstitutionFilters): Record<string, string | number> {
  const out: Record<string, string | number> = { page: f.page, page_size: f.page_size }
  if (f.q) out.q = f.q
  if (f.region_id) out.region_id = f.region_id
  return out
}

/* ---------- Institution 360: numbers computed from the institution's cases ---------- */
export interface BureauRow {
  key: string
  bureau_id: number | null
  label: string
  counts: Record<CaseStatus, number>
  total: number
}

export interface InstSummary {
  total: number
  open: number
  beyondSla: number // open AND expected_disposal_on < today (same definition as AGENTS.md)
  rows: BureauRow[]
  totals: Record<CaseStatus, number>
  openBureaus: string[] // distinct bureaus with open cases (Tier A rule needs >= 2)
}

const emptyCounts = () =>
  Object.fromEntries(STATUSES.map((s) => [s, 0])) as Record<CaseStatus, number>

export function summarise(cases: CaseRow[]): InstSummary {
  const todayMs = new Date().setHours(0, 0, 0, 0)
  const map = new Map<string, BureauRow>()
  const totals = emptyCounts()
  const openBureaus = new Set<string>()
  let open = 0
  let beyondSla = 0

  for (const c of cases) {
    const label = c.bureau_code ?? 'Unknown'
    let row = map.get(label)
    if (!row) {
      row = { key: label, bureau_id: c.bureau_id ?? null, label, counts: emptyCounts(), total: 0 }
      map.set(label, row)
    }
    row.counts[c.status] += 1
    row.total += 1
    totals[c.status] += 1

    if (c.status !== 'DISPOSED') {
      open += 1
      openBureaus.add(label)
      if (c.expected_disposal_on && new Date(`${c.expected_disposal_on}T00:00:00`).getTime() < todayMs) {
        beyondSla += 1
      }
    }
  }

  return {
    total: cases.length,
    open,
    beyondSla,
    rows: [...map.values()].sort((a, b) => a.label.localeCompare(b.label)),
    totals,
    openBureaus: [...openBureaus].sort(),
  }
}

/** Link into the Cases list, filtered. Uses the filter names from AGENTS.md. */
export function casesLink(institutionId: number, extra: Record<string, string | number> = {}): string {
  const p = new URLSearchParams({ institution_id: String(institutionId) })
  for (const [k, v] of Object.entries(extra)) p.set(k, String(v))
  return `/cases?${p.toString()}`
}
