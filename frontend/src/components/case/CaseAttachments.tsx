import { useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Paperclip } from 'lucide-react'
import { errorMessage } from '../../api/client'
import { downloadAttachment, uploadAttachment } from '../../api/caseDetail'
import type { Attachment } from '../../api/caseDetailTypes'
import { useCurrentUser } from '../../hooks/useCurrentUser'
import { EmptyState } from '../states'

const MAX_BYTES = 5 * 1024 * 1024
const ALLOWED = ['application/pdf', 'image/jpeg', 'image/png']

const fmtSize = (n: number) =>
  n >= 1_048_576 ? `${(n / 1_048_576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`

export default function CaseAttachments({
  caseId,
  attachments,
  canUpload,
}: {
  caseId: number
  attachments: Attachment[]
  canUpload: boolean
}) {
  const user = useCurrentUser()
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const upload = useMutation({
    mutationFn: (f: File) => uploadAttachment(caseId, f, user),
    onSuccess: () => {
      setMsg(null)
      void qc.invalidateQueries({ queryKey: ['case', caseId] })
    },
    onError: (e) => setMsg(errorMessage(e)),
  })

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    if (!ALLOWED.includes(f.type)) {
      setMsg('Only PDF, JPG or PNG files are allowed.')
      return
    }
    if (f.size > MAX_BYTES) {
      setMsg('File is larger than 5 MB.')
      return
    }
    setMsg(null)
    upload.mutate(f)
  }

  async function onDownload(a: Attachment) {
    try {
      await downloadAttachment(a)
    } catch (e) {
      setMsg(errorMessage(e))
    }
  }

  return (
    <div className="space-y-2">
      {attachments.length === 0 ? (
        <EmptyState text="No attachments." />
      ) : (
        <ul className="divide-y divide-slate-100 text-sm">
          {attachments.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-3 py-2">
              <span className="flex min-w-0 items-center gap-2">
                <Paperclip className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
                <span className="truncate text-slate-800">{a.filename}</span>
                <span className="shrink-0 text-xs text-slate-500">{fmtSize(a.size)}</span>
              </span>
              <button
                type="button"
                onClick={() => void onDownload(a)}
                className="inline-flex items-center gap-1 text-teal hover:underline"
              >
                <Download className="h-4 w-4" aria-hidden />
                Download
              </button>
            </li>
          ))}
        </ul>
      )}

      {msg && (
        <p role="alert" className="text-sm text-red-700">
          {msg}
        </p>
      )}

      {canUpload && (
        <div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            className="hidden"
            onChange={onPick}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={upload.isPending}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {upload.isPending ? 'Uploading…' : 'Attach document'}
          </button>
          <span className="ml-2 text-xs text-slate-500">PDF, JPG or PNG, up to 5 MB</span>
        </div>
      )}
    </div>
  )
}
