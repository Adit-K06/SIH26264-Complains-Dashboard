import { useState } from 'react'
import type { FormEvent } from 'react'
import type { WorkflowFields, WorkflowKind } from '../../api/caseDetailTypes'
import type { CaseStatus } from '../../lib/constants'
import { BUREAUS } from '../../lib/lookups'
import Modal from './Modal'

interface Cfg {
  title: string
  submit: string
  remarksLabel: string
  remarksRequired: boolean
}

const CFG: Record<WorkflowKind, Cfg> = {
  action: { title: 'Add action', submit: 'Save action', remarksLabel: 'What was done', remarksRequired: true },
  transfer: { title: 'Transfer case', submit: 'Transfer', remarksLabel: 'Remarks (optional)', remarksRequired: false },
  escalate: { title: 'Escalate case', submit: 'Escalate', remarksLabel: 'Reason (optional)', remarksRequired: false },
  dispose: { title: 'Dispose case', submit: 'Dispose', remarksLabel: 'Disposal remarks (optional)', remarksRequired: false },
  reopen: { title: 'Reopen case', submit: 'Reopen', remarksLabel: 'Reason for reopening', remarksRequired: true },
}

const FIELD = 'w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-900'
const LABEL = 'mb-1 block text-xs font-medium text-slate-600'

interface Props {
  kind: WorkflowKind
  status: CaseStatus
  bureauId?: number | null
  busy: boolean
  error: string | null
  onSubmit: (fields: WorkflowFields) => void
  onClose: () => void
}

export default function ActionDialog({ kind, status, bureauId, busy, error, onSubmit, onClose }: Props) {
  const cfg = CFG[kind]
  const [remarks, setRemarks] = useState('')
  const [next, setNext] = useState('')
  const [start, setStart] = useState(true)
  const [toBureau, setToBureau] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  function submit(e: FormEvent) {
    e.preventDefault()
    const r = remarks.trim()
    if (cfg.remarksRequired && !r) {
      setLocalError('Remarks are required.')
      return
    }
    if (kind === 'transfer' && !toBureau) {
      setLocalError('Select the bureau to transfer to.')
      return
    }
    setLocalError(null)
    onSubmit({
      remarks: r || undefined,
      next_action_text: kind === 'action' ? next.trim() || undefined : undefined,
      start_processing: kind === 'action' && status === 'PENDING' ? start : undefined,
      to_bureau_id: kind === 'transfer' ? Number(toBureau) : undefined,
    })
  }

  const shownError = localError ?? error

  return (
    <Modal title={cfg.title} onClose={() => (busy ? undefined : onClose())}>
      <form onSubmit={submit} className="space-y-3">
        {kind === 'transfer' && (
          <div>
            <label htmlFor="ad-bureau" className={LABEL}>
              Transfer to bureau
            </label>
            <select id="ad-bureau" className={FIELD} value={toBureau} onChange={(e) => setToBureau(e.target.value)}>
              <option value="">Select bureau…</option>
              {BUREAUS.filter((b) => b.id !== bureauId).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label htmlFor="ad-remarks" className={LABEL}>
            {cfg.remarksLabel}
          </label>
          <textarea
            id="ad-remarks"
            autoFocus
            rows={3}
            className={FIELD}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
        </div>

        {kind === 'action' && (
          <>
            <div>
              <label htmlFor="ad-next" className={LABEL}>
                Next action required (optional)
              </label>
              <input id="ad-next" className={FIELD} value={next} onChange={(e) => setNext(e.target.value)} />
            </div>
            {status === 'PENDING' && (
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={start} onChange={(e) => setStart(e.target.checked)} />
                Move case to Under process
              </label>
            )}
          </>
        )}

        {shownError && (
          <p role="alert" className="text-sm text-red-700">
            {shownError}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {busy ? 'Saving…' : cfg.submit}
          </button>
        </div>
      </form>
    </Modal>
  )
}
