import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight, Check, Download, Link2, RefreshCw, ShieldAlert, X,
} from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { adminApi, alertsApi, dashboardApi, overlapsApi, reportsApi } from '../api'
import { useAuth } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, formatDate, formatDateTime, LoadingState, PageHeader, SectionTitle, StatusBadge } from '../components/Shared'
import type { OverlapFlag, ReportType } from '../types'

const chartNavy = '#153a5b'
const chartTeal = '#0f766e'

export function DashboardPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [forwardMessage, setForwardMessage] = useState('')
  const refreshMs = 45000
  const summary = useQuery({ queryKey: ['dashboard', 'summary'], queryFn: dashboardApi.summary, refetchInterval: refreshMs })
  const workload = useQuery({ queryKey: ['dashboard', 'workload'], queryFn: dashboardApi.workload, refetchInterval: refreshMs })
  const trend = useQuery({ queryKey: ['dashboard', 'trend'], queryFn: dashboardApi.trend, refetchInterval: refreshMs })
  const ageing = useQuery({ queryKey: ['dashboard', 'ageing'], queryFn: dashboardApi.ageing, refetchInterval: refreshMs })
  const beyondSla = useQuery({ queryKey: ['dashboard', 'beyond-sla'], queryFn: dashboardApi.beyondSla, refetchInterval: refreshMs })
  const overlaps = useQuery({ queryKey: ['overlaps', 'dashboard-open'], queryFn: () => overlapsApi.list(undefined, 'OPEN'), refetchInterval: refreshMs })
  const forwardClock = useMutation({ mutationFn: () => adminApi.forwardDemo(30), onSuccess: async (result) => { setForwardMessage(`Demo date advanced to ${formatDate(result.as_of)}. ${result.overdue} overdue and ${result.escalations} escalation alerts recorded.`); await Promise.all([queryClient.invalidateQueries({ queryKey: ['dashboard'] }), queryClient.invalidateQueries({ queryKey: ['alerts'] }), queryClient.invalidateQueries({ queryKey: ['cases'] })]) } })
  const retry = () => { void summary.refetch(); void workload.refetch(); void trend.refetch(); void ageing.refetch(); void beyondSla.refetch(); void overlaps.refetch() }
  const hasError = summary.isError || workload.isError || trend.isError || ageing.isError || beyondSla.isError || overlaps.isError
  const loading = summary.isLoading || workload.isLoading || trend.isLoading || ageing.isLoading || beyondSla.isLoading || overlaps.isLoading
  const monthly = useMemo(() => (trend.data?.items ?? []).map((item) => ({ ...item, month: new Date(`${item.month}-01T00:00:00`).toLocaleDateString('en-IN', { month: 'short' }) })), [trend.data])
  const statusBars = useMemo(() => (workload.data?.items ?? []).map((bureau) => ({ bureau_code: bureau.bureau_code, ...bureau.status_counts })), [workload.data])
  const statusTiles = [
    { status: 'PENDING', label: 'Pending', tone: 'bg-amber-500' },
    { status: 'UNDER_PROCESS', label: 'Under process', tone: 'bg-blue-600' },
    { status: 'DISPOSED', label: 'Disposed', tone: 'bg-green-600' },
    { status: 'TRANSFERRED', label: 'Transferred', tone: 'bg-purple-600' },
    { status: 'ESCALATED', label: 'Escalated', tone: 'bg-red-600' },
  ]
  const ageingColors = ['bg-teal-600', 'bg-teal-700', 'bg-blue-600', 'bg-amber-500', 'bg-red-600']
  const beyondItems = beyondSla.data?.items ?? []
  const openFlags = overlaps.data?.items ?? []

  return <>
    <PageHeader title="Dashboard" helper="A quick view of case load, progress, and coordination flags." action={<div className="flex flex-wrap gap-2"><Link to="/cases" className="button-primary">All cases <ArrowRight className="h-4 w-4" /></Link>{user?.role === 'ADMIN' && <button className="button-secondary" onClick={() => forwardClock.mutate()} disabled={forwardClock.isPending}>{forwardClock.isPending ? 'Advancing…' : 'Advance demo 30 days'}</button>}</div>} />
    {forwardMessage && <div role="status" className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{forwardMessage}</div>}
    {forwardClock.isError && <div className="mb-4"><ErrorState message={forwardClock.error instanceof Error ? forwardClock.error.message : 'The demo clock could not be advanced.'} /></div>}
    {loading && <LoadingState label="Loading dashboard summary…" />}
    {hasError && <ErrorState message="Some dashboard information could not be loaded." retry={retry} />}
    {summary.data && <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">{statusTiles.map((tile) => <Link key={tile.status} to={`/cases?status=${tile.status}`} className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md" aria-label={`Open ${tile.label} cases`}><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{tile.label}</p><p className="mt-1 text-3xl font-bold text-slate-900">{summary.data.status_counts[tile.status] ?? 0}</p></div><span className={`grid h-10 w-10 place-items-center rounded-lg text-white ${tile.tone}`}><ArrowRight className="h-5 w-5 transition group-hover:translate-x-0.5" /></span></div><p className="mt-3 text-xs font-semibold text-teal-800">View matching cases</p></Link>)}<Link to="/cases?beyond_sla=true" className="group rounded-xl border border-red-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-red-300 hover:shadow-md" aria-label="Open beyond-SLA cases"><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-red-700">Beyond SLA</p><p className="mt-1 text-3xl font-bold text-slate-900">{beyondSla.data?.total ?? 0}</p></div><span className="grid h-10 w-10 place-items-center rounded-lg bg-red-600 text-white"><ArrowRight className="h-5 w-5 transition group-hover:translate-x-0.5" /></span></div><p className="mt-3 text-xs font-semibold text-red-700">View overdue cases</p></Link></div>}
    <div className="grid gap-5 xl:grid-cols-2">
      <Card className="p-5"><SectionTitle title="Cases by bureau and status" note="Each bureau bar is divided by the current case status." />{statusBars.length ? <div className="h-[320px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={statusBars} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="bureau_code" tickLine={false} axisLine={false} /><YAxis allowDecimals={false} tickLine={false} axisLine={false} /><Tooltip /><Bar dataKey="PENDING" name="Pending" stackId="status" fill="#d97706" /><Bar dataKey="UNDER_PROCESS" name="Under process" stackId="status" fill="#2563eb" /><Bar dataKey="DISPOSED" name="Disposed" stackId="status" fill="#16a34a" /><Bar dataKey="TRANSFERRED" name="Transferred" stackId="status" fill="#7c3aed" /><Bar dataKey="ESCALATED" name="Escalated" stackId="status" fill="#dc2626" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div> : <EmptyState title="No workload data" message="Bureau case totals will appear here." />}</Card>
      <Card className="p-5"><SectionTitle title="Monthly case trend" note="Cases received and disposed by month." />{monthly.length ? <div className="h-[320px]"><ResponsiveContainer width="100%" height="100%"><LineChart data={monthly} margin={{ top: 10, right: 15, left: -20, bottom: 10 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tickLine={false} axisLine={false} /><YAxis allowDecimals={false} tickLine={false} axisLine={false} /><Tooltip /><Line type="monotone" dataKey="received" name="Received" stroke={chartNavy} strokeWidth={3} dot={{ r: 3 }} /><Line type="monotone" dataKey="disposed" name="Disposed" stroke={chartTeal} strokeWidth={3} dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div> : <EmptyState title="No trend data" message="Monthly case activity will appear here." />}</Card>
    </div>
    <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <Card className="p-5"><SectionTitle title="Case ageing" note="Open cases grouped by the age bands returned by the API; the current contract combines 8–30 days." />{ageing.data?.items.length ? <div className="space-y-3">{ageing.data.items.map((item, index) => { const total = Math.max(1, summary.data?.open_cases ?? 0); return <div key={item.band}><div className="mb-1 flex justify-between text-sm"><span className="text-slate-600">{item.band}</span><span className="font-semibold text-slate-800">{item.cases}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${ageingColors[index] ?? 'bg-teal-600'}`} style={{ width: `${Math.min(100, item.cases / total * 100)}%` }} /></div></div> })}</div> : <EmptyState title="No ageing data" message="Open case ages will appear here." />}</Card>
      <Card className="overflow-hidden"><div className="flex items-center justify-between gap-3 p-5"><SectionTitle title="Beyond SLA" note="Open cases past their expected disposal date." /><Link to="/cases?beyond_sla=true" className="shrink-0 text-xs font-semibold text-teal-800 hover:underline">See all</Link></div>{beyondItems.length ? <div className="overflow-x-auto"><table className="gov-table min-w-[620px]"><thead><tr><th>Case / institution</th><th>Bureau</th><th>Due date</th><th>Status</th></tr></thead><tbody>{beyondItems.slice(0, 5).map((item) => <tr key={item.id}><td><Link to={`/cases/${item.id}`} className="font-semibold text-[#153a5b] hover:underline">{item.case_no}</Link><p className="mt-0.5 max-w-[260px] truncate text-xs text-slate-500">{item.institution_name ?? item.institution_id ?? 'Institution not resolved'}</p></td><td>{item.bureau_code ?? '—'}</td><td className="font-semibold text-red-700">{formatDate(item.expected_disposal_on)}</td><td><StatusBadge status={item.status} /></td></tr>)}</tbody></table></div> : <div className="px-5 pb-5"><EmptyState title="No beyond-SLA cases" message="No open case is currently past its expected disposal date." /></div>}</Card>
    </div>
    <Card className="mt-5 overflow-hidden"><div className="flex items-center justify-between gap-3 p-5"><SectionTitle title="Open overlaps" note="Potential cross-bureau pairs and institution-level coordination flags." /><Link to="/overlaps" className="shrink-0 text-xs font-semibold text-teal-800 hover:underline">Open Overlap Center</Link></div>{openFlags.length ? <div className="divide-y divide-slate-100">{openFlags.slice(0, 5).map((flag) => <Link key={flag.id} to="/overlaps" className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 hover:bg-slate-50"><div className="flex min-w-0 items-center gap-3"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${flag.tier === 'A' ? 'bg-amber-100 text-amber-900' : 'bg-teal-100 text-teal-900'}`}>Tier {flag.tier}</span><span className="truncate text-sm font-semibold text-slate-800">{flag.institution_name ?? 'Institution coordination'}</span></div><span className="text-xs text-slate-500">{flag.cases.length} cases · {flag.state}</span></Link>)}</div> : <div className="px-5 pb-5"><EmptyState title="No open overlaps" message="Potential coordination flags will appear here." /></div>}</Card>
  </>
}

export function OverlapsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [tier, setTier] = useState('')
  const [state, setState] = useState('OPEN')
  const [selected, setSelected] = useState<OverlapFlag | null>(null)
  const [linkOpen, setLinkOpen] = useState(false)
  const [leadBureau, setLeadBureau] = useState('')
  const [note, setNote] = useState('')
  const [message, setMessage] = useState('')
  const query = useQuery({ queryKey: ['overlaps', tier, state], queryFn: () => overlapsApi.list(tier || undefined, state || undefined) })
  const invalidate = () => Promise.all([queryClient.invalidateQueries({ queryKey: ['overlaps'] }), queryClient.invalidateQueries({ queryKey: ['institutions'] }), queryClient.invalidateQueries({ queryKey: ['dashboard'] })])
  const linkMutation = useMutation({ mutationFn: () => selected ? overlapsApi.link(selected.id, leadBureau, note.trim()) : Promise.reject(new Error('Choose a flag first.')), onSuccess: async () => { setSelected(null); setLinkOpen(false); setMessage('Cases linked for coordination.'); await invalidate() } })
  const dismissMutation = useMutation({ mutationFn: (id: string) => overlapsApi.dismiss(id), onSuccess: async (_, id) => { if (selected?.id === id) setSelected(null); setMessage('Overlap flag dismissed.'); await invalidate() } })
  const flags = query.data?.items ?? []

  function canAct() {
    // Cross-bureau overlap mutations require authority over both cases; Admin is the safe UI scope.
    return user?.role === 'ADMIN'
  }

  function review(flag: OverlapFlag) {
    setSelected(flag)
    setLinkOpen(false)
    setLeadBureau(flag.cases[0]?.bureau_id ?? '')
    setNote('')
  }

  return <>
    <PageHeader title="Potential Overlapping Cases - Coordination Required" helper="Review possible duplicate complaints and agree which bureau will coordinate follow-up." action={<button className="button-secondary" onClick={() => void query.refetch()}><RefreshCw className="h-4 w-4" />Refresh</button>} />
    {message && <div role="status" className="mb-4 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"><Check className="h-4 w-4" />{message}<button onClick={() => setMessage('')} className="ml-auto text-green-900 underline">Dismiss</button></div>}
    {linkMutation.isError && <div className="mb-4"><ErrorState message={linkMutation.error instanceof Error ? linkMutation.error.message : 'The cases could not be linked.'} /></div>}
    {dismissMutation.isError && <div className="mb-4"><ErrorState message={dismissMutation.error instanceof Error ? dismissMutation.error.message : 'The flag could not be dismissed.'} /></div>}
    <Card className="mb-5 p-4"><div className="flex flex-wrap gap-3"><label className="text-xs font-semibold text-slate-600">Flag tier<select className="form-control mt-1.5 min-w-36" value={tier} onChange={(event) => setTier(event.target.value)}><option value="">All tiers</option><option value="A">Tier A · Institution</option><option value="B">Tier B · Case pair</option></select></label><label className="text-xs font-semibold text-slate-600">State<select className="form-control mt-1.5 min-w-36" value={state} onChange={(event) => setState(event.target.value)}><option value="">All states</option><option value="OPEN">Open</option><option value="CONFIRMED">Confirmed</option><option value="DISMISSED">Dismissed</option></select></label></div></Card>
    {query.isLoading && <LoadingState label="Loading overlap flags…" />}
    {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Overlap flags could not be loaded.'} retry={() => void query.refetch()} />}
    {query.data && !flags.length && <EmptyState title="No overlap flags" message="No flags match these filters." />}
    {flags.length > 0 && <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="gov-table min-w-[900px]"><thead><tr><th>Tier</th><th>Institution</th><th>Case pair</th><th>Score</th><th>Reasons</th><th>State</th><th>Review</th></tr></thead><tbody>{flags.map((flag) => <tr key={flag.id}><td><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${flag.tier === 'A' ? 'bg-amber-100 text-amber-900' : 'bg-teal-100 text-teal-900'}`}>Tier {flag.tier}</span></td><td className="max-w-[190px] whitespace-normal font-semibold">{flag.institution_name ?? 'Synthetic institution'}</td><td><div className="space-y-1 text-xs">{flag.cases.slice(0, 2).map((item) => <p key={item.id} className="font-medium text-slate-700">{item.case_no} <span className="text-slate-400">· {item.bureau_code ?? 'Bureau'}</span></p>)}</div></td><td><OverlapScore score={flag.score} tier={flag.tier} /></td><td><div className="flex max-w-[250px] flex-wrap gap-1">{flag.reasons.length ? flag.reasons.map((reason) => <span key={reason} className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-700">{reason.replace(/_/g, ' ')}</span>) : <span className="text-xs text-slate-400">No reason details</span>}</div></td><td><span className={`rounded-full px-2 py-1 text-xs font-bold ${flag.state === 'OPEN' ? 'bg-red-50 text-red-700' : flag.state === 'CONFIRMED' ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-600'}`}>{flag.state}</span></td><td><button className="button-secondary whitespace-nowrap" onClick={() => review(flag)}>Compare cases <ArrowRight className="h-4 w-4" /></button></td></tr>)}</tbody></table></div></Card>}
    {selected && <div className="fixed inset-0 z-40 bg-slate-950/45" onMouseDown={(event) => { if (event.target === event.currentTarget && !linkMutation.isPending) setSelected(null) }}><aside role="dialog" aria-modal="true" aria-label="Compare overlapping cases" className="ml-auto flex h-full w-full max-w-5xl flex-col overflow-y-auto bg-slate-50 shadow-2xl"><div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4"><div><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${selected.tier === 'A' ? 'bg-amber-100 text-amber-900' : 'bg-teal-100 text-teal-900'}`}>Tier {selected.tier}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">{selected.state}</span></div><h2 className="mt-2 text-lg font-bold text-slate-900">Compare case records</h2><p className="text-sm text-slate-600">{selected.institution_name ?? 'Synthetic institution'}</p></div><button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Close comparison" onClick={() => setSelected(null)}><X className="h-5 w-5" /></button></div><div className="flex-1 p-5"><div className="grid gap-4 md:grid-cols-2">{selected.cases.slice(0, 2).map((caseItem, index) => <Card key={caseItem.id} className="p-5"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Case {index + 1}</p><h3 className="mt-1 text-lg font-bold text-[#153a5b]">{caseItem.case_no}</h3><p className="mt-1 text-sm text-slate-600">{caseItem.bureau_code ?? caseItem.bureau_id} · {caseItem.status.replace(/_/g, ' ')}</p><dl className="mt-5 space-y-3 border-t border-slate-100 pt-4 text-sm"><div><dt className="text-xs font-semibold uppercase text-slate-500">Received</dt><dd className="mt-0.5 font-medium text-slate-800">{formatDate(caseItem.received_on)}</dd></div><div><dt className="text-xs font-semibold uppercase text-slate-500">Category ID</dt><dd className="mt-0.5 font-medium text-slate-800">{caseItem.category_id}</dd></div><div><dt className="text-xs font-semibold uppercase text-slate-500">Summary</dt><dd className="mt-0.5 leading-6 text-slate-700">{caseItem.summary ?? 'No summary provided.'}</dd></div><div><dt className="text-xs font-semibold uppercase text-slate-500">Complainant reference</dt><dd className="mt-0.5 font-medium text-slate-800">{caseItem.complainant_ref ?? 'Not available'}</dd></div></dl><Link to={`/cases/${caseItem.id}`} className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-teal-800 hover:underline">Open case <ArrowRight className="h-4 w-4" /></Link></Card>)}</div>{selected.cases.length < 2 && <div className="mt-4"><EmptyState title="Only one case is available" message="This institution-level flag does not include two case records to compare." /></div>}<Card className="mt-4 p-5"><SectionTitle title="Why these records were flagged" note="Reason codes returned by the overlap service." /><div className="flex flex-wrap gap-2">{selected.reasons.length ? selected.reasons.map((reason) => <span key={reason} className="rounded-full bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-900">{reason.replace(/_/g, ' ')}</span>) : <span className="text-sm text-slate-500">No reason details were returned.</span>}</div>{selected.score !== null && selected.score !== undefined && <div className="mt-4 max-w-sm"><OverlapScore score={selected.score} tier={selected.tier} /></div>}</Card></div><div className="sticky bottom-0 flex flex-wrap justify-end gap-2 border-t border-slate-200 bg-white px-5 py-4">{selected.state === 'OPEN' && selected.tier === 'B' && canAct() && <button className="button-primary" onClick={() => setLinkOpen(true)}><Link2 className="h-4 w-4" />Link cases</button>}{selected.state === 'OPEN' && canAct() && <button className="button-secondary text-red-700" disabled={dismissMutation.isPending} onClick={() => dismissMutation.mutate(selected.id)}>Dismiss flag</button>}<button className="button-secondary" onClick={() => setSelected(null)}>Close</button></div></aside></div>}
    {linkOpen && selected && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-4"><section role="dialog" aria-modal="true" aria-labelledby="link-dialog-title" className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl"><div className="flex items-start justify-between gap-3"><div><h2 id="link-dialog-title" className="text-lg font-bold">Link cases for coordination</h2><p className="mt-1 text-sm text-slate-600">Choose one of the case bureaus to lead follow-up.</p></div><button className="rounded-lg p-1 text-slate-500 hover:bg-slate-100" aria-label="Close link dialog" onClick={() => setLinkOpen(false)} disabled={linkMutation.isPending}><X className="h-5 w-5" /></button></div><form onSubmit={(event) => { event.preventDefault(); linkMutation.mutate() }} className="mt-5 space-y-4"><label className="block text-sm font-semibold">Lead bureau<select required className="form-control mt-1.5" value={leadBureau} onChange={(event) => setLeadBureau(event.target.value)}><option value="">Select a bureau</option>{[...new Map(selected.cases.map((caseItem) => [caseItem.bureau_id, caseItem.bureau_code ?? caseItem.bureau_id])).entries()].map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><label className="block text-sm font-semibold">Coordination note<textarea className="form-control mt-1.5" rows={3} maxLength={4000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Optional note for both case histories" /></label><div className="flex justify-end gap-2"><button type="button" className="button-secondary" onClick={() => setLinkOpen(false)} disabled={linkMutation.isPending}>Cancel</button><button type="submit" className="button-primary" disabled={linkMutation.isPending || !leadBureau}>{linkMutation.isPending ? 'Linking…' : 'Confirm link'}</button></div></form></section></div>}
  </>
}

function OverlapScore({ score, tier }: { score?: number | null; tier: 'A' | 'B' }) {
  const percent = score === null || score === undefined ? null : Math.max(0, Math.min(100, score * 100))
  return <div className="min-w-24">{percent === null ? <span className="text-xs text-slate-500">{tier === 'A' ? 'Institution flag' : 'Not scored'}</span> : <><div className="mb-1 flex justify-between gap-2 text-[10px] font-semibold text-slate-600"><span>Score</span><span>{score?.toFixed(2)}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-600" style={{ width: `${percent}%` }} /></div></>}</div>
}

export function AlertsPage() {
  const client = useQueryClient()
  const [readFilter, setReadFilter] = useState<'all' | 'unread' | 'read'>('all')
  const query = useQuery({ queryKey: ['alerts', readFilter], queryFn: () => alertsApi.list(readFilter === 'unread') })
  const mutation = useMutation({ mutationFn: (id: string) => alertsApi.markRead(id), onSuccess: async () => { await Promise.all([client.invalidateQueries({ queryKey: ['alerts'] }), client.invalidateQueries({ queryKey: ['dashboard'] })] ) } })
  const alerts = (query.data?.items ?? []).filter((item) => readFilter === 'all' || (readFilter === 'read' ? Boolean(item.read_at) : !item.read_at))
  const badgeTone: Record<string, string> = { DUE_SOON: 'bg-amber-100 text-amber-900', OVERDUE: 'bg-red-100 text-red-900', REMINDER: 'bg-blue-100 text-blue-900', ESCALATION: 'bg-rose-100 text-rose-900', OVERLAP: 'bg-teal-100 text-teal-900' }
  return <>
    <PageHeader title="Alerts" helper="See due-date reminders and coordination items that need attention." action={<label className="text-xs font-semibold text-slate-600">Read status<select className="form-control mt-1.5 min-w-36" value={readFilter} onChange={(event) => setReadFilter(event.target.value as typeof readFilter)}><option value="all">All alerts</option><option value="unread">Unread</option><option value="read">Read</option></select></label>} />
    {mutation.isError && <div className="mb-4"><ErrorState message="The alert could not be marked as read." /></div>}
    {query.isLoading && <LoadingState label="Loading alerts…" />}
    {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Alerts could not be loaded.'} retry={() => void query.refetch()} />}
    {query.data && alerts.length === 0 && <EmptyState title={readFilter === 'unread' ? 'No unread alerts' : readFilter === 'read' ? 'No read alerts' : 'No alerts'} message="New SLA and coordination alerts will appear here." />}
    {query.data && alerts.length > 0 && <div className="space-y-3">{alerts.map((item) => <Card key={item.id} className={`flex flex-wrap items-start justify-between gap-4 p-4 ${item.read_at ? '' : 'border-l-4 border-l-amber-500'}`}><div className="flex min-w-0 flex-1 gap-3"><div className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg ${item.type === 'OVERDUE' || item.type === 'ESCALATION' ? 'bg-red-50 text-red-700' : item.type === 'OVERLAP' ? 'bg-teal-50 text-teal-700' : 'bg-amber-50 text-amber-700'}`}><ShieldAlert className="h-5 w-5" /></div><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${badgeTone[item.type] ?? 'bg-slate-100 text-slate-700'}`}>{item.type.replace(/_/g, ' ')}</span>{!item.read_at ? <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900">UNREAD</span> : <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600">READ</span>}</div><p className="mt-2 text-sm text-slate-800">{item.message}</p><p className="mt-1 text-xs text-slate-500">{formatDateTime(item.created_at)}{item.due_on ? ` · due ${formatDate(item.due_on)}` : ''}</p>{item.case_id && <Link className="mt-2 inline-block text-xs font-semibold text-teal-800 hover:underline" to={`/cases/${item.case_id}`}>Open case details</Link>}</div></div>{!item.read_at && <button className="button-secondary" onClick={() => mutation.mutate(item.id)} disabled={mutation.isPending}><Check className="h-4 w-4" />Mark read</button>}</Card>)}</div>}
  </>
}

const reportTypes: { id: ReportType; label: string }[] = [
  { id: 'bureau', label: 'Bureau workload' }, { id: 'region', label: 'Regional summary' },
  { id: 'institution', label: 'Institution cases' }, { id: 'ageing', label: 'Case ageing' },
  { id: 'disposal-rate', label: 'Disposal rate' }, { id: 'status', label: 'Case status' },
  { id: 'overlaps', label: 'Overlap flags' }, { id: 'monthly', label: 'Monthly trend' },
]

export function ReportsPage() {
  const [type, setType] = useState<ReportType>('bureau')
  const [downloadError, setDownloadError] = useState('')
  const [downloading, setDownloading] = useState<'csv' | 'json' | null>(null)
  const query = useQuery({ queryKey: ['report', type], queryFn: () => reportsApi.get(type, 'json') })
  const rows = query.data && !(query.data instanceof Blob) ? query.data.items : []
  async function download(format: 'csv' | 'json') {
    setDownloadError('')
    setDownloading(format)
    try {
      const result = await reportsApi.get(type, format)
      const blob = format === 'csv' ? result instanceof Blob ? result : new Blob([], { type: 'text/csv' }) : new Blob([JSON.stringify(result instanceof Blob ? await result.text() : result, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${type}.${format}`
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 0)
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : 'The report could not be downloaded.')
    } finally {
      setDownloading(null)
    }
  }
  return <>
    <PageHeader title="Reports" helper="Choose a report, preview its rows, and download a CSV or JSON copy." action={<div className="flex gap-2"><button className="button-secondary" onClick={() => void download('csv')} disabled={query.isLoading || downloading !== null}><Download className="h-4 w-4" />{downloading === 'csv' ? 'Preparing…' : 'CSV'}</button><button className="button-primary" onClick={() => void download('json')} disabled={query.isLoading || downloading !== null}><Download className="h-4 w-4" />{downloading === 'json' ? 'Preparing…' : 'JSON'}</button></div>} />
    <Card className="mb-5 p-4"><label className="block max-w-md text-xs font-semibold text-slate-600">Report<select className="form-control mt-1.5" value={type} onChange={(event) => setType(event.target.value as ReportType)}>{reportTypes.map((report) => <option key={report.id} value={report.id}>{report.label}</option>)}</select></label></Card>
    {downloadError && <div className="mb-4"><ErrorState message={downloadError} /></div>}
    {query.isLoading && <LoadingState label="Building report…" />}
    {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'This report could not be loaded.'} retry={() => void query.refetch()} />}
    {query.data && rows.length === 0 && <EmptyState title="This report is empty" message="There are no rows to display for this report." />}
    {rows.length > 0 && <ReportTable rows={rows} />}
  </>
}

function ReportTable({ rows }: { rows: Record<string, unknown>[] }) {
  const columns = Object.keys(rows[0])
  return <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="gov-table min-w-full"><thead><tr>{columns.map((column) => <th key={column}>{column.replace(/_/g, ' ')}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column} className="whitespace-nowrap">{typeof row[column] === 'number' && column.includes('rate') ? `${(Number(row[column]) * 100).toFixed(1)}%` : String(row[column] ?? '—')}</td>)}</tr>)}</tbody></table></div></Card>
}

interface EvaluationResult {
  disclaimer?: string
  source?: string
  split?: { strategy?: string; seed?: number; train_rows?: number; test_rows?: number }
  model?: { selected_threshold?: number; train_metrics?: Metrics }
  held_out?: Metrics
  baseline?: { rule?: string } & Metrics
  false_positives?: { case_a: string; case_b: string; score: number }[]
  misses?: { case_a: string; case_b: string; score: number }[]
}
interface Metrics { precision?: number; recall?: number; f1?: number; confusion_matrix?: { tn?: number; fp?: number; fn?: number; tp?: number } }

export function EvaluationPage() {
  const query = useQuery({ queryKey: ['evaluation'], queryFn: adminApi.evaluation })
  const result = query.data as EvaluationResult | undefined
  return <>
    <PageHeader title="Evaluation" helper="Review measured overlap results from the synthetic labeled dataset." />
    <div className="mb-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm font-semibold text-amber-950">Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.</div>
    {query.isLoading && <LoadingState label="Loading evaluation report…" />}
    {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'The evaluation report could not be loaded.'} retry={() => void query.refetch()} />}
    {result && <>
      <div className="mb-5 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700"><p className="font-bold">Evaluation report note</p><p className="mt-1">{result.disclaimer ?? 'Measured on synthetic evaluation splits.'}</p></div>
      <Card className="mb-5 p-5"><SectionTitle title="Evaluation setup" note="The decision threshold was tuned on training groups only." /><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><EvaluationField label="Split" value={`${result.split?.train_rows ?? 19} train / ${result.split?.test_rows ?? 13} held out`} /><EvaluationField label="Grouping" value={result.split?.strategy ?? 'Group split'} /><EvaluationField label="Fixed seed" value={String(result.split?.seed ?? 42)} /><EvaluationField label="Selected threshold" value={result.model?.selected_threshold != null ? result.model.selected_threshold.toFixed(4) : '0.6610'} /></div></Card>
      <div className="grid gap-5 xl:grid-cols-2">{result.held_out && <MetricsCard title="Held-out model" metrics={result.held_out} />}{result.baseline && <MetricsCard title="Simple baseline" subtitle={result.baseline.rule ?? 'Heuristic rule'} metrics={result.baseline} />}</div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2"><ExamplesCard title="False positives" cases={result.false_positives} /><ExamplesCard title="Misses" cases={result.misses} /></div>
    </>}
  </>
}

function EvaluationField({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 text-sm font-semibold text-slate-900">{value}</p></div>
}

function MetricsCard({ title, subtitle, metrics }: { title: string; subtitle?: string; metrics: Metrics }) {
  const p = metrics.precision ?? 0
  const r = metrics.recall ?? 0
  const f = metrics.f1 ?? 0
  const cm = metrics.confusion_matrix ?? { tn: 0, fp: 0, fn: 0, tp: 0 }
  return <Card className="p-5"><SectionTitle title={title} note={subtitle ?? 'Precision, recall, and F1 from the held-out split.'} /><div className="grid grid-cols-3 gap-3">{[['Precision', p], ['Recall', r], ['F1', f]].map(([label, value]) => <div key={String(label)} className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-xl font-bold text-slate-900">{(Number(value) * 100).toFixed(1)}%</p></div>)}</div><div className="mt-4 grid grid-cols-4 gap-2 text-center text-xs"><MatrixCell label="TN" value={cm.tn ?? 0} /><MatrixCell label="FP" value={cm.fp ?? 0} /><MatrixCell label="FN" value={cm.fn ?? 0} /><MatrixCell label="TP" value={cm.tp ?? 0} /></div></Card>
}

function MatrixCell({ label, value }: { label: string; value: number }) {
  return <div className="rounded-md border border-slate-200 p-2"><p className="text-slate-500">{label}</p><p className="mt-1 text-base font-bold text-slate-900">{value}</p></div>
}

function ExamplesCard({ title, cases }: { title: string; cases?: { case_a: string; case_b: string; score: number }[] }) {
  const list = Array.isArray(cases) ? cases : []
  return <Card className="p-5"><SectionTitle title={title} note="Examples from the held-out group split." />{list.length ? <ul className="space-y-2">{list.map((item) => <li key={`${item.case_a}-${item.case_b}`} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm"><span className="font-medium text-slate-800">{item.case_a} · {item.case_b}</span><span className="shrink-0 text-xs text-slate-500">score {item.score.toFixed(3)}</span></li>)}</ul> : <EmptyState title={`No ${title.toLowerCase()} in this split`} message="The held-out data produced no examples for this category." />}</Card>
}

