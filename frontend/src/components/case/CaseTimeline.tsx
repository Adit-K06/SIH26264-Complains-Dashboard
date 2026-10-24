import type { ActionType, CaseAction } from '../../api/caseDetailTypes'
import { STATUS_LABEL } from '../../lib/constants'
import { EmptyState } from '../states'

const DOT: Record<ActionType, string> = {
  CREATED: 'bg-slate-400',
  ASSIGNED: 'bg-blue-500',
  ACTION: 'bg-sky-600',
  TRANSFERRED: 'bg-purple-600',
  ESCALATED: 'bg-red-600',
  LINKED: 'bg-indigo-500',
  NOTE: 'bg-slate-500',
  DISPOSED: 'bg-green-600',
  REOPENED: 'bg-amber-600',
}

const LABEL: Record<ActionType, string> = {
  CREATED: 'Created',
  ASSIGNED: 'Assigned',
  ACTION: 'Action',
  TRANSFERRED: 'Transferred',
  ESCALATED: 'Escalated',
  LINKED: 'Linked',
  NOTE: 'Note',
  DISPOSED: 'Disposed',
  REOPENED: 'Reopened',
}

function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function CaseTimeline({ actions }: { actions: CaseAction[] }) {
  if (actions.length === 0) return <EmptyState text="No actions recorded yet." />

  // Append-only history, newest first.
  const sorted = [...actions].sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id)

  return (
    <ol className="ml-2 border-l border-slate-200">
      {sorted.map((a) => {
        const change =
          a.from_status && a.to_status && a.from_status !== a.to_status
            ? `${STATUS_LABEL[a.from_status]} → ${STATUS_LABEL[a.to_status]}`
            : null
        return (
          <li key={a.id} className="relative pb-4 pl-5 last:pb-0">
            <span
              className={`absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full ${DOT[a.action_type]}`}
              aria-hidden
            />
            <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <span className="font-medium text-slate-900">{LABEL[a.action_type]}</span>
              {change && <span className="text-xs text-slate-500">{change}</span>}
              <span className="text-xs text-slate-500">{fmtDateTime(a.created_at)}</span>
            </div>
            <div className="text-xs text-slate-600">
              {a.actor_name ?? 'System'}
              {a.bureau_code ? ` (${a.bureau_code})` : ''}
            </div>
            {a.remarks && <p className="mt-0.5 text-sm text-slate-700">{a.remarks}</p>}
          </li>
        )
      })}
    </ol>
  )
}
