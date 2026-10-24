// Mock data lives ONLY in src/api/mocks. Every report is computed from the same 240 SYNTHETIC
// cases as the Cases list, so numbers match the other pages. SLA-based figures (beyond SLA, ageing)
// use the placeholder SLA days of the mock data, not official norms.
import { parseFilters } from '../../lib/caseFilters'
import { STATUSES, STATUS_LABEL } from '../../lib/constants'
import type { CaseStatus } from '../../lib/constants'
import { BUREAUS, REGIONS } from '../../lib/lookups'
import { OVERLAP_STATES, STATE_LABEL } from '../../lib/overlap'
import type { ReportFilters } from '../../lib/reports'
import type { ReportTable } from '../../lib/reportTable'
import type { CaseRow } from '../types'
import { mockQueryCases } from './cases'
import { mockQueryOverlaps } from './overlaps'

const DAY = 86_400_000
const dayMs = (s?: string | null) => (s ? new Date(`${s}T00:00:00`).getTime() : Number.NaN)

function casesFor(f: ReportFilters): CaseRow[] {
  const p = new URLSearchParams()
  if (f.from_date) p.set('from_date', f.from_date)
  if (f.to_date) p.set('to_date', f.to_date)
  if (f.bureau_id) p.set('bureau_id', String(f.bureau_id))
  if (f.region_id) p.set('region_id', String(f.region_id))
  if (f.category_id) p.set('category_id', String(f.category_id))
  if (f.status) p.set('status', f.status)
  return mockQueryCases({ ...parseFilters(p), page: 1, page_size: 1000 }).items
}

const isOpen = (c: CaseRow) => c.status !== 'DISPOSED'
const pct = (a: number, b: number) => (b === 0 ? 0 : Number(((a / b) * 100).toFixed(1)))

function statusCounts(cs: CaseRow[]): number[] {
  return STATUSES.map((s: CaseStatus) => cs.filter((c) => c.status === s).length)
}

function groupTable(
  firstCol: string,
  groups: Array<{ label: string; cases: CaseRow[] }>,
  todayMs: number,
): ReportTable {
  return {
    columns: [firstCol, 'Total', ...STATUSES.map((s) => STATUS_LABEL[s]), 'Beyond SLA'],
    rows: groups.map((g) => [
      g.label,
      g.cases.length,
      ...statusCounts(g.cases),
      g.cases.filter((c) => isOpen(c) && dayMs(c.expected_disposal_on) < todayMs).length,
    ]),
  }
}

function byPeriod(cs: CaseRow[], key: (received: string) => string): ReportTable {
  const map = new Map<string, { received: number; disposed: number }>()
  for (const c of cs) {
    if (!c.received_on) continue
    const k = key(c.received_on)
    const e = map.get(k) ?? { received: 0, disposed: 0 }
    e.received += 1
    if (c.status === 'DISPOSED') e.disposed += 1
    map.set(k, e)
  }
  const rows = [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  return {
    columns: ['Period', 'Received', 'Disposed (of those received)'],
    rows: rows.map(([k, e]) => [k, e.received, e.disposed]),
  }
}

export function mockReport(f: ReportFilters): ReportTable {
  const todayMs = new Date().setHours(0, 0, 0, 0)

  if (f.type === 'overlaps') {
    // Overlap flags are not filtered by the case filters in this mock.
    return {
      columns: ['State', 'Tier A', 'Tier B', 'Total'],
      rows: OVERLAP_STATES.map((state) => {
        const a = mockQueryOverlaps({ state, tier: 'A', page: 1, page_size: 1 }).total
        const b = mockQueryOverlaps({ state, tier: 'B', page: 1, page_size: 1 }).total
        return [STATE_LABEL[state], a, b, a + b]
      }),
    }
  }

  const cs = casesFor(f)

  switch (f.type) {
    case 'bureau':
      return groupTable('Bureau', BUREAUS.map((b) => ({ label: b.label, cases: cs.filter((c) => c.bureau_id === b.id) })), todayMs)
    case 'region':
      return groupTable('Region', REGIONS.map((r) => ({ label: r.label, cases: cs.filter((c) => c.region_id === r.id) })), todayMs)
    case 'institution': {
      const map = new Map<number, CaseRow[]>()
      for (const c of cs) {
        if (c.institution_id == null) continue
        const l = map.get(c.institution_id)
        if (l) l.push(c)
        else map.set(c.institution_id, [c])
      }
      const rows = [...map.entries()]
        .sort((a, b) => b[1].length - a[1].length || a[0] - b[0])
        .slice(0, 25)
        .map(([id, list]) => [
          list[0].institution_name ?? `Institution ${id}`,
          `SYN-${String(10000 + id).padStart(5, '0')}`,
          list.length,
          list.filter(isOpen).length,
          list.filter((c) => isOpen(c) && dayMs(c.expected_disposal_on) < todayMs).length,
        ])
      return { columns: ['Institution (top 25 by cases)', 'AICTE permanent ID', 'Total', 'Open', 'Beyond SLA'], rows }
    }
    case 'ageing': {
      const edges: Array<[string, number, number]> = [
        ['0-7 days', 0, 7],
        ['8-15 days', 8, 15],
        ['16-30 days', 16, 30],
        ['31-60 days', 31, 60],
        ['60+ days', 61, Number.POSITIVE_INFINITY],
      ]
      const open = cs.filter(isOpen)
      return {
        columns: ['Bureau', ...edges.map((e) => e[0]), 'Total open'],
        rows: BUREAUS.map((b) => {
          const mine = open.filter((c) => c.bureau_id === b.id)
          const counts = edges.map(([, lo, hi]) =>
            mine.filter((c) => {
              const age = Math.floor((todayMs - dayMs(c.received_on)) / DAY)
              return age >= lo && age <= hi
            }).length,
          )
          return [b.label, ...counts, mine.length]
        }),
      }
    }
    case 'disposal-rate':
      return {
        columns: ['Bureau', 'Received', 'Disposed', 'Disposal rate (%)'],
        rows: BUREAUS.map((b) => {
          const mine = cs.filter((c) => c.bureau_id === b.id)
          const done = mine.filter((c) => c.status === 'DISPOSED').length
          return [b.label, mine.length, done, pct(done, mine.length)]
        }),
      }
    case 'status':
      return {
        columns: ['Status', 'Cases', 'Share (%)'],
        rows: STATUSES.map((s) => {
          const n = cs.filter((c) => c.status === s).length
          return [STATUS_LABEL[s], n, pct(n, cs.length)]
        }),
      }
    case 'monthly':
      return byPeriod(cs, (d) => d.slice(0, 7))
    default: // quarterly
      return byPeriod(cs, (d) => `${d.slice(0, 4)} Q${Math.floor((Number(d.slice(5, 7)) - 1) / 3) + 1}`)
  }
}
