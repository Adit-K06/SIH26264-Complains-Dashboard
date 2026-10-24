import { api } from './client'
import { USE_MOCKS } from './config'
import type { Actor, Attachment, CaseDetail, WorkflowInput } from './caseDetailTypes'
import { mockAttachmentBlob, mockGetCase, mockUpload, mockWorkflow } from './mocks/caseDetail'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

// GET /cases/{id}
export async function getCase(id: number): Promise<CaseDetail> {
  if (USE_MOCKS) {
    await delay(250)
    return mockGetCase(id)
  }
  return (await api.get<CaseDetail>(`/cases/${id}`)).data
}

// POST /cases/{id}/actions | /transfer | /escalate | /dispose | /reopen
// Request bodies are assumptions (AGENTS.md gives paths only) - adjust here if P1 differs.
export async function runWorkflow(id: number, input: WorkflowInput, actor: Actor): Promise<void> {
  if (USE_MOCKS) {
    await delay(300)
    mockWorkflow(id, input, actor)
    return
  }
  const remarks = input.remarks
  switch (input.kind) {
    case 'action':
      await api.post(`/cases/${id}/actions`, {
        action_type: 'ACTION',
        remarks,
        next_action_text: input.next_action_text,
        to_status: input.start_processing ? 'UNDER_PROCESS' : undefined,
      })
      return
    case 'transfer':
      await api.post(`/cases/${id}/transfer`, { to_bureau_id: input.to_bureau_id, remarks })
      return
    case 'escalate':
      await api.post(`/cases/${id}/escalate`, { remarks })
      return
    case 'dispose':
      await api.post(`/cases/${id}/dispose`, { remarks })
      return
    case 'reopen':
      await api.post(`/cases/${id}/reopen`, { remarks })
      return
  }
}

// POST /cases/{id}/attachments  (multipart field "file")
export async function uploadAttachment(id: number, file: File, actor: Actor): Promise<Attachment> {
  if (USE_MOCKS) {
    await delay(300)
    return mockUpload(id, file, actor)
  }
  const fd = new FormData()
  fd.append('file', file)
  return (await api.post<Attachment>(`/cases/${id}/attachments`, fd)).data
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// GET /attachments/{id}  (fetched with the auth header, then saved)
export async function downloadAttachment(a: Attachment): Promise<void> {
  if (USE_MOCKS) {
    await delay(150)
    saveBlob(mockAttachmentBlob(a), a.filename)
    return
  }
  const res = await api.get<Blob>(`/attachments/${a.id}`, { responseType: 'blob' })
  saveBlob(res.data, a.filename)
}
