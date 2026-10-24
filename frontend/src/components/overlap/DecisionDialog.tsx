import { useState } from 'react'
import type { FormEvent } from 'react'
import type { OverlapRow } from '../../api/overlapTypes'
import { BUREAUS } from '../../lib/lookups'
import { involvedBureauIds } from '../../lib/overlap'
import Modal from '../case/Modal'

const FIELD = 'w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-900'
const LABEL = 'mb-1 block text-xs font-medium text-slate-600'

export default function DecisionDialog({
  mode,
  row,
  busy,
  error,
  onSubmit,
  onClose,
}: {
  mode: 'link' | 'dismiss'
  row: OverlapRow
  busy: boolean
  error: string | null
  onSubmit: (input: { lead_bureau_id?: number; note?: string }) => void
  onClose: () => void
}) {
  const [lead, setLead] = useState('')
  const [note, setNote] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const ids = involvedBureauIds(row)
  const options = ids.length > 0 ? BUREAUS.filter((b) => ids.includes(b.id)) : BUREAUS

  function submit(e: FormEvent) {
    e.preventDefault()
    if (mode === 'link' && !lead) {
      setLocalError('Select the lead bureau.')
      return
    }
    setLocalError(null)
    onSubmit({
      lead_bureau_id: mode === 'link' ? Number(lead) : undefined,
      note: note.trim() || undefined,
    })
  }

  const shown = localError ?? error

  return (
    <Modal
      title={mode === 'link' ? 'Link as related cases' : 'Dismiss overlap flag'}
      onClose={() => (busy ? undefined : onClose())}
    >
      <form onSubmit={submit} className="space-y-3">
        <p className="text-sm text-slate-600">
          {mode === 'link'
            ? 'The cases will be linked and the flag marked as confirmed. Name the lead bureau and add a shared coordination note.'
            : 'The flag will be marked dismissed and will not be raised again unless the cases change.'}
        </p>

        {mode === 'link' && (
          <div>
            <label htmlFor="dd-lead" className={LABEL}>
              Lead bureau
            </label>
            <select id="dd-lead" className={FIELD} value={lead} onChange={(e) => setLead(e.target.value)}>
              <option value="">Select bureau…</option>
              {options.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label htmlFor="dd-note" className={LABEL}>
            {mode === 'link' ? 'Coordination note (optional)' : 'Reason (optional)'}
          </label>
          <textarea
            id="dd-note"
            autoFocus
            rows={3}
            className={FIELD}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>

        {shown && (
          <p role="alert" className="text-sm text-red-700">
            {shown}
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
            {busy ? 'Saving…' : mode === 'link' ? 'Link cases' : 'Dismiss flag'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
