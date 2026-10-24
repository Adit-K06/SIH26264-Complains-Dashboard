import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { OverlapCase, OverlapRow } from '../../api/overlapTypes'
import { fmtDate } from '../../lib/format'
import { BUREAUS } from '../../lib/lookups'
import { bureausOf } from '../../lib/overlap'
import StatusBadge from '../StatusBadge'
import { OverlapStateBadge, ReasonChips, ScoreBar, TierBadge } from './OverlapBits'

function Line({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[6.5rem_1fr] gap-2 py-1 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="min-w-0 break-words text-slate-900">{children}</dd>
    </div>
  )
}

function CaseCard({ c }: { c: OverlapCase }) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <Link to={`/cases/${c.id}`} className="font-medium text-teal hover:underline">
          {c.case_no}
        </Link>
        <StatusBadge status={c.status} />
      </div>
      <p className="mb-1 text-sm text-slate-700">{c.summary ?? 'No summary provided.'}</p>
      <dl className="divide-y divide-slate-100">
        <Line label="Bureau">{c.bureau_code ?? '—'}</Line>
        <Line label="Category">{c.category_name ?? '—'}</Line>
        <Line label="Officer">{c.assigned_officer_name ?? '—'}</Line>
        <Line label="Received">{fmtDate(c.received_on)}</Line>
        <Line label="Last action">
          {c.last_action_text ?? '—'}
          {c.last_action_on ? ` (${fmtDate(c.last_action_on)})` : ''}
        </Line>
        <Line label="Next action">{c.next_action_text ?? '—'}</Line>
      </dl>
    </article>
  )
}

export default function OverlapDrawer({
  row,
  blocked,
  onClose,
  onDecide,
}: {
  row: OverlapRow
  blocked: boolean // true while a dialog is open on top (Escape then closes the dialog only)
  onClose: () => void
  onDecide: (mode: 'link' | 'dismiss') => void
}) {
  useEffect(() => {
    if (blocked) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [blocked, onClose])

  const cases = row.cases ?? []
  const leadLabel = BUREAUS.find((b) => b.id === row.lead_bureau_id)?.label

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end bg-slate-900/40"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Overlap review"
        className="flex h-full w-full max-w-4xl flex-col overflow-y-auto bg-slate-50 shadow-xl"
      >
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-slate-900">
              {row.institution_name ?? `Institution ${row.institution_id}`}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-600">
              <TierBadge tier={row.tier} />
              <OverlapStateBadge state={row.state} />
              <span>{bureausOf(row).join(' + ')}</span>
              <ScoreBar score={row.score} />
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
          >
            Close
          </button>
        </header>

        <div className="space-y-4 p-5">
          <section>
            <h3 className="mb-1 text-sm font-semibold text-slate-800">Why flagged</h3>
            <ReasonChips reasons={row.reasons} />
            <p className="mt-2 text-sm text-slate-600">
              {row.tier === 'A'
                ? 'This institution has open cases in more than one bureau. Review the cases below and coordinate.'
                : 'These two cases scored as a likely match for the same issue. The system only flags; an officer decides.'}
            </p>
          </section>

          <section>
            <h3 className="mb-1 text-sm font-semibold text-slate-800">
              {row.tier === 'B' ? 'Cases side by side' : `Open cases (${cases.length})`}
            </h3>
            {cases.length === 0 ? (
              <p className="text-sm text-slate-500">Case details are not available for this flag.</p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {cases.map((c) => (
                  <CaseCard key={c.id} c={c} />
                ))}
              </div>
            )}
          </section>

          <section className="rounded-md border border-slate-200 bg-white p-4">
            {row.state === 'OPEN' ? (
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onDecide('link')}
                  className="rounded border border-slate-800 bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
                >
                  Link as related
                </button>
                <button
                  type="button"
                  onClick={() => onDecide('dismiss')}
                  className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Dismiss
                </button>
              </div>
            ) : (
              <div className="space-y-1 text-sm text-slate-700">
                <p>
                  Decision: <strong>{row.state === 'CONFIRMED' ? 'Linked (confirmed)' : 'Dismissed'}</strong>
                  {leadLabel ? ` · Lead bureau: ${leadLabel}` : ''}
                  {row.decided_by_name ? ` · by ${row.decided_by_name}` : ''}
                </p>
                {row.note && <p>Note: {row.note}</p>}
              </div>
            )}
          </section>
        </div>
      </aside>
    </div>
  )
}
