import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Link2,
  Plus,
  Search,
  X,
} from 'lucide-react'
import { casesApi, dashboardApi, institutionsApi, type CaseFilters } from '../api'
import { useAuth } from '../auth/AuthContext'
import {
  Card,
  EmptyState,
  ErrorState,
  formatDate,
  formatDateTime,
  LoadingState,
  PageHeader,
  SectionTitle,
  SlaBadge,
  StatusBadge,
} from '../components/Shared'
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
  const filters: CaseFilters = {
    q: q || undefined,
    status: status || undefined,
    priority: priority || undefined,
    linked: linked ? linked === 'true' : undefined,
    beyond_sla: beyondSla || undefined,
    page,
    page_size: pageSize,
  }
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
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      <PageHeader
        title="Complaint Management"
        helper="Unified tracking of grievance movement across bureaus, statutory SLA monitoring, and audited case actions."
      />

      {/* Filter Toolbar */}
      <Card className="p-5">
        <div className="grid gap-3 md:grid-cols-[minmax(240px,1.2fr)_180px_140px_160px_160px]">
          <label className="relative block text-xs font-semibold text-slate-600">
            Search dockets
            <input
              className="form-control mt-1.5 pl-9 rounded-xl"
              value={q}
              onChange={(event) => updateParam('q', event.target.value)}
              placeholder="Docket ID, institution, or keyword…"
            />
            <Search className="absolute left-3 top-[32px] h-4 w-4 text-slate-400" />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Status
            <select
              className="form-control mt-1.5 rounded-xl"
              value={status}
              onChange={(event) => updateParam('status', event.target.value)}
            >
              <option value="">All statuses</option>
              {statusChoices.map((item) => (
                <option key={item} value={item}>
                  {item === 'UNDER_PROCESS' ? 'Under Process' : item.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Priority
            <select
              className="form-control mt-1.5 rounded-xl"
              value={priority}
              onChange={(event) => updateParam('priority', event.target.value)}
            >
              <option value="">All priorities</option>
              {priorityChoices.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Coordination
            <select
              className="form-control mt-1.5 rounded-xl"
              value={linked}
              onChange={(event) => updateParam('linked', event.target.value)}
            >
              <option value="">All dockets</option>
              <option value="true">Linked for coordination</option>
              <option value="false">Unlinked</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            SLA benchmark
            <select
              className="form-control mt-1.5 rounded-xl"
              value={beyondSla ? 'true' : ''}
              onChange={(event) => updateParam('beyond_sla', event.target.value)}
            >
              <option value="">Any timeline</option>
              <option value="true">Beyond SLA limit</option>
            </select>
          </label>
        </div>
      </Card>

      {query.isLoading && <LoadingState label="Retrieving complaint registry…" />}
      {query.isError && (
        <ErrorState
          message={query.error instanceof Error ? query.error.message : 'Cases could not be loaded.'}
          retry={() => void query.refetch()}
        />
      )}
      {query.data && query.data.items.length === 0 && (
        <EmptyState title="No matching dockets found" message="Try adjusting your search criteria or resetting filters." />
      )}

      {query.data && query.data.items.length > 0 && (
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-4 bg-slate-50/50">
            <p className="text-sm font-bold text-slate-900">
              {query.data.total.toLocaleString()} Registered Inquiries
            </p>
            <p className="text-xs font-medium text-slate-500">
              Page {query.data.page} of {Math.max(1, Math.ceil(query.data.total / query.data.page_size))}
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="gov-table min-w-[1000px]">
              <thead>
                <tr>
                  <th>Docket / Institution</th>
                  <th>Bureau / Category</th>
                  <th>Received Date</th>
                  <th>Priority</th>
                  <th>SLA Status</th>
                  <th>State</th>
                  <th>Overlap Coordination</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((item) => (
                  <CaseRow key={item.id} item={item} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3.5 bg-slate-50/50">
            <span className="text-xs text-slate-500 font-medium">
              Showing {Math.min((page - 1) * pageSize + 1, query.data.total)}–
              {Math.min(page * pageSize, query.data.total)} of {query.data.total}
            </span>
            <div className="flex gap-2">
              <button
                className="button-secondary text-xs px-3 py-1.5"
                disabled={page <= 1}
                onClick={() => updateParam('page', String(page - 1))}
              >
                Previous
              </button>
              <button
                className="button-secondary text-xs px-3 py-1.5"
                disabled={page * pageSize >= query.data.total}
                onClick={() => updateParam('page', String(page + 1))}
              >
                Next
              </button>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

function CaseRow({ item }: { item: CaseRecord }) {
  const priorityBadge =
    item.priority === 'HIGH'
      ? 'bg-rose-50 text-rose-700 border-rose-200 font-bold'
      : item.priority === 'MEDIUM'
      ? 'bg-amber-50 text-amber-700 border-amber-200 font-medium'
      : 'bg-slate-100 text-slate-700 border-slate-200'

  return (
    <tr className="hover:bg-slate-50/80 transition-colors">
      <td>
        <Link to={`/cases/${item.id}`} className="font-bold text-blue-700 hover:text-blue-900 hover:underline">
          {item.case_no}
        </Link>
        <p className="mt-0.5 max-w-[340px] truncate text-xs text-slate-500 font-medium">
          {item.institution_name ?? 'Institution not resolved'}
          {item.aicte_permanent_id ? ` · ${item.aicte_permanent_id}` : ''}
        </p>
      </td>
      <td>
        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-100 text-slate-700 border border-slate-200">
          {item.bureau_code ?? '—'}
        </span>
        <p className="text-xs text-slate-600 mt-0.5">{item.category_name ?? 'Category'}</p>
      </td>
      <td className="font-mono text-xs text-slate-600">{formatDate(item.received_on)}</td>
      <td>
        <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] border ${priorityBadge}`}>
          {item.priority}
        </span>
      </td>
      <td>
        <SlaBadge dueOn={item.expected_disposal_on} status={item.status} />
      </td>
      <td>
        <StatusBadge status={item.status} />
      </td>
      <td>
        {item.link_group_id ? (
          <span
            title="Linked for multi-bureau coordination"
            className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2.5 py-0.5 text-[11px] font-bold text-purple-700 border border-purple-200"
          >
            <Link2 className="h-3 w-3" />
            Linked
          </span>
        ) : (
          <span className="text-xs text-slate-400">—</span>
        )}
      </td>
    </tr>
  )
}

type ActionKind = 'action' | 'transfer' | 'escalate' | 'dispose' | 'reopen'
const actionLabels: Record<ActionKind, string> = {
  action: 'Add Action',
  transfer: 'Transfer Bureau',
  escalate: 'Senior Escalation',
  dispose: 'Dispose Docket',
  reopen: 'Reopen Investigation',
}

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
    mutationFn: ({ kind, payload }: { kind: ActionKind; payload: Record<string, string> }) =>
      casesApi.action(caseId, kind, payload),
    onSuccess: async (_, variables) => {
      setActiveAction(null)
      setSuccess(`${actionLabels[variables.kind]} recorded to immutable audit history.`)
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

  const item = query.data

  function canAct() {
    if (!item || !user) return false
    if (user.role === 'ADMIN') return true
    if (user.role === 'SENIOR_MGMT') return activeAction === 'escalate'
    if (user.role === 'REGIONAL_OFFICER') return Boolean(user.region_id && item.region_id === user.region_id)
    if (user.role === 'BUREAU_OFFICER') return Boolean(user.bureau_id && item.bureau_id === user.bureau_id)
    return false
  }

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      <div className="flex items-center gap-3">
        <Link
          to="/cases"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-slate-800 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to All Dockets</span>
        </Link>
      </div>

      {query.isLoading && <LoadingState label="Loading case dossier…" />}
      {query.isError && (
        <ErrorState
          message={query.error instanceof Error ? query.error.message : 'Docket could not be loaded.'}
          retry={() => void query.refetch()}
        />
      )}

      {item && (
        <>
          {/* Header Title with Badges */}
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded bg-blue-100 text-blue-900 border border-blue-200">
                  {item.bureau_code ?? 'AICTE'}
                </span>
                <span className="text-xs text-slate-500">•</span>
                <span className="text-xs font-bold text-slate-600">{item.category_name ?? 'General'}</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1">{item.case_no}</h1>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                {item.institution_name ?? 'Institution Not Resolved'}
                {item.aicte_permanent_id ? ` (AICTE Permanent ID: ${item.aicte_permanent_id})` : ''}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {item.bureau_code === 'PGRC' && user?.role === 'ADMIN' && (
                <button
                  type="button"
                  onClick={() => {
                    setCreateRBSummary(`Regulatory non-compliance inquiry for ${item.institution_name ?? 'institution'}`)
                    setCreateRBOpen(true)
                  }}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-purple-200 bg-purple-50 px-3 py-1.5 text-xs font-bold text-purple-700 hover:bg-purple-100 transition shadow-xs"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Demo: Create Concurrent RB Case</span>
                </button>
              )}
              <SlaBadge dueOn={item.expected_disposal_on} status={item.status} />
              <StatusBadge status={item.status} />
            </div>
          </div>

          {success && (
            <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-medium text-emerald-900 flex items-center justify-between">
              <span>{success}</span>
              <button onClick={() => setSuccess('')} className="text-emerald-700 hover:text-emerald-900 font-bold ml-2">Dismiss</button>
            </div>
          )}

          {/* Linked Coordination Banner */}
          {item.link_group_id && (
            <div className="rounded-2xl border border-purple-200 bg-gradient-to-r from-purple-50 to-indigo-50 p-5 shadow-xs flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center shrink-0">
                  <Link2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-purple-900">
                    This docket is formally linked for multi-bureau coordination
                  </h3>
                  <p className="text-xs text-purple-700 mt-0.5">
                    Coordinated inquiry active between Regulation Bureau and PGRC under group ID: <code className="font-mono">{item.link_group_id}</code>.
                  </p>
                </div>
              </div>
              <Link
                to="/overlaps"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-600 text-white font-bold text-xs hover:bg-purple-700 transition"
              >
                <span>Overlap Center</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          )}

          {/* 10 Core AICTE Mandated Fields */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Left 2 Cols: Primary Dossier */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="p-6">
                <SectionTitle title="Docket Overview & Allegation Summary" />
                <p className="text-sm text-slate-800 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                  {item.summary || 'No grievance narrative provided.'}
                </p>

                <div className="grid sm:grid-cols-2 gap-4 mt-6 pt-6 border-t border-slate-100">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Date of Receipt</p>
                    <p className="mt-1 text-sm font-bold text-slate-800 font-mono">{formatDate(item.received_on)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Assigned Official / Officer</p>
                    <p className="mt-1 text-sm font-bold text-slate-800">{item.assigned_officer_name ?? 'AICTE Duty Officer'}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Last Action Recorded</p>
                    <p className="mt-1 text-xs text-slate-700 font-medium">{item.last_action_text ?? 'Docket acknowledged.'}</p>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5">{formatDateTime(item.last_action_on)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Next Action Required</p>
                    <p className="mt-1 text-xs font-bold text-blue-700">{item.next_action_text ?? 'Initial evaluation pending.'}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">Expected Disposal: {formatDate(item.expected_disposal_on)}</p>
                  </div>
                </div>
              </Card>

              {/* Append-Only Chronological Audit Timeline */}
              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <SectionTitle title="Append-Only Workflow Audit Ledger" note="Immutable cryptographic trail of officer actions and transitions." />
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                    INSERT-ONLY
                  </span>
                </div>

                <div className="space-y-4">
                  {item.actions && item.actions.length > 0 ? (
                    item.actions.map((act, idx) => (
                      <div key={act.id || idx} className="relative pl-6 pb-4 border-l-2 border-blue-500/30 last:border-0 last:pb-0">
                        <span className="absolute -left-1.5 top-0 w-3 h-3 rounded-full bg-blue-600 border-2 border-white ring-2 ring-blue-100" />
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-bold text-xs text-slate-900">
                            {act.action_type.replace(/_/g, ' ')}
                            {act.to_status && (
                              <span className="ml-2 font-normal text-slate-500">
                                → <StatusBadge status={act.to_status} />
                              </span>
                            )}
                          </span>
                          <span className="text-[10px] font-mono text-slate-400">{formatDateTime(act.created_at)}</span>
                        </div>
                        <p className="text-xs text-slate-700 mt-1">{act.remarks || 'No remarks entered.'}</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Officer: <span className="font-semibold text-slate-600">{act.actor_name ?? 'Official'}</span>
                          {act.bureau_code ? ` · ${act.bureau_code}` : ''}
                        </p>
                      </div>
                    ))
                  ) : (
                    <EmptyState title="No past actions" message="New actions will appear in this immutable timeline." />
                  )}
                </div>
              </Card>
            </div>

            {/* Right Col: Metadata & Action Controls */}
            <div className="space-y-6">
              {/* Institution Quick Profile */}
              <Card className="p-5">
                <SectionTitle title="Affiliated Institution" />
                <div className="space-y-2 mt-3">
                  <p className="text-sm font-bold text-slate-900">{item.institution_name ?? 'Unresolved Institution'}</p>
                  <p className="text-xs text-slate-500 font-mono">Permanent ID: {item.aicte_permanent_id ?? 'SYN-00000'}</p>
                  {item.institution_id && (
                    <Link
                      to={`/institutions/${item.institution_id}`}
                      className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-800 pt-2"
                    >
                      <Building2 className="w-3.5 h-3.5" />
                      <span>View Complete Profile</span>
                    </Link>
                  )}
                </div>
              </Card>

              {/* Whistleblower Privacy & Complainant Reference */}
              <Card className="p-5">
                <SectionTitle title="Complainant Reference" note="RBAC protected whistleblower identifier." />
                <div className="mt-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-xs font-mono font-bold text-slate-800">
                    {item.complainant_ref || 'MASKED / NOT DISCLOSED'}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1">
                    Direct identity is securely masked outside the receiving bureau and regional jurisdiction.
                  </p>
                </div>
              </Card>

              {/* Action Execution Console */}
              <Card className="p-5">
                <SectionTitle title="Execute Action Transition" note="Enforces AICTE finite state machine." />
                {!canAct() && (
                  <p className="mt-2 text-xs text-amber-700 bg-amber-50 p-2 rounded-lg border border-amber-200">
                    Your current officer role ({user?.role}) does not have action authority for this docket.
                  </p>
                )}
                <div className="space-y-2 mt-3">
                  {item.status !== 'DISPOSED' && (
                    <>
                      {item.status === 'PENDING' && (
                        <button
                          disabled={!canAct()}
                          className="w-full flex items-center justify-between p-2.5 rounded-xl border border-blue-200 bg-blue-50/50 hover:bg-blue-100/70 text-xs font-bold text-blue-900 transition disabled:opacity-50"
                          onClick={() => setActiveAction('action')}
                        >
                          <span>Move to Under Process</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        disabled={!canAct()}
                        className="w-full flex items-center justify-between p-2.5 rounded-xl border border-purple-200 bg-purple-50/50 hover:bg-purple-100/70 text-xs font-bold text-purple-900 transition disabled:opacity-50"
                        onClick={() => setActiveAction('transfer')}
                      >
                        <span>Transfer Bureau</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                      <button
                        disabled={!canAct()}
                        className="w-full flex items-center justify-between p-2.5 rounded-xl border border-rose-200 bg-rose-50/50 hover:bg-rose-100/70 text-xs font-bold text-rose-900 transition disabled:opacity-50"
                        onClick={() => setActiveAction('escalate')}
                      >
                        <span>Escalate to Senior Council</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                      <button
                        disabled={!canAct()}
                        className="w-full flex items-center justify-between p-2.5 rounded-xl border border-emerald-200 bg-emerald-50/50 hover:bg-emerald-100/70 text-xs font-bold text-emerald-900 transition disabled:opacity-50"
                        onClick={() => setActiveAction('dispose')}
                      >
                        <span>Dispose & Resolve</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                  {item.status === 'DISPOSED' && (
                    <button
                      disabled={!canAct()}
                      className="w-full flex items-center justify-between p-2.5 rounded-xl border border-amber-200 bg-amber-50/50 hover:bg-amber-100/70 text-xs font-bold text-amber-900 transition disabled:opacity-50"
                      onClick={() => setActiveAction('reopen')}
                    >
                      <span>Reopen Investigation</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </Card>
            </div>
          </div>

          {/* Action Modal Dialog */}
          {activeAction && (
            <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/60 backdrop-blur-xs p-4">
              <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">{actionLabels[activeAction]}</h2>
                    <p className="text-xs text-slate-500 mt-0.5">Docket: {item.case_no}</p>
                  </div>
                  <button
                    onClick={() => setActiveAction(null)}
                    className="p-1 rounded-lg text-slate-400 hover:bg-slate-100"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    const fd = new FormData(e.currentTarget)
                    const payload: Record<string, string> = {
                      remarks: String(fd.get('remarks') || ''),
                    }
                    if (activeAction === 'transfer') {
                      payload.to_bureau_id = String(fd.get('to_bureau_id') || '')
                    }
                    mutation.mutate({ kind: activeAction, payload })
                  }}
                  className="mt-5 space-y-4"
                >
                  {activeAction === 'transfer' && (
                    <label className="block text-xs font-bold text-slate-700">
                      Destination Bureau
                      <select name="to_bureau_id" required className="form-control mt-1 rounded-xl">
                        <option value="">Select target bureau…</option>
                        {workloadQuery.data?.items
                          .filter((b) => b.bureau_id !== item.bureau_id)
                          .map((b) => (
                            <option key={b.bureau_id} value={b.bureau_id}>
                              {b.bureau_name} ({b.bureau_code})
                            </option>
                          ))}
                      </select>
                    </label>
                  )}

                  <label className="block text-xs font-bold text-slate-700">
                    Mandatory Officer Remarks
                    <textarea
                      name="remarks"
                      required
                      rows={3}
                      className="form-control mt-1 rounded-xl"
                      placeholder="Enter official statement for the immutable audit trail…"
                    />
                  </label>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setActiveAction(null)}
                      className="button-secondary text-xs rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={mutation.isPending}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white hover:bg-blue-700 shadow-sm transition disabled:opacity-50"
                    >
                      {mutation.isPending ? 'Recording…' : 'Confirm Action'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Plant Concurrent RB Case Modal (Live Demo Tool) */}
          {createRBOpen && (
            <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/60 backdrop-blur-xs p-4">
              <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">Create Concurrent RB Case</h2>
                    <p className="text-xs text-slate-500 mt-0.5">Live demonstration tool for testing overlap detection</p>
                  </div>
                  <button
                    onClick={() => setCreateRBOpen(false)}
                    className="p-1 rounded-lg text-slate-400 hover:bg-slate-100"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    createRBMutation.mutate(createRBSummary)
                  }}
                  className="mt-5 space-y-4"
                >
                  <label className="block text-xs font-bold text-slate-700">
                    Regulatory Non-Compliance Allegation Summary
                    <textarea
                      required
                      rows={3}
                      value={createRBSummary}
                      onChange={(e) => setCreateRBSummary(e.target.value)}
                      className="form-control mt-1 rounded-xl"
                      placeholder="Enter details for the concurrent Regulation Bureau investigation..."
                    />
                  </label>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setCreateRBOpen(false)}
                      className="button-secondary text-xs rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={createRBMutation.isPending || !createRBSummary.trim()}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-purple-700 px-4 py-2 text-xs font-bold text-white hover:bg-purple-800 shadow-sm transition disabled:opacity-50"
                    >
                      {createRBMutation.isPending ? 'Planting Case…' : 'Generate RB Case'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function InstitutionsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const page = Math.max(1, Number(searchParams.get('page') ?? 1) || 1)
  const pageSize = 12
  const query = useQuery({
    queryKey: ['institutions', q, page],
    queryFn: () => institutionsApi.list(q, page, pageSize),
  })

  function updateQuery(value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value) next.set('q', value)
      else next.delete('q')
      next.delete('page')
      return next
    })
  }

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      <PageHeader
        title="Institutions Directory"
        helper="Centralized institution registry with cross-bureau grievance histories and permanent AICTE IDs."
      />

      <Card className="p-4">
        <label className="relative block max-w-md text-xs font-semibold text-slate-600">
          Search institutions
          <input
            className="form-control mt-1.5 pl-9 rounded-xl"
            value={q}
            onChange={(e) => updateQuery(e.target.value)}
            placeholder="College name, Permanent ID (e.g. SYN-00001), or state…"
          />
          <Search className="absolute left-3 top-[32px] h-4 w-4 text-slate-400" />
        </label>
      </Card>

      {query.isLoading && <LoadingState label="Searching institution registry…" />}
      {query.isError && (
        <ErrorState
          message={query.error instanceof Error ? query.error.message : 'Institutions could not be loaded.'}
          retry={() => void query.refetch()}
        />
      )}
      {query.data && query.data.items.length === 0 && (
        <EmptyState title="No institutions match" message="Try searching with a different campus name or ID." />
      )}

      {query.data && query.data.items.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {query.data.items.map((inst) => (
            <Card key={inst.id} className="p-5 flex flex-col justify-between hover:border-blue-400 transition-all">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                    {inst.aicte_permanent_id}
                  </span>
                  <span className="text-[10px] text-slate-400 font-semibold">{inst.region_name ?? 'North'} Region</span>
                </div>
                <h3 className="text-sm font-bold text-slate-900 mt-2 line-clamp-2">{inst.name}</h3>
                <p className="text-xs text-slate-500 mt-1">{inst.state} • {inst.type}</p>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                <Link
                  to={`/institutions/${inst.id}`}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-800"
                >
                  <span>Dossier & History</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export function InstitutionDetailPage() {
  const { institutionId = '' } = useParams()
  const instQuery = useQuery({
    queryKey: ['institution', institutionId],
    queryFn: () => institutionsApi.detail(institutionId),
  })
  const casesQuery = useQuery({
    queryKey: ['institution-cases', institutionId],
    queryFn: () => institutionsApi.cases(institutionId),
  })

  const inst = instQuery.data
  const cases = casesQuery.data?.items ?? []

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      <Link
        to="/institutions"
        className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-slate-800 transition"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Institutions</span>
      </Link>

      {instQuery.isLoading && <LoadingState label="Loading institution profile…" />}
      {inst && (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded bg-blue-100 text-blue-900 border border-blue-200">
                  {inst.aicte_permanent_id}
                </span>
                <span className="text-xs text-slate-500">•</span>
                <span className="text-xs font-bold text-slate-600">{inst.region_name} Region</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1">{inst.name}</h1>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                {inst.address}, {inst.district}, {inst.state} • Type: {inst.type}
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-600" />
              {inst.status}
            </span>
          </div>

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-slate-200 bg-slate-50/50">
              <SectionTitle
                title="Consolidated Multi-Bureau Grievance History"
                note="Complete timeline of complaints received across Regulation, PGRC, Approval, and Finance."
              />
              <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200">
                {cases.length} Total Cases
              </span>
            </div>

            {cases.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="gov-table min-w-[800px]">
                  <thead>
                    <tr>
                      <th>Docket ID</th>
                      <th>Bureau</th>
                      <th>Category</th>
                      <th>Received On</th>
                      <th>SLA Status</th>
                      <th>Current State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                        <td>
                          <Link to={`/cases/${c.id}`} className="font-bold text-blue-700 hover:underline">
                            {c.case_no}
                          </Link>
                        </td>
                        <td>
                          <span className="font-mono text-xs font-bold">{c.bureau_code ?? '—'}</span>
                        </td>
                        <td className="text-xs text-slate-700">{c.category_name ?? 'General'}</td>
                        <td className="font-mono text-xs text-slate-600">{formatDate(c.received_on)}</td>
                        <td><SlaBadge dueOn={c.expected_disposal_on} status={c.status} /></td>
                        <td><StatusBadge status={c.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8">
                <EmptyState title="No complaints recorded" message="No grievances have been registered for this campus." />
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
