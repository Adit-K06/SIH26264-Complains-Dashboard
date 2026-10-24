import { STATUSES } from './constants'
import type { CaseStatus } from './constants'

// Report types: exact list from AGENTS.md (GET /reports/{type}?format=csv|json|pdf)
export const REPORT_TYPES = [
  'bureau',
  'region',
  'institution',
  'ageing',
  'disposal-rate',
  'status',
  'overlaps',
  'monthly',
  'quarterly',
] as const
export type ReportType = (typeof REPORT_TYPES)[number]

export const REPORT_LABEL: Record<ReportType, string> = {
  bureau: 'Bureau-wise',
  region: 'Region-wise',
  institution: 'Institution-wise',
  ageing: 'Ageing',
  'disposal-rate': 'Disposal rate',
  status: 'Status-wise',
  overlaps: 'Overlaps',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
}

export type ReportFormat = 'csv' | 'json' | 'pdf'

export interface ReportFilters {
  type: ReportType
  from_date: string // YYYY-MM-DD or ''
  to_date: string
  bureau_id?: number
  region_id?: number
  category_id?: number
  status: '' | CaseStatus
}

const DATE = /^\d{4}-\d{2}-\d{2}$/

export function parseReportFilters(p: URLSearchParams): ReportFilters {
  const posInt = (key: string): number | undefined => {
    const n = Number(p.get(key))
    return Number.isInteger(n) && n > 0 ? n : undefined
  }
  const date = (key: string) => {
    const v = p.get(key) ?? ''
    return DATE.test(v) ? v : ''
  }
  const t = p.get('type') ?? ''
  const s = p.get('status') ?? ''
  return {
    type: (REPORT_TYPES as readonly string[]).includes(t) ? (t as ReportType) : 'bureau',
    from_date: date('from_date'),
    to_date: date('to_date'),
    bureau_id: posInt('bureau_id'),
    region_id: posInt('region_id'),
    category_id: posInt('category_id'),
    status: (STATUSES as readonly string[]).includes(s) ? (s as CaseStatus) : '',
  }
}

/** Browser URL: only non-default values are written. */
export function toSearchParams(f: ReportFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.type !== 'bureau') p.set('type', f.type)
  if (f.from_date) p.set('from_date', f.from_date)
  if (f.to_date) p.set('to_date', f.to_date)
  if (f.bureau_id) p.set('bureau_id', String(f.bureau_id))
  if (f.region_id) p.set('region_id', String(f.region_id))
  if (f.category_id) p.set('category_id', String(f.category_id))
  if (f.status) p.set('status', f.status)
  return p
}

/** Query string for GET /reports/{type}. Filter names follow the case filters in AGENTS.md. */
export function toApiParams(f: ReportFilters, format: ReportFormat): Record<string, string | number> {
  const out: Record<string, string | number> = { format }
  if (f.from_date) out.from_date = f.from_date
  if (f.to_date) out.to_date = f.to_date
  if (f.bureau_id) out.bureau_id = f.bureau_id
  if (f.region_id) out.region_id = f.region_id
  if (f.category_id) out.category_id = f.category_id
  if (f.status) out.status = f.status
  return out
}
