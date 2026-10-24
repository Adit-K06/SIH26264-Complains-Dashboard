// Mock data lives ONLY in src/api/mocks. Flags are derived from the same 240 SYNTHETIC cases
// as the Cases list. Scores/reasons here are fake demo values, NOT output of the real matcher.
// Decisions mutate in-memory state (reset on page reload).
import { parseFilters } from '../../lib/caseFilters'
import type { CaseStatus } from '../../lib/constants'
import type { OverlapFilters } from '../../lib/overlap'
import type { Actor } from '../caseDetailTypes'
import type { OverlapCase, OverlapRow } from '../overlapTypes'
import type { CaseRow, Paged } from '../types'
import { mockQueryCases } from './cases'

const OFFICERS = ['S. Rao', 'A. Nair', 'M. Iyer', 'R. Kumar']
const NEXT_TEXT: Record<CaseStatus, string | null> = {
  PENDING: 'Assign officer and begin review',
  UNDER_PROCESS: 'Await institution reply',
  ESCALATED: 'Senior management review',
  TRANSFERRED: 'Receiving bureau to review',
  DISPOSED: null,
}

type Decision = Pick<OverlapRow, 'state' | 'lead_bureau_id' | 'note' | 'decided_by_name' | 'decided_at'>
const decisions = new Map<number, Decision>()
let cache: OverlapRow[] | null = null

const dayMs = (s?: string | null) => (s ? new Date(`${s}T00:00:00`).getTime() : Number.NaN)

function toOverlapCase(c: CaseRow): OverlapCase {
  return {
    id: c.id,
    case_no: c.case_no,
    status: c.status,
    bureau_id: c.bureau_id ?? null,
    bureau_code: c.bureau_code ?? null,
    category_name: c.category_name ?? null,
    priority: c.priority ?? null,
    received_on: c.received_on ?? null,
    assigned_officer_name: OFFICERS[c.id % OFFICERS.length],
    last_action_on: c.last_action_on ?? null,
    last_action_text: c.status === 'PENDING' ? null : 'Notice issued to institution',
    next_action_text: NEXT_TEXT[c.status],
    summary: `Synthetic complaint regarding ${(c.category_name ?? 'a general matter').toLowerCase()}. Demo data (source: SYNTHETIC).`,
  }
}

const initialState = (id: number): OverlapRow['state'] =>
  id % 10 === 7 ? 'CONFIRMED' : id % 10 === 8 ? 'DISMISSED' : 'OPEN'

const codes = (cs: CaseRow[]) =>
  Array.from(new Set(cs.map((c) => c.bureau_code).filter((x): x is string => !!x)))

function build(): OverlapRow[] {
  const rows = mockQueryCases({ ...parseFilters(new URLSearchParams()), page: 1, page_size: 1000 }).items
  const byInst = new Map<number, CaseRow[]>()
  for (const c of rows) {
    if (c.institution_id == null || c.status === 'DISPOSED') continue
    const list = byInst.get(c.institution_id)
    if (list) list.push(c)
    else byInst.set(c.institution_id, [c])
  }

  const tierA: OverlapRow[] = []
  const tierB: OverlapRow[] = []
  let nextB = 1000

  for (const [instId, list] of [...byInst.entries()].sort((x, y) => x[0] - y[0])) {
    const bureaus = codes(list)
    if (bureaus.length < 2) continue
    const common = {
      institution_id: instId,
      institution_name: list[0].institution_name ?? null,
      region_id: list[0].region_id ?? null,
    }
    tierA.push({
      ...common,
      id: instId,
      tier: 'A',
      score: null,
      reasons: ['DIFFERENT_BUREAU'],
      state: initialState(instId),
      bureaus,
      cases: list.map(toOverlapCase),
    })

    const pairs: Array<{ a: CaseRow; b: CaseRow; score: number }> = []
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        const a = list[i]
        const b = list[j]
        if (a.bureau_id === b.bureau_id) continue
        const score = 0.55 + ((a.id * 7 + b.id * 13) % 40) / 100
        if (score >= 0.6) pairs.push({ a, b, score: Number(score.toFixed(2)) })
      }
    }
    pairs.sort((x, y) => y.score - x.score)
    for (const { a, b, score } of pairs.slice(0, 2)) {
      const reasons = ['DIFFERENT_BUREAU']
      if (a.category_id === b.category_id) reasons.push('SAME_CATEGORY')
      if (Math.abs(dayMs(a.received_on) - dayMs(b.received_on)) <= 30 * 86_400_000) reasons.push('WITHIN_30_DAYS')
      if (score >= 0.75) reasons.push('HIGH_TEXT_SIMILARITY')
      const id = nextB++
      tierB.push({
        ...common,
        id,
        tier: 'B',
        score,
        reasons,
        state: initialState(id),
        bureaus: codes([a, b]),
        cases: [toOverlapCase(a), toOverlapCase(b)],
      })
    }
  }
  tierB.sort((x, y) => (y.score ?? 0) - (x.score ?? 0))
  return [...tierA, ...tierB]
}

function all(): OverlapRow[] {
  if (!cache) cache = build()
  return cache
}

function current(id: number): OverlapRow {
  const r = all().find((x) => x.id === id)
  if (!r) throw new Error('Overlap flag not found')
  const d = decisions.get(id)
  return d ? { ...r, ...d } : r
}

export function mockQueryOverlaps(f: OverlapFilters): Paged<OverlapRow> {
  const rows = all()
    .map((r) => current(r.id))
    .filter(
      (r) =>
        r.state === f.state &&
        (!f.tier || r.tier === f.tier) &&
        (!f.region_id || r.region_id === f.region_id) &&
        (f.min_score === undefined || r.score === null || r.score >= f.min_score),
    )
  const start = (f.page - 1) * f.page_size
  return { items: rows.slice(start, start + f.page_size), total: rows.length, page: f.page, page_size: f.page_size }
}

export function mockDecide(
  id: number,
  mode: 'link' | 'dismiss',
  input: { lead_bureau_id?: number; note?: string },
  actor: Actor,
): void {
  const r = current(id)
  if (r.state !== 'OPEN') throw new Error('This flag has already been decided.')
  const note = input.note?.trim() || null
  const base = { note, decided_by_name: actor.name, decided_at: new Date().toISOString() }
  if (mode === 'link') {
    const ids = (r.cases ?? []).map((c) => c.bureau_id)
    if (input.lead_bureau_id === undefined || !ids.includes(input.lead_bureau_id)) {
      throw new Error('Lead bureau must be one of the bureaus involved.')
    }
    decisions.set(id, { ...base, state: 'CONFIRMED', lead_bureau_id: input.lead_bureau_id })
  } else {
    decisions.set(id, { ...base, state: 'DISMISSED' })
  }
}
