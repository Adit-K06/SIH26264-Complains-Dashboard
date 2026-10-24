import { Link } from 'react-router-dom'
import type { CaseRow } from '../../api/types'
import { fmtDate } from '../../lib/format'
import StatusBadge from '../StatusBadge'
import { EmptyState } from '../states'

interface Ev {
  key: string
  date: string // YYYY-MM-DD
  label: string
  c: CaseRow
}

/**
 * Built only from dates on the case rows (received / last action). The full per-case
 * history lives on each Case detail page (case_actions).
 */
export default function InstitutionTimeline({ cases }: { cases: CaseRow[] }) {
  const events: Ev[] = []
  for (const c of cases) {
    if (c.received_on) events.push({ key: `${c.id}-r`, date: c.received_on, label: 'Received', c })
    if (c.last_action_on && c.last_action_on !== c.received_on) {
      events.push({ key: `${c.id}-a`, date: c.last_action_on, label: 'Last action recorded', c })
    }
  }
  if (events.length === 0) return <EmptyState text="No dated events for this institution." />

  events.sort((a, b) => b.date.localeCompare(a.date) || b.key.localeCompare(a.key))

  return (
    <div>
      <p className="mb-3 text-xs text-slate-500">
        Received and last-action dates across all bureaus, newest first. Open a case for its full action history.
      </p>
      <ol className="ml-2 border-l border-slate-200">
        {events.map((e) => (
          <li key={e.key} className="relative pb-3 pl-5 last:pb-0">
            <span
              className={`absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full ${
                e.label === 'Received' ? 'bg-slate-400' : 'bg-sky-600'
              }`}
              aria-hidden
            />
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
              <span className="text-xs text-slate-500">{fmtDate(e.date)}</span>
              <span className="font-medium text-slate-900">{e.label}</span>
              <Link to={`/cases/${e.c.id}`} className="text-teal hover:underline">
                {e.c.case_no}
              </Link>
              {e.c.bureau_code && <span className="text-xs text-slate-600">({e.c.bureau_code})</span>}
              <StatusBadge status={e.c.status} />
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
