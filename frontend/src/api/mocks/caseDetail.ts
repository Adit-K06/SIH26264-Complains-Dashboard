// Mock data lives ONLY in src/api/mocks. Derived from the same 240 SYNTHETIC cases as the list.
// Workflow actions mutate in-memory state so the buttons work before a backend exists
// (state resets on page reload).
import { parseFilters } from '../../lib/caseFilters'
import type { CaseStatus } from '../../lib/constants'
import { BUREAUS, REGIONS } from '../../lib/lookups'
import type {
  Actor,
  ActionType,
  Attachment,
  CaseAction,
  CaseDetail,
  LinkedCase,
  OverlapInfo,
  WorkflowInput,
} from '../caseDetailTypes'
import type { CaseRow } from '../types'
import { mockQueryCases } from './cases'

const OFFICERS = ['S. Rao', 'A. Nair', 'M. Iyer', 'R. Kumar']

let cache: CaseRow[] | null = null
function allRows(): CaseRow[] {
  if (!cache) {
    cache = mockQueryCases({ ...parseFilters(new URLSearchParams()), page: 1, page_size: 1000 }).items
  }
  return cache
}
function find(id: number): CaseRow {
  const c = allRows().find((r) => r.id === id)
  if (!c) throw new Error('Case not found')
  return c
}

type Patch = Partial<Omit<CaseDetail, 'actions' | 'attachments'>>
const patches = new Map<number, Patch>()
const extraActions = new Map<number, CaseAction[]>()
const extraFiles = new Map<number, Attachment[]>()
let nextId = 90000

const bureauCode = (id?: number | null) => BUREAUS.find((b) => b.id === id)?.label ?? null

function baseActions(c: CaseRow): CaseAction[] {
  const stamp = (date: string | null | undefined, hour: number) =>
    `${date ?? '2026-01-01'}T${String(hour).padStart(2, '0')}:00:00`
  const officer = OFFICERS[c.id % OFFICERS.length]
  const mk = (
    n: number,
    type: ActionType,
    at: string,
    remarks: string,
    from: CaseStatus | null,
    to: CaseStatus | null,
    system = false,
  ): CaseAction => ({
    id: c.id * 100 + n,
    case_id: c.id,
    actor_id: system ? null : (c.id % 4) + 1,
    actor_name: system ? null : officer,
    bureau_id: c.bureau_id ?? null,
    bureau_code: c.bureau_code ?? null,
    action_type: type,
    from_status: from,
    to_status: to,
    remarks,
    attachment_id: null,
    created_at: at,
  })
  const list: CaseAction[] = [
    mk(1, 'CREATED', stamp(c.received_on, 9), 'Received via ingest API (synthetic)', null, 'PENDING', true),
    mk(2, 'ASSIGNED', stamp(c.received_on, 10), `Assigned to ${officer}`, null, null),
  ]
  if (c.status !== 'PENDING') {
    list.push(mk(3, 'ACTION', stamp(c.last_action_on, 11), 'Notice issued to institution', 'PENDING', 'UNDER_PROCESS'))
    const at = stamp(c.last_action_on, 15)
    if (c.status === 'TRANSFERRED') {
      list.push(mk(4, 'TRANSFERRED', at, 'Transferred to another bureau for handling', 'UNDER_PROCESS', 'TRANSFERRED'))
    } else if (c.status === 'ESCALATED') {
      list.push(mk(4, 'ESCALATED', at, 'Escalated to senior management', 'UNDER_PROCESS', 'ESCALATED'))
    } else if (c.status === 'DISPOSED') {
      list.push(mk(4, 'DISPOSED', at, 'Disposed after institution reply', 'UNDER_PROCESS', 'DISPOSED'))
    }
  }
  return list
}

const NEXT_TEXT: Record<CaseStatus, string | null> = {
  PENDING: 'Assign officer and begin review',
  UNDER_PROCESS: 'Await institution reply',
  ESCALATED: 'Senior management review',
  TRANSFERRED: 'Receiving bureau to review',
  DISPOSED: null,
}

function build(c: CaseRow): CaseDetail {
  const patch = patches.get(c.id) ?? {}
  const merged = { ...c, ...patch }
  const status: CaseStatus = merged.status
  const rows = allRows()
  const actions = [...baseActions(c), ...(extraActions.get(c.id) ?? [])]
  const lastRemarks = [...actions].reverse().find((a) => a.remarks)?.remarks ?? null

  let linked_cases: LinkedCase[] = []
  let lead_bureau_code: string | null = null
  let link_note: string | null = null
  let overlaps: OverlapInfo[] = []
  if (c.link_group_id) {
    const idx = rows.findIndex((r) => r.id === c.id)
    const p = rows[(idx + 1) % rows.length]
    linked_cases = [{ id: p.id, case_no: p.case_no, bureau_code: p.bureau_code ?? null }]
    lead_bureau_code = c.bureau_code ?? null
    link_note = 'Coordinating one notice to the institution (synthetic).'
  } else if (status !== 'DISPOSED') {
    const other = rows.find(
      (r) =>
        r.institution_id === c.institution_id &&
        r.id !== c.id &&
        r.status !== 'DISPOSED' &&
        r.bureau_id !== merged.bureau_id,
    )
    if (other) {
      overlaps = [
        {
          id: c.id,
          tier: 'B',
          score: 0.6 + (c.id % 30) / 100,
          other_case_id: other.id,
          other_case_no: other.case_no,
          other_bureau_code: other.bureau_code ?? null,
        },
      ]
    }
  }

  const files: Attachment[] = [...(extraFiles.get(c.id) ?? [])]
  if (c.id % 3 === 0) {
    files.unshift({
      id: c.id * 10,
      filename: 'complaint_copy.txt',
      mime: 'text/plain',
      size: 18_432,
      uploaded_by_name: OFFICERS[c.id % OFFICERS.length],
      created_at: `${c.received_on ?? '2026-01-01'}T10:15:00`,
    })
  }

  return {
    ...merged,
    aicte_permanent_id: c.institution_id ? `SYN-${String(10000 + c.institution_id).padStart(5, '0')}` : null,
    region_name: REGIONS.find((r) => r.id === c.region_id)?.label ?? null,
    assigned_officer_name: OFFICERS[c.id % OFFICERS.length],
    last_action_text: lastRemarks,
    next_action_text: NEXT_TEXT[status],
    summary: `Synthetic complaint regarding ${(c.category_name ?? 'a general matter').toLowerCase()} at the institution. This text is generated demo data (source: SYNTHETIC).`,
    complainant_ref: `CR-****${String(c.id % 10000).padStart(4, '0')}`,
    source: 'SYNTHETIC',
    needs_institution_review: false,
    linked_cases,
    lead_bureau_code,
    link_note,
    overlaps,
    ...patch, // user changes win (status, bureau, next action, ...)
    actions,
    attachments: files,
  }
}

export function mockGetCase(id: number): CaseDetail {
  return build(find(id))
}

export function mockWorkflow(id: number, input: WorkflowInput, actor: Actor): void {
  const cur = build(find(id))
  const from = cur.status
  const remarks = input.remarks?.trim() || null
  const patch: Patch = {}
  let type: ActionType = 'ACTION'
  let to: CaseStatus = from

  switch (input.kind) {
    case 'action':
      if (from === 'DISPOSED') throw new Error('Case is disposed. Reopen it first.')
      type = 'ACTION'
      if (input.start_processing && from === 'PENDING') to = 'UNDER_PROCESS'
      break
    case 'transfer':
      if (from === 'DISPOSED') throw new Error('A disposed case cannot be transferred.')
      if (!input.to_bureau_id || input.to_bureau_id === cur.bureau_id) {
        throw new Error('Choose a different bureau to transfer to.')
      }
      type = 'TRANSFERRED'
      to = 'TRANSFERRED'
      patch.bureau_id = input.to_bureau_id
      patch.bureau_code = bureauCode(input.to_bureau_id)
      break
    case 'escalate':
      if (from === 'DISPOSED') throw new Error('A disposed case cannot be escalated.')
      type = 'ESCALATED'
      to = 'ESCALATED'
      break
    case 'dispose':
      if (from !== 'UNDER_PROCESS') throw new Error('Only a case that is under process can be disposed.')
      type = 'DISPOSED'
      to = 'DISPOSED'
      break
    case 'reopen':
      if (from !== 'DISPOSED') throw new Error('Only a disposed case can be reopened.')
      if (!remarks) throw new Error('Remarks are required to reopen a case.')
      type = 'REOPENED'
      to = 'PENDING'
      break
  }

  const now = new Date()
  const act: CaseAction = {
    id: nextId++,
    case_id: id,
    actor_id: actor.id,
    actor_name: actor.name,
    bureau_id: actor.bureau_id,
    bureau_code: bureauCode(actor.bureau_id),
    action_type: type,
    from_status: from,
    to_status: to,
    remarks,
    attachment_id: null,
    created_at: now.toISOString(),
  }
  extraActions.set(id, [...(extraActions.get(id) ?? []), act])
  patches.set(id, {
    ...(patches.get(id) ?? {}),
    ...patch,
    status: to,
    last_action_on: now.toISOString().slice(0, 10),
    last_action_text: remarks ?? 'Action recorded',
    next_action_text: to === 'DISPOSED' ? null : input.next_action_text?.trim() || NEXT_TEXT[to],
  })
}

export function mockUpload(id: number, file: File, actor: Actor): Attachment {
  find(id)
  const a: Attachment = {
    id: nextId++,
    filename: file.name,
    mime: file.type,
    size: file.size,
    uploaded_by_name: actor.name,
    created_at: new Date().toISOString(),
  }
  extraFiles.set(id, [...(extraFiles.get(id) ?? []), a])
  return a
}

export function mockAttachmentBlob(a: Attachment): Blob {
  return new Blob([`Synthetic demo attachment: ${a.filename}\n`], { type: 'text/plain' })
}
