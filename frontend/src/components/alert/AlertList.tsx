import { Link } from 'react-router-dom'
import type { Alert } from '../../api/alertTypes'
import { ALERT_BADGE, ALERT_LABEL, fmtWhen } from '../../lib/alerts'
import { fmtDate } from '../../lib/format'

/** Click-through target: the case if there is one, else the institution. */
function targetOf(a: Alert): string | null {
  if (a.case_id) return `/cases/${a.case_id}`
  if (a.institution_id) return `/institutions/${a.institution_id}`
  return null
}

export default function AlertList({
  alerts,
  pendingId,
  onMarkRead,
}: {
  alerts: Alert[]
  pendingId?: number
  onMarkRead: (id: number) => void
}) {
  return (
    <ul>
      {alerts.map((a) => {
        const unread = !a.read_at
        const target = targetOf(a)
        const msgCls = `text-sm ${unread ? 'font-semibold text-slate-900' : 'text-slate-700'}`
        return (
          <li
            key={a.id}
            className={`flex items-start gap-3 border-b border-slate-100 px-4 py-3 ${unread ? 'bg-sky-50' : ''}`}
          >
            <span
              className={`mt-2 h-2 w-2 shrink-0 rounded-full ${unread ? 'bg-sky-600' : 'bg-transparent'}`}
              aria-hidden
            />
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded border px-1.5 py-0.5 text-xs font-medium ${ALERT_BADGE[a.type]}`}>
                  {ALERT_LABEL[a.type]}
                </span>
                {unread && <span className="sr-only">Unread</span>}
              </div>

              {target ? (
                <Link
                  to={target}
                  onClick={() => {
                    if (unread) onMarkRead(a.id) // opening the item counts as reading it
                  }}
                  className={`${msgCls} block hover:underline`}
                >
                  {a.message}
                </Link>
              ) : (
                <p className={msgCls}>{a.message}</p>
              )}

              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
                {(a.case_no || a.case_id) && <span>{a.case_no ?? `Case #${a.case_id}`}</span>}
                {a.institution_name && <span>{a.institution_name}</span>}
                {a.due_on && <span>Due {fmtDate(a.due_on.slice(0, 10))}</span>}
                <span>Raised {fmtWhen(a.created_at)}</span>
              </div>
            </div>

            {unread && (
              <button
                type="button"
                onClick={() => onMarkRead(a.id)}
                disabled={pendingId === a.id}
                className="shrink-0 rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                {pendingId === a.id ? 'Saving…' : 'Mark read'}
              </button>
            )}
          </li>
        )
      })}
    </ul>
  )
}
