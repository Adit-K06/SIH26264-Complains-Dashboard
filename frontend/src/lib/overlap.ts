import type { OverlapRow } from '../api/overlapTypes'

export const OVERLAP_STATES = ['OPEN', 'CONFIRMED', 'DISMISSED'] as const
export type OverlapState = (typeof OVERLAP_STATES)[number]

export const STATE_LABEL: Record<OverlapState, string> = {
  OPEN: 'Open',
  CONFIRMED: 'Confirmed',
  DISMISSED: 'Dismissed',
}

// Reason codes from AGENTS.md. Unknown codes are shown as-is.
const REASON_LABEL: Record<string, string> = {
  HIGH_TEXT_SIMILARITY: 'Similar text',
  SAME_CATEGORY: 'Same category',
  WITHIN_30_DAYS: 'Within 30 days',
  SHARED_REFERENCE: 'Shared reference',
  SHARED_COMPLAINANT_REF: 'Same complainant ref',
  DIFFERENT_BUREAU: 'Different bureaus',
}
export const reasonLabel = (code: string) => REASON_LABEL[code] ?? code

export interface OverlapFilters {
  state: OverlapState
  tier: '' | 'A' | 'B'
  region_id?: number
  min_score?: number
  page: number
  page_size: number
}

export const DEFAULT_PAGE_SIZE = 20

export function parseOverlapFilters(p: URLSearchParams): OverlapFilters {
  const posInt = (key: string): number | undefined => {
    const n = Number(p.get(key))
    return Number.isInteger(n) && n > 0 ? n : undefined
  }
  const s = p.get('state')
  const state: OverlapState = (OVERLAP_STATES as readonly string[]).includes(s ?? '')
    ? (s as OverlapState)
    : 'OPEN'
  const t = p.get('tier')
  const tier: '' | 'A' | 'B' = t === 'A' || t === 'B' ? t : ''
  const raw = p.get('min_score')
  const m = raw === null || raw === '' ? NaN : Number(raw)
  return {
    state,
    tier,
    region_id: posInt('region_id'),
    min_score: Number.isFinite(m) && m > 0 && m <= 1 ? m : undefined,
    page: posInt('page') ?? 1,
    page_size: Math.min(posInt('page_size') ?? DEFAULT_PAGE_SIZE, 100),
  }
}

/** Browser URL: only non-default values are written. */
export function toSearchParams(f: OverlapFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.state !== 'OPEN') p.set('state', f.state)
  if (f.tier) p.set('tier', f.tier)
  if (f.region_id) p.set('region_id', String(f.region_id))
  if (f.min_score !== undefined) p.set('min_score', String(f.min_score))
  if (f.page > 1) p.set('page', String(f.page))
  if (f.page_size !== DEFAULT_PAGE_SIZE) p.set('page_size', String(f.page_size))
  return p
}

/** Request to GET /overlaps. */
export function toApiParams(f: OverlapFilters): Record<string, string | number> {
  const out: Record<string, string | number> = { state: f.state, page: f.page, page_size: f.page_size }
  if (f.tier) out.tier = f.tier
  if (f.region_id) out.region_id = f.region_id
  if (f.min_score !== undefined) out.min_score = f.min_score
  return out
}

export function bureausOf(r: OverlapRow): string[] {
  if (r.bureaus && r.bureaus.length > 0) return r.bureaus
  const codes = (r.cases ?? []).map((c) => c.bureau_code).filter((x): x is string => !!x)
  return Array.from(new Set(codes))
}

export function involvedBureauIds(r: OverlapRow): number[] {
  const ids = (r.cases ?? []).map((c) => c.bureau_id).filter((x): x is number => typeof x === 'number')
  return Array.from(new Set(ids))
}
