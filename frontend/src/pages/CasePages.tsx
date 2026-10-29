import { FormEvent, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeft, ArrowRight, Check, ExternalLink, Link2, Plus, Search, X } from 'lucide-react'
import { casesApi, dashboardApi, institutionsApi, overlapsApi, type CaseFilters } from '../api'
import { useAuth } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, formatDate, formatDateTime, LoadingState, PageHeader, SectionTitle, SlaBadge, StatusBadge } from '../components/Shared'
import type { CaseRecord } from '../types'

const statusChoices = ['PENDING', 'UNDER_PROCESS', 'DISPOSED', 'TRANSFERRED', 'ESCALATED']
const priorityChoices = ['LOW', 'MEDIUM', 'HIGH']

export function CasesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const status = searchParams.get('status') ?? ''
  const priority = searchParams.get('priority') ?? ''
  const linked = searchParams.get('linked') ?? ''
  const beyondSla = searchParams.get('beyond_sla') === 'true'
  const page = Math.max(1, Number(searchParams.get('page') ?? 1) || 1)
  const pageSize = 10
  const filters: CaseFilters = { q: q || undefined, status: status || undefined, priority: priority || undefined, linked: linked ? linked === 'true' : undefined, beyond_sla: beyondSla || undefined, page, page_size: pageSize }
  const query = useQuery({ queryKey: ['cases', filters], queryFn: () => casesApi.list(filters) })

  function updateParam(key: string, value: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      if (value) next.set(key, value)
      else next.delete(key)
      if (key !== 'page') next.delete('page')
      return next
    })
  }

  return (
    <>
      <PageHeader title="Cases" helper="Find a complaint, see its next step, and check whether it is nearing its due date." />
      <Card className="mb-5 p-4">
        <div className="grid gap-3 md:grid-cols-[minmax(240px,1fr)_190px_150px_160px_160px]">
          <label className="relative block text-xs font-semibold text-slate-600">Search cases<input className="form-control mt-1.5 pl-9" value={q} onChange={(event) => updateParam('q', event.target.value)} placeholder="Case number, institution, or words" /><Search className="absolute left-3 top-[34px] h-4 w-4 text-slate-400" /></label>
          <label className="text-xs font-semibold text-slate-600">Status<select className="form-control mt-1.5" value={status} onChange={(event) => updateParam('status', event.target.value)}><option value="">All statuses</option>{statusChoices.map((item) => <option key={item} value={item}>{item === 'UNDER_PROCESS' ? 'Under process' : item.replace(/_/g, ' ')}</option>)}</select></label>
          <label className="text-xs font-semibold text-slate-600">Priority<select className="form-control mt-1.5" value={priority} onChange={(event) => updateParam('priority', event.target.value)}><option value="">All priorities</option>{priorityChoices.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="text-xs font-semibold text-slate-600">Coordination<select className="form-control mt-1.5" value={linked} onChange={(event) => updateParam('linked', event.target.value)}><option value="">All cases</option><option value="true">Linked cases</option><option value="false">Not linked</option></select></label>
          <label className="text-xs font-semibold text-slate-600">SLA status<select className="form-control mt-1.5" value={beyondSla ? 'true' : ''} onChange={(event) => updateParam('beyond_sla', event.target.value)}><option value="">Any due date</option><option value="true">Beyond SLA</option></select></label>
        </div>
      </Card>
      {query.isLoading && <LoadingState label="Loading cases…" />}
      {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Cases could not be loaded.'} retry={() => void query.refetch()} />}
      {query.data && query.data.items.length === 0 && <EmptyState title="No matching cases" message="Change or clear the filters to see more cases." />}
      {query.data && query.data.items.length > 0 && <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3"><p className="text-sm font-semibold text-slate-800">{query.data.total.toLocaleString()} cases</p><p className="text-xs text-slate-500">Page {query.data.page} of {Math.max(1, Math.ceil(query.data.total / query.data.page_size))}</p></div>
        <div className="overflow-x-auto"><table className="gov-table min-w-[1000px]"><thead><tr><th>Case / institution</th><th>Bureau / category</th><th>Received</th><th>Priority</th><th>SLA</th><th>Status</th><th>Link</th></tr></thead><tbody>{query.data.items.map((item) => <CaseRow key={item.id} item={item} />)}</tbody></table></div>
        <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3"><span className="text-xs text-slate-500">Showing {Math.min((page - 1) * pageSize + 1, query.data.total)}–{Math.min(page * pageSize, query.data.total)} of {query.data.total}</span><div className="flex gap-2"><button className="button-secondary" disabled={page <= 1} onClick={() => updateParam('page', String(page - 1))}>Previous</button><button className="button-secondary" disabled={page * pageSize >= query.data.total} onClick={() => updateParam('page', String(page + 1))}>Next</button></div></div>
      </Card>}
    </>
  )
}

function CaseRow({ item }: { item: CaseRecord }) {
  return <tr>
    <td><Link to={`/cases/${item.id}`} className="font-semibold text-[#153a5b] hover:text-teal-800 hover:underline">{item.case_no}</Link><p className="mt-0.5 max-w-[340px] truncate text-xs text-slate-500">{item.institution_name ?? 'Institution not resolved'}{item.aicte_permanent_id ? ` · ${item.aicte_permanent_id}` : ''}</p></td>
    <td><p className="font-medium text-slate-800">{item.bureau_code ?? '—'}</p><p className="text-xs text-slate-500">{item.category_name ?? 'Category'}</p></td>
    <td>{formatDate(item.received_on)}</td>
    <td><span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span></td>
    <td><SlaBadge dueOn={item.expected_disposal_on} status={item.status} /></td>
    <td><StatusBadge status={item.status} /></td>
    <td>{item.link_group_id ? <span title="Linked for coordination" className="inline-flex items-center gap-1 rounded-md bg-teal-50 px-2 py-1 text-xs font-semibold text-teal-800"><Link2 className="h-3.5 w-3.5" />Linked</span> : <span className="text-xs text-slate-400">—</span>}</td>
  </tr>
}

type ActionKind = 'action' | 'transfer' | 'escalate' | 'dispose' | 'reopen'
const actionLabels: Record<ActionKind, string> = { action: 'Add action', transfer: 'Transfer', escalate: 'Escalate', dispose: 'Dispose', reopen: 'Reopen' }

export function CaseDetailPage() {
  const { caseId = '' } = useParams()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [activeAction, setActiveAction] = useState<ActionKind | null>(null)
  const [success, setSuccess] = useState('')
  const [createRBOpen, setCreateRBOpen] = useState(false)
  const [createRBSummary, setCreateRBSummary] = useState('')
  const query = useQuery({ queryKey: ['case', caseId], queryFn: () => casesApi.detail(caseId), enabled: Boolean(caseId) })
  const workloadQuery = useQuery({ queryKey: ['dashboard', 'workload'], queryFn: dashboardApi.workload })
  const mutation = useMutation({
    mutationFn: ({ kind, payload }: { kind: ActionKind; payload: Record<string, string> }) => casesApi.action(caseId, kind, payload),
    onSuccess: async (_, variables) => {
      setActiveAction(null)
      setSuccess(`${actionLabels[variables.kind]} saved to the case history.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['case', caseId] }),
        queryClient.invalidateQueries({ queryKey: ['cases'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
    },
  })
  const createRBMutation = useMutation({
    mutationFn: (summary: string) => {
      const item = query.data
      const rb = workloadQuery.data?.items.find((bureau) => bureau.bureau_code === 'RB')
      if (!item?.institution_id || !rb) throw new Error('The RB bureau or institution is not available.')
      return casesApi.create({
        case_no: `RB-DEMO-${Date.now()}`,
        institution_id: item.institution_id,
        bureau_id: rb.bureau_id,
        category_id: item.category_id,
        received_on: new Date().toISOString().slice(0, 10),
        summary: summary.trim(),
        priority: item.priority,
        source_channel: 'DIRECT',
        complainant_ref: item.complainant_ref ?? undefined,
      })
    },
    onSuccess: async (created) => {
      setCreateRBOpen(false)
      setSuccess(`Created ${created.case_no}. Open Overlap Center to review the new pair.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cases'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['overlaps'] }),
      ])
    },
  })

  if (query.isLoading) return <LoadingState label="Loading case details…" />
  if (query.isError || !query.data) return <ErrorState message={query.error instanceof Error ? query.error.message : 'This case could not be loaded.'} retry={() => void query.refetch()} />
  const item = query.data
  const canManage = user?.role === 'ADMIN'
    || (user?.role === 'BUREAU_OFFICER' && user.bureau_id === item.bureau_id)
    || (user?.role === 'REGIONAL_OFFICER' && Boolean(user.region_id && (item.region_id ?? item.institution?.region_id) === user.region_id))
  const canEscalate = canManage || user?.role === 'SENIOR_MGMT'
  const rbBureau = workloadQuery.data?.items.find((bureau) => bureau.bureau_code === 'RB')
  const canCreateRB = user?.role === 'ADMIN'
    || (user?.role === 'BUREAU_OFFICER' && user.bureau_id === rbBureau?.bureau_id)
    || (user?.role === 'REGIONAL_OFFICER' && Boolean(user.region_id && (item.region_id ?? item.institution?.region_id) === user.region_id))
  const open = item.status !== 'DISPOSED'
  const buttons: ActionKind[] = []
  if (canManage && open) buttons.push('action')
  if (canManage && open && item.status !== 'TRANSFERRED') buttons.push('transfer')
  if (canEscalate && open && item.status !== 'ESCALATED') buttons.push('escalate')
  if (canManage && item.status === 'UNDER_PROCESS') buttons.push('dispose')
  if (canManage && item.status === 'DISPOSED') buttons.push('reopen')

  function submitAction(kind: ActionKind, remarks: string, toBureauId?: string) {
    mutation.mutate({ kind, payload: { remarks, ...(toBureauId ? { to_bureau_id: toBureauId } : {}) } })
  }

  return (
    <>
      <div className="mb-4"><Link to="/cases" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-teal-800"><ArrowLeft className="h-4 w-4" />Back to cases</Link></div>
      <PageHeader title={item.case_no} helper="Case tracking record and action history." action={<span className="flex flex-wrap gap-2">{item.institution_id && <button className="button-secondary" disabled={!canCreateRB || !rbBureau || createRBMutation.isPending} title={canCreateRB ? 'Create a related case in the Regional Bureau.' : 'RB case creation requires an RB officer or Admin.'} onClick={() => { setCreateRBSummary(`Students asked the Regional Bureau to independently review the reported ${item.category_name ?? 'service'} concern at ${item.institution_name ?? 'this institution'} and clarify the pending issue.`); createRBMutation.reset(); setCreateRBOpen(true) }}><Plus className="h-4 w-4" />Create RB follow-up</button>}{buttons.map((kind) => <button key={kind} onClick={() => { setSuccess(''); mutation.reset(); setActiveAction(kind) }} className={kind === 'dispose' ? 'button-danger' : kind === 'escalate' ? 'button-warning' : 'button-primary'}>{kind === 'action' && <Plus className="h-4 w-4" />}{actionLabels[kind]}</button>)}</span>} />
      {success && <div role="status" className="mb-4 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"><Check className="h-4 w-4" />{success}</div>}
      {mutation.isError && <div className="mb-4"><ErrorState message={mutation.error instanceof Error ? mutation.error.message : 'The case action could not be saved.'} /></div>}
      {createRBMutation.isError && <div className="mb-4"><ErrorState message={createRBMutation.error instanceof Error ? createRBMutation.error.message : 'The RB case could not be created.'} /></div>}
      {item.link_group_id && <div className="mb-4 flex items-start gap-3 rounded-xl border border-teal-200 bg-teal-50 p-4 text-teal-950"><Link2 className="mt-0.5 h-5 w-5 shrink-0" /><div><p className="font-semibold">This case is linked for cross-bureau coordination</p><p className="mt-1 text-sm">Group ID: <span className="font-mono">{item.link_group_id}</span></p></div></div>}
      {item.needs_institution_review && <div className="mb-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><AlertTriangle className="h-4 w-4" />Institution details need review.</div>}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.8fr)]">
        <div className="space-y-5">
          <Card className="p-5"><SectionTitle title="Case summary" note="Key complaint and tracking details." /><p className="mb-5 text-sm leading-6 text-slate-700">{item.summary || 'No summary provided.'}</p><div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">{[
            ['Institution', item.institution_name ?? item.institution?.name ?? 'Unresolved'],
            ['AICTE permanent ID', item.aicte_permanent_id ?? item.institution?.aicte_permanent_id ?? '—'],
            ['Bureau / cell', item.bureau_name ?? item.bureau_code ?? '—'],
            ['Category', item.category_name ?? '—'],
            ['Status', <StatusBadge status={item.status} />],
            ['Priority', <span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span>],
            ['Received on', formatDate(item.received_on)],
            ['Expected disposal', <span className="inline-flex items-center gap-2"><span>{formatDate(item.expected_disposal_on)}</span><SlaBadge dueOn={item.expected_disposal_on} status={item.status} /></span>],
            ['Last action date', formatDateTime(item.last_action_on)],
            ['Last action', item.last_action_text ?? '—'],
            ['Next action', item.next_action_text ?? '—'],
            ['Assigned officer', item.assigned_officer_name ?? '—'],
            ['Source channel', item.source_channel],
            ['Source', item.source],
            ['Hard deadline', item.hard_deadline_on ? `${formatDate(item.hard_deadline_on)} · ${item.hard_deadline_type ?? ''}` : 'None'],
            ['Complainant reference', item.complainant_ref ?? 'Masked or unavailable'],
          ].map(([label, value]) => <div key={String(label)}><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p><div className="mt-1 text-sm font-medium text-slate-800">{value}</div></div>)}</div></Card>
          {item.institution_id && <Link to={`/institutions/${item.institution_id}`} className="inline-flex items-center gap-1 text-sm font-semibold text-teal-800 hover:underline">Open institution 360 <ExternalLink className="h-4 w-4" /></Link>}
        </div>
        <Card className="p-5"><SectionTitle title="Action history" note="Status changes and notes are recorded in order." />
          {item.actions.length === 0 ? <EmptyState title="No action history" message="This case has no recorded actions yet." /> : <ol className="relative ml-2 border-l border-slate-200">{item.actions.map((action) => <li key={action.id} className="relative pb-6 pl-5 last:pb-0"><span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full border-2 border-white bg-teal-600 ring-1 ring-teal-200" /><p className="text-sm font-semibold text-slate-800">{(action.action_type ?? 'ACTION').replace(/_/g, ' ')}</p><p className="mt-0.5 text-xs text-slate-500">{formatDateTime(action.created_at)}{action.actor_name ? ` · ${action.actor_name}` : ''}{action.bureau_code ? ` · ${action.bureau_code}` : ''}</p>{action.from_status && action.to_status && <p className="mt-1 text-xs text-slate-600">{action.from_status.replace(/_/g, ' ')} <ArrowRight className="inline h-3 w-3" /> {action.to_status.replace(/_/g, ' ')}</p>}{action.remarks && <p className="mt-1 text-sm leading-5 text-slate-600">{action.remarks}</p>}</li>)}</ol>}
        </Card>
      </div>
      {activeAction && <ActionDialog kind={activeAction} isPending={mutation.isPending} onClose={() => setActiveAction(null)} onSubmit={(remarks, toBureauId) => submitAction(activeAction, remarks, toBureauId)} />}
      {createRBOpen && <CreateRBCaseDialog initialSummary={createRBSummary} isPending={createRBMutation.isPending} onClose={() => setCreateRBOpen(false)} onSubmit={(summary) => createRBMutation.mutate(summary)} />}
    </>
  )
}

function CreateRBCaseDialog({ initialSummary, isPending, onClose, onSubmit }: { initialSummary: string; isPending: boolean; onClose: () => void; onSubmit: (summary: string) => void }) {
  const [summary, setSummary] = useState(initialSummary)
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !isPending) onClose() }}><section role="dialog" aria-modal="true" aria-labelledby="create-rb-title" className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl sm:p-6"><div className="flex items-start justify-between gap-4"><div><h2 id="create-rb-title" className="text-lg font-bold text-slate-900">Create related RB case</h2><p className="mt-1 text-sm text-slate-600">The institution and category follow this case. Use distinct wording for the new case summary.</p></div><button type="button" onClick={onClose} disabled={isPending} aria-label="Close dialog" className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button></div><p className="mt-3 rounded-lg bg-teal-50 p-3 text-xs leading-5 text-teal-950">The demo reuses the visible synthetic complainant reference when available so the overlap explanation can show the shared-reference signal.</p><form onSubmit={(event) => { event.preventDefault(); onSubmit(summary.trim()) }} className="mt-4 space-y-4"><label className="block text-sm font-semibold text-slate-700">New RB complaint wording<textarea required minLength={10} maxLength={4000} rows={5} value={summary} onChange={(event) => setSummary(event.target.value)} className="form-control mt-1.5 resize-y" /></label><div className="flex justify-end gap-2 border-t border-slate-100 pt-4"><button type="button" className="button-secondary" onClick={onClose} disabled={isPending}>Cancel</button><button type="submit" className="button-primary" disabled={isPending || summary.trim().length < 10}>{isPending ? 'Creating…' : 'Create RB case'}</button></div></form></section></div>
}

function ActionDialog({ kind, isPending, onClose, onSubmit }: { kind: ActionKind; isPending: boolean; onClose: () => void; onSubmit: (remarks: string, bureauId?: string) => void }) {
  const [remarks, setRemarks] = useState('')
  const [bureauId, setBureauId] = useState('')
  const title = kind === 'action' ? 'Add action note' : `${actionLabels[kind]} case`
  const reasonLabel = kind === 'reopen' ? 'Reason for reopening' : kind === 'action' ? 'Action taken' : 'Reason / remarks'
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit(remarks.trim(), kind === 'transfer' ? bureauId.trim() : undefined)
  }
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !isPending) onClose() }}>
    <section role="dialog" aria-modal="true" aria-labelledby="action-dialog-title" className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl sm:p-6">
      <div className="mb-4 flex items-start justify-between gap-4"><div><h2 id="action-dialog-title" className="text-lg font-bold text-slate-900">{title}</h2><p className="mt-1 text-sm text-slate-600">This note will be added to the case history.</p></div><button type="button" onClick={onClose} disabled={isPending} aria-label="Close dialog" className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button></div>
      <form onSubmit={submit} className="space-y-4"><label className="block text-sm font-semibold text-slate-700">{reasonLabel}<textarea required minLength={2} maxLength={2000} rows={4} value={remarks} onChange={(event) => setRemarks(event.target.value)} className="form-control mt-1.5 resize-y" placeholder="Write a clear reason for the case history" /></label>
        {kind === 'transfer' && <label className="block text-sm font-semibold text-slate-700">Target bureau ID<input required value={bureauId} onChange={(event) => setBureauId(event.target.value)} className="form-control mt-1.5" placeholder="Enter target bureau ID" /><span className="mt-1 block text-xs font-normal text-slate-500">Use the bureau ID supplied by your administrator.</span></label>}
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4"><button type="button" className="button-secondary" disabled={isPending} onClick={onClose}>Cancel</button><button type="submit" disabled={isPending || remarks.trim().length < 2 || (kind === 'transfer' && !bureauId.trim())} className="button-primary">{isPending ? 'Saving…' : `Save ${kind === 'action' ? 'action' : kind}`}</button></div>
      </form>
    </section>
  </div>
}

export function InstitutionsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const page = Math.max(1, Number(searchParams.get('page') ?? 1) || 1)
  const pageSize = 10
  const query = useQuery({ queryKey: ['institutions', q, page], queryFn: () => institutionsApi.list(q, page, pageSize) })
  function setSearch(value: string) { setSearchParams((current) => { const next = new URLSearchParams(current); if (value) next.set('q', value); else next.delete('q'); next.delete('page'); return next }) }
  function setPage(nextPage: number) { setSearchParams((current) => { const next = new URLSearchParams(current); if (nextPage > 1) next.set('page', String(nextPage)); else next.delete('page'); return next }) }
  return <>
    <PageHeader title="Institutions" helper="Review synthetic institution identity and open its case coordination view." />
    <Card className="mb-5 p-4"><label className="relative block max-w-xl text-xs font-semibold text-slate-600">Find an institution<input className="form-control mt-1.5 pl-9" value={q} onChange={(event) => setSearch(event.target.value)} placeholder="Name or AICTE permanent ID" /><Search className="absolute left-3 top-[34px] h-4 w-4 text-slate-400" /></label></Card>
    {query.isLoading && <LoadingState label="Loading institutions…" />}
    {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Institutions could not be loaded.'} retry={() => void query.refetch()} />}
    {query.data && query.data.items.length === 0 && <EmptyState title="No matching institutions" message="Try another name or permanent ID." />}
    {query.data && query.data.items.length > 0 && <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="gov-table min-w-[760px]"><thead><tr><th>Institution</th><th>AICTE permanent ID</th><th>Region</th><th>Type</th><th>Source</th></tr></thead><tbody>{query.data.items.map((institution) => <tr key={institution.id}><td><Link className="font-semibold text-[#153a5b] hover:underline" to={`/institutions/${institution.id}`}>{institution.name}</Link><p className="mt-0.5 text-xs text-slate-500">{institution.district ?? 'District not listed'}</p></td><td className="font-mono text-xs">{institution.aicte_permanent_id}</td><td>{institution.region_name ?? institution.state ?? '—'}</td><td>{institution.type ?? '—'}</td><td><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{institution.source}</span></td></tr>)}</tbody></table></div><div className="flex justify-between border-t border-slate-200 px-4 py-3"><p className="text-xs text-slate-500">{query.data.total} institutions</p><div className="flex gap-2"><button className="button-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><button className="button-secondary" disabled={page * pageSize >= query.data.total} onClick={() => setPage(page + 1)}>Next</button></div></div></Card>}
  </>
}

type InstitutionTab = 'cases' | 'overlaps'
export function InstitutionDetailPage() {
  const { institutionId = '' } = useParams()
  const [tab, setTab] = useState<InstitutionTab>('cases')
  const institutionQuery = useQuery({ queryKey: ['institution', institutionId], queryFn: () => institutionsApi.detail(institutionId), enabled: Boolean(institutionId) })
  const casesQuery = useQuery({ queryKey: ['institution-cases', institutionId], queryFn: () => institutionsApi.cases(institutionId), enabled: Boolean(institutionId) })
  const overlapsQuery = useQuery({ queryKey: ['overlaps', 'all'], queryFn: () => overlapsApi.list(), enabled: Boolean(institutionId) })
  const institution = institutionQuery.data
  const cases = casesQuery.data?.items ?? []
  const flags = (overlapsQuery.data?.items ?? []).filter((flag) => flag.institution_id === institutionId || (institution && flag.institution_id === institution.id))
  const tierA = flags.find((flag) => flag.tier === 'A' && flag.state === 'OPEN')
  const bureauCounts = useMemo(() => cases.reduce<Record<string, number>>((counts, item) => { const name = item.bureau_code ?? item.bureau_id; counts[name] = (counts[name] ?? 0) + 1; return counts }, {}), [cases])

  if (institutionQuery.isLoading) return <LoadingState label="Loading institution profile…" />
  if (institutionQuery.isError || !institution) return <ErrorState message={institutionQuery.error instanceof Error ? institutionQuery.error.message : 'Institution profile could not be loaded.'} retry={() => void institutionQuery.refetch()} />

  return <>
    <div className="mb-4"><Link to="/institutions" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-teal-800"><ArrowLeft className="h-4 w-4" />Back to institutions</Link></div>
    <PageHeader title="Institution 360" helper="Identity, case activity, and cross-bureau coordination at a glance." />
    {tierA && <div className="mb-5 flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" /><div><p className="font-bold">Potential Overlapping Cases - Coordination Required</p><p className="mt-1 text-sm">Open cases appear in more than one bureau. Review the Overlaps tab and coordinate next steps.</p></div></div>}
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)]">
      <Card className="p-5"><SectionTitle title="Institution identity" note="Synthetic institution reference details." /><div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><p className="text-xl font-bold text-slate-900">{institution.name}</p><p className="mt-1 font-mono text-sm text-teal-800">{institution.aicte_permanent_id}</p></div><span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">{institution.status ?? 'ACTIVE'}</span></div><div className="grid gap-4 border-t border-slate-100 pt-4 sm:grid-cols-2"><IdentityField label="Address" value={institution.address} /><IdentityField label="District" value={institution.district} /><IdentityField label="State" value={institution.state} /><IdentityField label="Region" value={institution.region_name} /><IdentityField label="Institution type" value={institution.type} /><IdentityField label="Record source" value={institution.source} /></div></Card>
      <Card className="p-5"><SectionTitle title="Cases by bureau" note="Counts are based on this institution’s current case list." />{Object.keys(bureauCounts).length === 0 ? <p className="text-sm text-slate-500">No cases recorded for this institution.</p> : <div className="space-y-3">{Object.entries(bureauCounts).map(([bureau, count]) => <div key={bureau} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2.5"><span className="text-sm font-medium text-slate-700">{bureau}</span><span className="rounded-full bg-white px-2.5 py-1 text-sm font-bold text-slate-900 shadow-sm">{count}</span></div>)}</div>}<div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">{cases.length} cases total</div></Card>
    </div>
    <div className="mt-6 border-b border-slate-200"><div className="flex gap-5"><button onClick={() => setTab('cases')} className={`border-b-2 px-1 pb-3 text-sm font-semibold ${tab === 'cases' ? 'border-teal-700 text-teal-800' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>All cases</button><button onClick={() => setTab('overlaps')} className={`border-b-2 px-1 pb-3 text-sm font-semibold ${tab === 'overlaps' ? 'border-teal-700 text-teal-800' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>Overlaps <span className="ml-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-xs">{flags.length}</span></button></div></div>
    <div className="mt-4">
      {(casesQuery.isLoading || (tab === 'overlaps' && overlapsQuery.isLoading)) && <LoadingState label="Loading institution activity…" />}
      {(casesQuery.isError || (tab === 'overlaps' && overlapsQuery.isError)) && <ErrorState message="Institution activity could not be loaded." retry={() => { void casesQuery.refetch(); void overlapsQuery.refetch() }} />}
      {tab === 'cases' && casesQuery.data && (cases.length ? <CaseTable items={cases} /> : <EmptyState title="No cases for this institution" message="Cases linked to this institution will appear here." />)}
      {tab === 'overlaps' && overlapsQuery.data && (flags.length ? <div className="space-y-3">{flags.map((flag) => <Card key={flag.id} className="p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">Tier {flag.tier} · {flag.tier === 'A' ? 'Institution coordination' : 'Potential case pair'}</p><p className="mt-1 text-xs text-slate-500">{flag.reasons.join(' · ') || 'Review this flag with the owning bureau.'}</p></div><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${flag.state === 'OPEN' ? 'bg-amber-100 text-amber-800' : flag.state === 'CONFIRMED' ? 'bg-teal-100 text-teal-800' : 'bg-slate-100 text-slate-600'}`}>{flag.state}</span></div><div className="mt-3 flex flex-wrap gap-2">{flag.cases.map((caseItem) => <Link key={caseItem.id} to={`/cases/${caseItem.id}`} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-[#153a5b] hover:bg-slate-50">{caseItem.case_no}<ExternalLink className="h-3.5 w-3.5" /></Link>)}</div></Card>)}</div> : <EmptyState title="No overlap flags" message="No potential coordination flags are recorded for this institution." />)}
    </div>
  </>
}

function IdentityField({ label, value }: { label: string; value?: string | null }) {
  return <div><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 text-sm text-slate-800">{value || 'Not listed'}</p></div>
}

export function CaseTable({ items }: { items: CaseRecord[] }) {
  return <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="gov-table min-w-[900px]"><thead><tr><th>Case</th><th>Bureau</th><th>Received</th><th>Next action</th><th>SLA</th><th>Status</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><Link to={`/cases/${item.id}`} className="font-semibold text-[#153a5b] hover:underline">{item.case_no}</Link><p className="mt-0.5 max-w-[340px] truncate text-xs text-slate-500">{item.summary}</p></td><td>{item.bureau_code ?? '—'}</td><td>{formatDate(item.received_on)}</td><td className="max-w-[220px] truncate">{item.next_action_text ?? '—'}</td><td><SlaBadge dueOn={item.expected_disposal_on} status={item.status} /></td><td><StatusBadge status={item.status} /></td></tr>)}</tbody></table></div></Card>
}

