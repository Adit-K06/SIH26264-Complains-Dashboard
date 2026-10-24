import { PRIORITIES, STATUSES } from './constants'
import type { CaseStatus, Priority } from './constants'

// Filter names follow AGENTS.md: q, institution_id, aicte_id, bureau_id, region_id,
// category_id, status, priority, from_date, to_date, beyond_sla,
// no_recent_action_days, linked, page, page_size.
export const PAGE_SIZES = [10, 20, 50] as const
export const DEFAULT_PAGE_SIZE = 20

export interface CaseFilters {
  q: string
  status?: CaseStatus
  priority?: Priority
  bureau_id?: number
  region_id?: number
  category_id?: number
  institution_id?: number
  aicte_id?: string
  from_date?: string // YYYY-MM-DD
  to_date?: string // YYYY-MM-DD
  beyond_sla: boolean
  linked?: boolean
  no_recent_action_days?: number
  page: number
  page_size: number
}

export type FilterPatch = Partial<CaseFilters>

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

function posInt(v: string | null): number | undefined {
  if (v === null || !/^\d+$/.test(v)) return undefined
  const n = Number(v)
  return n > 0 ? n : undefined
}

function oneOf<T extends string>(v: string | null, allowed: readonly T[]): T | undefined {
  return allowed.find((a) => a === v)
}

function dateOrUndef(v: string | null): string | undefined {
  return v !== null && DATE_RE.test(v) ? v : undefined
}

/** URL -> validated filters. Bad or unknown values are dropped, never thrown. */
export function parseFilters(p: URLSearchParams): CaseFilters {
  const linked = p.get('linked')
  return {
    q: (p.get('q') ?? '').trim(),
    status: oneOf(p.get('status'), STATUSES),
    priority: oneOf(p.get('priority'), PRIORITIES),
    bureau_id: posInt(p.get('bureau_id')),
    region_id: posInt(p.get('region_id')),
    category_id: posInt(p.get('category_id')),
    institution_id: posInt(p.get('institution_id')),
    aicte_id: p.get('aicte_id')?.trim() || undefined,
    from_date: dateOrUndef(p.get('from_date')),
    to_date: dateOrUndef(p.get('to_date')),
    beyond_sla: p.get('beyond_sla') === 'true',
    linked: linked === 'true' ? true : linked === 'false' ? false : undefined,
    no_recent_action_days: posInt(p.get('no_recent_action_days')),
    page: posInt(p.get('page')) ?? 1,
    page_size: PAGE_SIZES.find((s) => s === posInt(p.get('page_size'))) ?? DEFAULT_PAGE_SIZE,
  }
}

/** Filters -> URL. Defaults are left out so shared links stay short. */
export function toSearchParams(f: CaseFilters): URLSearchParams {
  const p = new URLSearchParams()
  const set = (k: string, v: string | number | boolean | undefined) => {
    if (v !== undefined && v !== '') p.set(k, String(v))
  }
  set('q', f.q)
  set('status', f.status)
  set('priority', f.priority)
  set('bureau_id', f.bureau_id)
  set('region_id', f.region_id)
  set('category_id', f.category_id)
  set('institution_id', f.institution_id)
  set('aicte_id', f.aicte_id)
  set('from_date', f.from_date)
  set('to_date', f.to_date)
  if (f.beyond_sla) p.set('beyond_sla', 'true')
  set('linked', f.linked)
  set('no_recent_action_days', f.no_recent_action_days)
  if (f.page > 1) p.set('page', String(f.page))
  if (f.page_size !== DEFAULT_PAGE_SIZE) p.set('page_size', String(f.page_size))
  return p
}

/** Filters -> query params for GET /cases. Only set values are sent. */
export function toApiParams(f: CaseFilters): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {
    page: f.page,
    page_size: f.page_size,
  }
  if (f.q) out.q = f.q
  if (f.status) out.status = f.status
  if (f.priority) out.priority = f.priority
  if (f.bureau_id) out.bureau_id = f.bureau_id
  if (f.region_id) out.region_id = f.region_id
  if (f.category_id) out.category_id = f.category_id
  if (f.institution_id) out.institution_id = f.institution_id
  if (f.aicte_id) out.aicte_id = f.aicte_id
  if (f.from_date) out.from_date = f.from_date
  if (f.to_date) out.to_date = f.to_date
  if (f.beyond_sla) out.beyond_sla = true
  if (f.linked !== undefined) out.linked = f.linked
  if (f.no_recent_action_days) out.no_recent_action_days = f.no_recent_action_days
  return out
}

export function activeFilterCount(f: CaseFilters): number {
  return [
    f.q !== '',
    f.status,
    f.priority,
    f.bureau_id,
    f.region_id,
    f.category_id,
    f.institution_id,
    f.aicte_id,
    f.from_date,
    f.to_date,
    f.beyond_sla,
    f.linked !== undefined,
    f.no_recent_action_days,
  ].filter(Boolean).length
}

/** Filters that arrive via links (e.g. from other pages) and have no input on the bar. */
export function extraChips(f: CaseFilters): Array<{ key: string; label: string; patch: FilterPatch }> {
  const chips: Array<{ key: string; label: string; patch: FilterPatch }> = []
  if (f.institution_id)
    chips.push({ key: 'institution_id', label: `Institution #${f.institution_id}`, patch: { institution_id: undefined } })
  if (f.aicte_id)
    chips.push({ key: 'aicte_id', label: `AICTE ID ${f.aicte_id}`, patch: { aicte_id: undefined } })
  if (f.linked !== undefined)
    chips.push({ key: 'linked', label: f.linked ? 'Linked cases only' : 'Not linked', patch: { linked: undefined } })
  if (f.no_recent_action_days)
    chips.push({
      key: 'no_recent_action_days',
      label: `No action in ${f.no_recent_action_days}+ days`,
      patch: { no_recent_action_days: undefined },
    })
  return chips
}
