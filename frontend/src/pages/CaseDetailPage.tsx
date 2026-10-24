import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { errorMessage } from '../api/client'
import { getCase, runWorkflow } from '../api/caseDetail'
import type { CaseDetail, WorkflowFields, WorkflowInput, WorkflowKind } from '../api/caseDetailTypes'
import AsyncBoundary from '../components/AsyncBoundary'
import ActionDialog from '../components/case/ActionDialog'
import CaseAttachments from '../components/case/CaseAttachments'
import CaseTimeline from '../components/case/CaseTimeline'
import SlaBadge from '../components/SlaBadge'
import StatusBadge from '../components/StatusBadge'
import { EmptyState } from '../components/states'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { OVERLAP_HEADING } from '../lib/constants'
import { allowedActions, canUpload, isOpen } from '../lib/casePermissions'
import { daysOverdue, fmtDate } from '../lib/format'

const CARD = 'rounded-md border border-slate-200 bg-white'
const CARD_H = 'border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800'
const BTN = 'rounded border px-3 py-1.5 text-sm font-medium disabled:opacity-50'

const BUTTONS: Record<WorkflowKind, { label: string; cls: string }> = {
  action: { label: 'Add action', cls: 'border-slate-800 bg-slate-800 text-white hover:bg-slate-700' },
  transfer: { label: 'Transfer', cls: 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50' },
  escalate: { label: 'Escalate', cls: 'border-red-300 bg-white text-red-700 hover:bg-red-50' },
  dispose: { label: 'Dispose', cls: 'border-green-300 bg-white text-green-700 hover:bg-green-50' },
  reopen: { label: 'Reopen', cls: 'border-amber-300 bg-white text-amber-700 hover:bg-amber-50' },
}

const DONE_TEXT: Record<WorkflowKind, string> = {
  action: 'Action recorded.',
  transfer: 'Case transferred.',
  escalate: 'Case escalated.',
  dispose: 'Case disposed.',
  reopen: 'Case reopened.',
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[8.5rem_1fr] gap-2 py-1.5 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="min-w-0 break-words text-slate-900">{children}</dd>
    </div>
  )
}

function CaseDetailBody({ c }: { c: CaseDetail }) {
  const user = useCurrentUser()
  const qc = useQueryClient()
  const [dialog, setDialog] = useState<WorkflowKind | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const allowed = allowedActions(user, c)
  const overdue = isOpen(c.status) ? daysOverdue(c.expected_disposal_on) : null
  const linked = c.linked_cases ?? []
  const overlaps = c.overlaps ?? []

  const mut = useMutation({
    mutationFn: (input: WorkflowInput) => runWorkflow(c.id, input, user),
    onSuccess: (_data, input) => {
      setDialog(null)
      setNotice(DONE_TEXT[input.kind])
      void qc.invalidateQueries({ queryKey: ['case', c.id] })
      void qc.invalidateQueries({ queryKey: ['cases'] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  function open(kind: WorkflowKind) {
    mut.reset()
    setNotice(null)
    setDialog(kind)
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <section className={`${CARD} px-4 py-3`}>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold text-slate-900">{c.case_no}</h1>
          <StatusBadge status={c.status} />
          <SlaBadge
            status={c.status}
            expected_disposal_on={c.expected_disposal_on}
            received_on={c.received_on}
          />
          {c.priority && (
            <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600">
              {c.priority} priority
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-slate-600">
          {c.category_name ?? 'Uncategorised'} ·{' '}
          {c.institution_name ?? 'Institution not resolved'}
          {c.aicte_permanent_id ? ` (${c.aicte_permanent_id})` : ''}
          {c.institution_id ? (
            <>
              {' · '}
              <Link to={`/cases?institution_id=${c.institution_id}`} className="text-teal hover:underline">
                All cases of this institution
              </Link>
            </>
          ) : null}
        </p>
      </section>

      {notice && (
        <div
          role="status"
          className="flex items-center justify-between rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800"
        >
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Banners */}
      {linked.length > 0 && (
        <div role="note" className="rounded-md border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm text-indigo-900">
          Linked with{' '}
          {linked.map((l, i) => (
            <span key={l.id}>
              {i > 0 && ', '}
              <Link to={`/cases/${l.id}`} className="font-medium underline">
                {l.case_no}
              </Link>
            </span>
          ))}
          {c.lead_bureau_code ? ` - Lead: ${c.lead_bureau_code}` : ''}
          {c.link_note && <div className="mt-0.5 text-xs text-indigo-800">Note: {c.link_note}</div>}
        </div>
      )}
      {overlaps.length > 0 && (
        <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          <div className="font-semibold">{OVERLAP_HEADING}</div>
          <ul className="mt-0.5 space-y-0.5">
            {overlaps.map((o) => (
              <li key={o.id}>
                {o.other_case_id ? (
                  <Link to={`/cases/${o.other_case_id}`} className="underline">
                    {o.other_case_no ?? `Case ${o.other_case_id}`}
                  </Link>
                ) : (
                  (o.other_case_no ?? 'Multiple bureaus')
                )}
                {o.other_bureau_code ? ` (${o.other_bureau_code})` : ''} · Tier {o.tier}
                {o.score !== null ? ` · score ${o.score.toFixed(2)}` : ''}
              </li>
            ))}
          </ul>
          <Link to="/overlaps?state=OPEN" className="mt-1 inline-block text-xs underline">
            Open Overlap Center
          </Link>
        </div>
      )}
      {c.needs_institution_review && (
        <div role="note" className="rounded-md border border-slate-300 bg-slate-50 px-4 py-2 text-sm text-slate-700">
          The institution for this case is not confirmed and is waiting for review.
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-3">
        {/* Left: summary, timeline, attachments */}
        <div className="space-y-3 lg:col-span-2">
          <section className={CARD}>
            <h2 className={CARD_H}>Summary</h2>
            <p className="px-4 py-3 text-sm text-slate-800">{c.summary || 'No summary provided.'}</p>
          </section>

          <section className={CARD}>
            <h2 className={CARD_H}>Action history</h2>
            <div className="px-4 py-3">
              <CaseTimeline actions={c.actions} />
            </div>
          </section>

          <section className={CARD}>
            <h2 className={CARD_H}>Attachments</h2>
            <div className="px-4 py-3">
              <CaseAttachments caseId={c.id} attachments={c.attachments} canUpload={canUpload(user, c)} />
            </div>
          </section>
        </div>

        {/* Right: actions + details */}
        <div className="space-y-3">
          <section className={CARD}>
            <h2 className={CARD_H}>Actions</h2>
            <div className="px-4 py-3">
              {allowed.length === 0 ? (
                <p className="text-sm text-slate-500">
                  You have read-only access to this case.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {allowed.map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => open(k)}
                      className={`${BTN} ${BUTTONS[k].cls}`}
                    >
                      {BUTTONS[k].label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>

          <section className={CARD}>
            <h2 className={CARD_H}>Case details</h2>
            <dl className="divide-y divide-slate-100 px-4 py-1">
              <Row label="Handled by">{c.bureau_code ?? '—'}</Row>
              <Row label="Officer">{c.assigned_officer_name ?? '—'}</Row>
              <Row label="Region">{c.region_name ?? '—'}</Row>
              <Row label="Received">{fmtDate(c.received_on)}</Row>
              <Row label="Expected disposal">
                {fmtDate(c.expected_disposal_on)}
                {overdue !== null && overdue > 0 && (
                  <span className="ml-1 text-red-700">
                    ({overdue} day{overdue === 1 ? '' : 's'} beyond due)
                  </span>
                )}
              </Row>
              <Row label="Last action">
                {c.last_action_text ?? '—'}
                {c.last_action_on ? ` (${fmtDate(c.last_action_on)})` : ''}
              </Row>
              <Row label="Next action">{c.next_action_text ?? '—'}</Row>
              <Row label="Complainant ref">{c.complainant_ref ?? '—'}</Row>
              <Row label="Source">{c.source ?? '—'}</Row>
            </dl>
          </section>
        </div>
      </div>

      {dialog && (
        <ActionDialog
          kind={dialog}
          status={c.status}
          bureauId={c.bureau_id}
          busy={mut.isPending}
          error={mut.isError ? errorMessage(mut.error) : null}
          onSubmit={(fields: WorkflowFields) => mut.mutate({ kind: dialog, ...fields })}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  )
}

function CaseDetailLoader({ id }: { id: number }) {
  const query = useQuery({
    queryKey: ['case', id],
    queryFn: () => getCase(id),
    refetchInterval: 45_000,
  })
  return (
    <AsyncBoundary query={query} height={420}>
      {(c) => <CaseDetailBody key={c.id} c={c} />}
    </AsyncBoundary>
  )
}

export default function CaseDetailPage() {
  const { id: idParam } = useParams<{ id: string }>()
  const id = Number(idParam)
  const valid = Number.isInteger(id) && id > 0

  return (
    <div className="mx-auto max-w-[1400px] space-y-3">
      <Link to="/cases" className="inline-flex items-center gap-1 text-sm text-teal hover:underline">
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Back to cases
      </Link>
      {valid ? <CaseDetailLoader id={id} /> : <EmptyState text="Invalid case id." />}
    </div>
  )
}
