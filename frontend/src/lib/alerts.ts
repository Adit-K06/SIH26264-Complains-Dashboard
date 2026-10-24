// Alert types: exact strings from AGENTS.md.
export const ALERT_TYPES = ['OVERLAP', 'REMINDER', 'DUE_SOON', 'OVERDUE', 'ESCALATION'] as const
export type AlertType = (typeof ALERT_TYPES)[number]

export const ALERT_LABEL: Record<AlertType, string> = {
  OVERLAP: 'Overlap',
  REMINDER: 'Reminder',
  DUE_SOON: 'Due soon',
  OVERDUE: 'Overdue',
  ESCALATION: 'Escalation',
}

export const ALERT_BADGE: Record<AlertType, string> = {
  OVERLAP: 'border-indigo-200 bg-indigo-50 text-indigo-800',
  REMINDER: 'border-slate-200 bg-slate-50 text-slate-700',
  DUE_SOON: 'border-amber-200 bg-amber-50 text-amber-800',
  OVERDUE: 'border-red-200 bg-red-50 text-red-700',
  ESCALATION: 'border-red-300 bg-red-100 text-red-800',
}

export interface AlertFilters {
  unread: boolean
  type: '' | AlertType
  page: number
  page_size: number
}

export const DEFAULT_PAGE_SIZE = 20

export function parseAlertFilters(p: URLSearchParams): AlertFilters {
  const posInt = (key: string): number | undefined => {
    const n = Number(p.get(key))
    return Number.isInteger(n) && n > 0 ? n : undefined
  }
  const t = p.get('type') ?? ''
  const unread = p.get('unread')
  return {
    unread: unread === 'true' || unread === '1',
    type: (ALERT_TYPES as readonly string[]).includes(t) ? (t as AlertType) : '',
    page: posInt('page') ?? 1,
    page_size: Math.min(posInt('page_size') ?? DEFAULT_PAGE_SIZE, 100),
  }
}

/** Browser URL: only non-default values are written. */
export function toSearchParams(f: AlertFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.unread) p.set('unread', 'true')
  if (f.type) p.set('type', f.type)
  if (f.page > 1) p.set('page', String(f.page))
  if (f.page_size !== DEFAULT_PAGE_SIZE) p.set('page_size', String(f.page_size))
  return p
}

/** Request to GET /alerts. */
export function toApiParams(f: AlertFilters): Record<string, string | number> {
  const out: Record<string, string | number> = { page: f.page, page_size: f.page_size }
  if (f.unread) out.unread = 'true'
  if (f.type) out.type = f.type
  return out
}

export function fmtWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
