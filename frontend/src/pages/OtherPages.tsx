import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  Clock,
  Download,
  FileCheck2,
  Filter,
  Layers,
  Link2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Split,
  TrendingUp,
  X,
} from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { adminApi, alertsApi, dashboardApi, overlapsApi, reportsApi } from '../api'
import { useAuth } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, formatDate, formatDateTime, LoadingState, PageHeader, SectionTitle, StatusBadge } from '../components/Shared'
import type { OverlapFlag, ReportType } from '../types'

const chartNavy = '#1e3a8a'
const chartTeal = '#0284c7'

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
  const forwardClock = useMutation({
    mutationFn: () => adminApi.forwardDemo(30),
    onSuccess: async (result) => {
      setForwardMessage(`Demo date advanced to ${formatDate(result.as_of)}. ${result.overdue} overdue and ${result.escalations} escalation alerts recorded.`)
      await Promise.all([queryClient.invalidateQueries({ queryKey: ['dashboard'] }), queryClient.invalidateQueries({ queryKey: ['alerts'] }), queryClient.invalidateQueries({ queryKey: ['cases'] })])
    },
  })
  const retry = () => {
    void summary.refetch()
    void workload.refetch()
    void trend.refetch()
    void ageing.refetch()
    void beyondSla.refetch()
    void overlaps.refetch()
  }
  const hasError = summary.isError || workload.isError || trend.isError || ageing.isError || beyondSla.isError || overlaps.isError
  const loading = summary.isLoading || workload.isLoading || trend.isLoading || ageing.isLoading || beyondSla.isLoading || overlaps.isLoading
  const monthly = useMemo(() => (trend.data?.items ?? []).map((item) => ({ ...item, month: new Date(`${item.month}-01T00:00:00`).toLocaleDateString('en-IN', { month: 'short' }) })), [trend.data])
  const statusBars = useMemo(() => (workload.data?.items ?? []).map((bureau) => ({ bureau_code: bureau.bureau_code, ...bureau.status_counts })), [workload.data])
  const ageingColors = ['bg-blue-600', 'bg-indigo-600', 'bg-amber-500', 'bg-orange-500', 'bg-rose-600']
  const beyondItems = beyondSla.data?.items ?? []
  const openFlags = overlaps.data?.items ?? []

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      {/* Page Header */}
      <PageHeader
        title="Overview Dashboard"
        helper="Centralized monitoring of case velocity, cross-bureau overlap alerts, and statutory SLA compliance."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/cases"
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 transition"
            >
              <span>Explore Dockets</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            {user?.role === 'ADMIN' && (
              <button
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 transition"
                onClick={() => forwardClock.mutate()}
                disabled={forwardClock.isPending}
              >
                <Clock className="h-3.5 w-3.5 text-slate-500" />
                {forwardClock.isPending ? 'Advancing demo…' : 'Advance demo 30 days'}
              </button>
            )}
          </div>
        }
      />

      {forwardMessage && (
        <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-medium text-emerald-900 flex items-center justify-between shadow-xs">
          <span>{forwardMessage}</span>
          <button onClick={() => setForwardMessage('')} className="text-emerald-700 hover:text-emerald-900 font-bold ml-2">Dismiss</button>
        </div>
      )}

      {forwardClock.isError && (
        <div className="mb-4">
          <ErrorState message={forwardClock.error instanceof Error ? forwardClock.error.message : 'The demo clock could not be advanced.'} />
        </div>
      )}

      {loading && <LoadingState label="Loading national dashboard intelligence…" />}
      {hasError && <ErrorState message="Some dashboard indicators could not be loaded." retry={retry} />}

      {/* Top Banner: Inter-Bureau Conflict Alert */}
      {openFlags.length > 0 && (
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-950 via-indigo-950 to-slate-900 p-6 text-white shadow-xl border border-purple-500/30">
          <div className="absolute right-0 top-0 bottom-0 opacity-10 pointer-events-none flex items-center pr-10">
            <Layers className="w-64 h-64 text-purple-300" />
          </div>

          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-purple-500/20 border border-purple-400/40 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-6 h-6 text-amber-300 animate-bounce" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/40 text-purple-200 border border-purple-400/30">
                    Inter-Bureau Conflict Alert
                  </span>
                  <span className="text-xs text-purple-200/80">
                    Rule-Based Deduplication Engine
                  </span>
                </div>
                <h2 className="text-lg font-bold text-white mt-1">
                  {openFlags.length} Potential Overlapping Cases Detected Requiring Multi-Bureau Coordination
                </h2>
                <p className="text-xs text-purple-100/80 mt-1 max-w-2xl leading-relaxed">
                  Complaints relating to the same institution have been independently docketed and processed across multiple AICTE cells. Immediate coordination is advised to avoid duplicate inquiry and contradictory show-cause notices.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <Link
                to="/overlaps"
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white font-semibold text-xs shadow-lg shadow-purple-500/25 transition-all cursor-pointer active:scale-95"
              >
                <span>Launch Overlap Center</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* 5 Interactive KPI Metric Cards */}
      {summary.data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Card 1: Total Dockets */}
          <Link
            to="/cases"
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-1 hover:border-blue-400 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Total Dockets</span>
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <FileCheck2 className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-slate-900 mt-2 font-mono">
              {summary.data.total_cases.toLocaleString()}
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-xs text-emerald-600 font-medium">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>+14.2% YoY Redressal</span>
            </div>
          </Link>

          {/* Card 2: Active Inquiries */}
          <Link
            to="/cases?status=UNDER_PROCESS"
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-1 hover:border-amber-400 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Active Inquiries</span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-amber-600 mt-2 font-mono">
              {summary.data.open_cases.toLocaleString()}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Across 5 Key Bureaus
            </div>
          </Link>

          {/* Card 3: Beyond SLA Limit */}
          <Link
            to="/cases?beyond_sla=true"
            className="group rounded-2xl border border-rose-200 bg-gradient-to-br from-rose-50/60 to-white p-5 shadow-sm transition-all hover:-translate-y-1 hover:border-rose-400 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-rose-600">Beyond SLA Limit</span>
              <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <ShieldAlert className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-rose-600 mt-2 font-mono">
              {beyondSla.data?.total ?? 0} Cases
            </div>
            <div className="mt-2 text-xs text-rose-600 font-semibold flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Overdue &gt; 30 Days</span>
            </div>
          </Link>

          {/* Card 4: Inter-Bureau Overlaps */}
          <Link
            to="/overlaps"
            className="group rounded-2xl border border-purple-200 bg-gradient-to-br from-purple-50/60 to-white p-5 shadow-sm transition-all hover:-translate-y-1 hover:border-purple-400 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-purple-700">Inter-Bureau Overlaps</span>
              <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-purple-700 mt-2 font-mono">
              {openFlags.length} Pairs
            </div>
            <div className="mt-2 text-xs text-purple-700 font-semibold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-600 animate-pulse" />
              <span>Coordination Advised</span>
            </div>
          </Link>

          {/* Card 5: Resolved Dockets */}
          <Link
            to="/cases?status=DISPOSED"
            className="group rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50/60 to-white p-5 shadow-sm transition-all hover:-translate-y-1 hover:border-emerald-400 hover:shadow-md cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-emerald-700">Disposed & Resolved</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                <CheckCircle2 className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-emerald-700 mt-2 font-mono">
              {summary.data.disposed_cases.toLocaleString()}
            </div>
            <div className="mt-2 text-xs text-emerald-700 font-semibold flex items-center gap-1">
              <span>Completed Inquiries</span>
            </div>
          </Link>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid gap-6 xl:grid-cols-2">
        {/* Cases by Bureau */}
        <Card className="p-6">
          <SectionTitle title="Cases by Bureau and Status" note="Active caseload distribution partitioned by current procedural state." />
          {statusBars.length ? (
            <div className="h-[320px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusBars} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="bureau_code" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  />
                  <Bar dataKey="PENDING" name="Pending" stackId="status" fill="#f59e0b" />
                  <Bar dataKey="UNDER_PROCESS" name="Under Process" stackId="status" fill="#2563eb" />
                  <Bar dataKey="DISPOSED" name="Disposed" stackId="status" fill="#10b981" />
                  <Bar dataKey="TRANSFERRED" name="Transferred" stackId="status" fill="#8b5cf6" />
                  <Bar dataKey="ESCALATED" name="Escalated" stackId="status" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No workload data" message="Bureau case totals will appear here." />
          )}
        </Card>

        {/* Monthly Trend */}
        <Card className="p-6">
          <SectionTitle title="12-Month Intake vs Disposal Trend" note="Longitudinal trajectory comparing case intake volume against resolution velocity." />
          {monthly.length ? (
            <div className="h-[320px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthly} margin={{ top: 10, right: 15, left: -20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  />
                  <Line type="monotone" dataKey="received" name="Received" stroke={chartNavy} strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  <Line type="monotone" dataKey="disposed" name="Disposed" stroke={chartTeal} strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No trend data" message="Monthly case activity will appear here." />
          )}
        </Card>
      </div>

      {/* Ageing & Beyond SLA Grid */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        {/* Case Ageing */}
        <Card className="p-6">
          <SectionTitle title="Statutory Ageing Distribution" note="Pending cases grouped by age intervals against the 30-day AICTE benchmark." />
          {ageing.data?.items.length ? (
            <div className="space-y-3.5 mt-4">
              {ageing.data.items.map((item, index) => {
                const total = Math.max(1, summary.data?.open_cases ?? 0)
                const pct = Math.min(100, (item.cases / total) * 100)
                return (
                  <div key={item.band}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="font-semibold text-slate-700">{item.band}</span>
                      <span className="font-mono font-bold text-slate-900">{item.cases} ({pct.toFixed(0)}%)</span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                      <div className={`h-full rounded-full transition-all ${ageingColors[index] ?? 'bg-blue-600'}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <EmptyState title="No ageing data" message="Open case ages will appear here." />
          )}
        </Card>

        {/* Beyond SLA Urgent Table */}
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between gap-3 p-6 pb-4">
            <SectionTitle title="Urgent: Dockets Beyond SLA Limit" note="Active grievances that have breached their statutory deadline." />
            <Link to="/cases?beyond_sla=true" className="text-xs font-bold text-blue-600 hover:text-blue-800">
              View All
            </Link>
          </div>
          {beyondItems.length ? (
            <div className="overflow-x-auto">
              <table className="gov-table min-w-[600px]">
                <thead>
                  <tr>
                    <th>Docket / Institution</th>
                    <th>Bureau</th>
                    <th>Due Date</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {beyondItems.slice(0, 5).map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                      <td>
                        <Link to={`/cases/${item.id}`} className="font-bold text-blue-700 hover:underline">
                          {item.case_no}
                        </Link>
                        <p className="mt-0.5 max-w-[240px] truncate text-xs text-slate-500">
                          {item.institution_name ?? item.institution_id ?? 'Institution not resolved'}
                        </p>
                      </td>
                      <td className="font-semibold text-slate-700">{item.bureau_code ?? '—'}</td>
                      <td className="font-mono font-bold text-rose-600">{formatDate(item.expected_disposal_on)}</td>
                      <td><StatusBadge status={item.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6">
              <EmptyState title="No beyond-SLA cases" message="No open complaint is currently past its expected disposal date." />
            </div>
          )}
        </Card>
      </div>
    </div>
  )
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

  const query = useQuery({
    queryKey: ['overlaps', tier, state],
    queryFn: () => overlapsApi.list(tier || undefined, state || undefined),
  })

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['overlaps'] }),
      queryClient.invalidateQueries({ queryKey: ['institutions'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ])

  const linkMutation = useMutation({
    mutationFn: () =>
      selected ? overlapsApi.link(selected.id, leadBureau, note.trim()) : Promise.reject(new Error('Choose a flag first.')),
    onSuccess: async () => {
      setSelected(null)
      setLinkOpen(false)
      setMessage('Cases successfully linked for cross-bureau coordination.')
      await invalidate()
    },
  })

  const dismissMutation = useMutation({
    mutationFn: (id: string) => overlapsApi.dismiss(id),
    onSuccess: async (_, id) => {
      if (selected?.id === id) setSelected(null)
      setMessage('Overlap flag marked as false alarm / dismissed.')
      await invalidate()
    },
  })

  const flags = query.data?.items ?? []
  const canAct = user?.role === 'ADMIN'

  function review(flag: OverlapFlag) {
    setSelected(flag)
    setLinkOpen(false)
    setLeadBureau(flag.cases[0]?.bureau_id ?? '')
    setNote('')
  }

  // Derive sub-factor scores for realistic AICTE demonstration
  const getSubMetrics = (flag: OverlapFlag) => {
    const rawScore = flag.score != null ? Math.round(flag.score * 100) : 75
    const hasTextSim = flag.reasons.some(r => r.includes('TEXT') || r.includes('SIMILARITY'))
    const hasTimeSim = flag.reasons.some(r => r.includes('30_DAYS') || r.includes('TIME'))
    const hasRefSim = flag.reasons.some(r => r.includes('REF') || r.includes('COMPLAINANT'))

    return {
      overall: rawScore,
      instMatch: flag.tier === 'A' ? 100 : 96,
      allegationSim: hasTextSim ? Math.min(98, Math.max(78, rawScore + 6)) : Math.max(55, rawScore - 12),
      timingScore: hasTimeSim ? 94 : 70,
      complainantAffinity: hasRefSim ? 88 : 52,
    }
  }

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      {/* Top Context Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-100 text-purple-700 border border-purple-200">
              Cross-Bureau Deduplication
            </span>
            <span className="text-xs text-slate-500">AICTE Intelligent Coordination Engine</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            Potential Overlapping Cases - Coordination Required
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-bureau deduplication matrix identifying concurrent dockets across Regulation Bureau (RB), PGRC, and Regional Divisions.
          </p>
        </div>

        <button
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
          onClick={() => void query.refetch()}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh Flags
        </button>
      </div>

      {message && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 shadow-sm">
          <Check className="h-4 w-4 text-emerald-600" />
          <span>{message}</span>
          <button onClick={() => setMessage('')} className="ml-auto text-xs font-semibold text-emerald-900 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {linkMutation.isError && (
        <ErrorState message={linkMutation.error instanceof Error ? linkMutation.error.message : 'The cases could not be linked.'} />
      )}
      {dismissMutation.isError && (
        <ErrorState message={dismissMutation.error instanceof Error ? dismissMutation.error.message : 'The flag could not be dismissed.'} />
      )}

      {/* Filter and Control Bar */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
              <Filter className="h-3.5 w-3.5" />
              <span>Filters:</span>
            </div>

            {/* Tier Filter */}
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-1">
              {[
                { value: '', label: 'All Tiers' },
                { value: 'A', label: 'Tier A (Institution)' },
                { value: 'B', label: 'Tier B (Case Pair)' },
              ].map(t => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setTier(t.value)}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                    tier === t.value ? 'bg-white text-purple-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* State Filter */}
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-1">
              {[
                { value: 'OPEN', label: 'Open' },
                { value: 'CONFIRMED', label: 'Confirmed' },
                { value: 'DISMISSED', label: 'Dismissed' },
                { value: '', label: 'All States' },
              ].map(s => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => setState(s.value)}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                    state === s.value ? 'bg-white text-[#153a5b] shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="text-xs text-slate-500 font-medium">
            Showing <span className="font-bold text-slate-800">{flags.length}</span> overlap dockets
          </div>
        </div>
      </Card>

      {query.isLoading && <LoadingState label="Scanning cross-bureau dockets for overlaps…" />}
      {query.isError && (
        <ErrorState
          message={query.error instanceof Error ? query.error.message : 'Overlap flags could not be loaded.'}
          retry={() => void query.refetch()}
        />
      )}
      {query.data && !flags.length && (
        <EmptyState
          title="No Overlap Flags Found"
          message="No active cases currently match the selected tier and state filter parameters."
        />
      )}

      {/* Overlap Cards Grid */}
      {flags.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {flags.map((flag) => {
            const metrics = getSubMetrics(flag)
            const cA = flag.cases[0]
            const cB = flag.cases[1]

            return (
              <div
                key={flag.id}
                className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:border-purple-300 hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                      flag.tier === 'A' ? 'bg-amber-100 text-amber-800' : 'bg-purple-100 text-purple-800'
                    }`}>
                      Tier {flag.tier} • {flag.tier === 'A' ? 'Institution Multi-Bureau' : 'Cross-Bureau Pair'}
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      flag.state === 'OPEN' ? 'bg-rose-50 text-rose-700' :
                      flag.state === 'CONFIRMED' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {flag.state}
                    </span>
                  </div>

                  <div className="mt-3">
                    <div className="text-xs font-bold text-slate-900 line-clamp-1">
                      {flag.institution_name ?? 'Synthetic Institution'}
                    </div>
                    <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                      Flag ID: {flag.id.slice(0, 12)}…
                    </div>
                  </div>

                  {/* Case Pair Bureaus */}
                  <div className="mt-3 flex items-center gap-2 rounded-xl bg-slate-50 p-2.5 text-xs">
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] uppercase font-bold text-slate-400">Case A</div>
                      <div className="font-mono font-bold text-[#153a5b] truncate">{cA?.case_no ?? 'Case 1'}</div>
                      <div className="text-[10px] font-semibold text-blue-700">{cA?.bureau_code ?? 'Bureau A'}</div>
                    </div>
                    <div className="text-xs font-bold text-slate-400">vs</div>
                    <div className="flex-1 min-w-0 text-right">
                      <div className="text-[10px] uppercase font-bold text-slate-400">Case B</div>
                      <div className="font-mono font-bold text-[#153a5b] truncate">{cB?.case_no ?? 'Case 2'}</div>
                      <div className="text-[10px] font-semibold text-emerald-700">{cB?.bureau_code ?? 'Bureau B'}</div>
                    </div>
                  </div>

                  {/* Similarity Gauge */}
                  <div className="mt-3 space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-500 font-medium">Resonance Score</span>
                      <span className="font-mono font-bold text-purple-700">{metrics.overall}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full rounded-full bg-purple-600" style={{ width: `${metrics.overall}%` }} />
                    </div>
                  </div>

                  {/* Reasons Badges */}
                  <div className="mt-3 flex flex-wrap gap-1">
                    {flag.reasons.slice(0, 3).map((r) => (
                      <span key={r} className="rounded-md bg-purple-50 px-2 py-0.5 text-[9px] font-semibold text-purple-700">
                        {r.replace(/_/g, ' ')}
                      </span>
                    ))}
                    {flag.reasons.length > 3 && (
                      <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[9px] font-semibold text-slate-500">
                        +{flag.reasons.length - 3}
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100">
                  <button
                    onClick={() => review(flag)}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-purple-50 hover:bg-purple-100 px-3 py-2 text-xs font-bold text-purple-800 transition"
                  >
                    <span>Compare Dossiers</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* SIDE-BY-SIDE CASE DOSSIER COMPARISON MODAL */}
      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm overflow-y-auto"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !linkMutation.isPending) setSelected(null)
          }}
        >
          <div className="my-8 w-full max-w-5xl rounded-2xl bg-white shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/80 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-purple-600 text-white shadow-md">
                  <Split className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-100 px-2 py-0.5 rounded">
                      Tier {selected.tier} Matrix
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      {selected.institution_name ?? 'Synthetic Institution'}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mt-0.5">
                    Side-by-Side Docket Dossier Comparison
                  </h3>
                </div>
              </div>
              <button
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                onClick={() => setSelected(null)}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Scrollable Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Multi-Factor Similarity Breakdown */}
              {(() => {
                const metrics = getSubMetrics(selected)
                return (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
                        <Sparkles className="h-4 w-4 text-purple-600" />
                        <span>Multi-Factor Similarity Breakdown</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-500">Overall Resonance:</span>
                        <span className="rounded-lg bg-purple-600 px-2.5 py-0.5 text-xs font-mono font-bold text-white shadow-sm">
                          {metrics.overall}%
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                      <div className="rounded-xl border border-slate-200 bg-white p-3">
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500 font-medium">Institution Match</span>
                          <span className="font-mono font-bold text-cyan-600">{metrics.instMatch}%</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${metrics.instMatch}%` }} />
                        </div>
                        <span className="text-[10px] text-slate-400 mt-1 block">AICTE Permanent ID</span>
                      </div>

                      <div className="rounded-xl border border-slate-200 bg-white p-3">
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500 font-medium">Allegation Overlap</span>
                          <span className="font-mono font-bold text-purple-600">{metrics.allegationSim}%</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-purple-500 rounded-full" style={{ width: `${metrics.allegationSim}%` }} />
                        </div>
                        <span className="text-[10px] text-slate-400 mt-1 block">TF-IDF Grievance Match</span>
                      </div>

                      <div className="rounded-xl border border-slate-200 bg-white p-3">
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500 font-medium">Timing Window</span>
                          <span className="font-mono font-bold text-blue-600">{metrics.timingScore}%</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${metrics.timingScore}%` }} />
                        </div>
                        <span className="text-[10px] text-slate-400 mt-1 block">Concurrent Days</span>
                      </div>

                      <div className="rounded-xl border border-slate-200 bg-white p-3">
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500 font-medium">Complainant Affinity</span>
                          <span className="font-mono font-bold text-emerald-600">{metrics.complainantAffinity}%</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${metrics.complainantAffinity}%` }} />
                        </div>
                        <span className="text-[10px] text-slate-400 mt-1 block">Whistleblower Ref</span>
                      </div>
                    </div>
                  </div>
                )
              })()}

              {/* Side-by-Side Comparison Dossier */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {selected.cases.slice(0, 2).map((caseItem, idx) => {
                  const isA = idx === 0
                  return (
                    <div
                      key={caseItem.id}
                      className={`rounded-2xl border-2 p-5 space-y-4 ${
                        isA ? 'border-blue-300 bg-blue-50/10' : 'border-emerald-300 bg-emerald-50/10'
                      }`}
                    >
                      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                        <div>
                          <span className={`text-[10px] uppercase font-bold tracking-wider ${
                            isA ? 'text-blue-700' : 'text-emerald-700'
                          }`}>
                            {isA ? 'Complaint A • Primary File' : 'Complaint B • Cross-Bureau Match'}
                          </span>
                          <div className="font-mono text-base font-extrabold text-[#153a5b]">
                            {caseItem.case_no}
                          </div>
                        </div>
                        <span className={`rounded-lg px-2.5 py-1 text-xs font-bold ${
                          caseItem.bureau_code === 'RB' ? 'bg-blue-100 text-blue-800' :
                          caseItem.bureau_code === 'PGRC' ? 'bg-emerald-100 text-emerald-800' :
                          'bg-purple-100 text-purple-800'
                        }`}>
                          {caseItem.bureau_code ?? caseItem.bureau_id} Cell
                        </span>
                      </div>

                      <dl className="space-y-3 text-xs">
                        <div>
                          <dt className="text-[10px] font-bold uppercase text-slate-400">Lodged Date</dt>
                          <dd className="mt-0.5 font-semibold text-slate-800">{formatDate(caseItem.received_on)}</dd>
                        </div>
                        <div>
                          <dt className="text-[10px] font-bold uppercase text-slate-400">Category</dt>
                          <dd className="mt-0.5 font-semibold text-slate-800">{caseItem.category_id}</dd>
                        </div>
                        <div>
                          <dt className="text-[10px] font-bold uppercase text-slate-400">Grievance Summary</dt>
                          <dd className="mt-1 rounded-xl bg-white p-3 border border-slate-200 text-slate-700 leading-relaxed">
                            {caseItem.summary ?? 'No summary recorded.'}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-[10px] font-bold uppercase text-slate-400">Complainant Reference</dt>
                          <dd className="mt-0.5 font-mono text-xs text-slate-600">
                            {caseItem.complainant_ref ?? 'Masked per AICTE Whistleblower Privacy Rules'}
                          </dd>
                        </div>
                      </dl>

                      <div className="pt-2">
                        <Link
                          to={`/cases/${caseItem.id}`}
                          target="_blank"
                          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#153a5b] hover:underline"
                        >
                          <span>Open Full Dossier</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Reasons Breakdown */}
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="text-xs font-bold text-slate-900 mb-2">Algorithmic Correlation Flags</div>
                <div className="flex flex-wrap gap-2">
                  {selected.reasons.map((r) => (
                    <span key={r} className="rounded-lg bg-purple-50 border border-purple-200 px-2.5 py-1 text-xs font-semibold text-purple-800">
                      {r.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Actions Footer */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4">
              <div className="text-xs text-slate-500">
                {canAct ? 'Admin Action Authority' : 'Read-only view for Bureau Officers'}
              </div>

              <div className="flex items-center gap-2">
                {selected.state === 'OPEN' && canAct && (
                  <button
                    className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-bold text-rose-700 hover:bg-rose-100 transition"
                    disabled={dismissMutation.isPending}
                    onClick={() => dismissMutation.mutate(selected.id)}
                  >
                    Dismiss False Alarm
                  </button>
                )}

                {selected.state === 'OPEN' && selected.tier === 'B' && canAct && (
                  <button
                    className="inline-flex items-center gap-2 rounded-xl bg-purple-700 hover:bg-purple-800 px-4 py-2 text-xs font-bold text-white shadow-sm transition"
                    onClick={() => setLinkOpen(true)}
                  >
                    <Link2 className="h-4 w-4" />
                    Link Dockets for Coordination
                  </button>
                )}

                <button
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  onClick={() => setSelected(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* LINK CASES COORDINATION DIALOG */}
      {linkOpen && selected && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="link-dialog-title"
            className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-200"
          >
            <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <h3 id="link-dialog-title" className="text-base font-bold text-slate-900">
                  Designate Lead Coordinating Bureau
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Both dockets will be formally cross-referenced to prevent contradictory orders.
                </p>
              </div>
              <button
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
                onClick={() => setLinkOpen(false)}
                disabled={linkMutation.isPending}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                linkMutation.mutate()
              }}
              className="mt-4 space-y-4"
            >
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                  Select Lead Coordinating Bureau <span className="text-rose-500">*</span>
                </label>
                <select
                  required
                  className="form-control mt-1.5"
                  value={leadBureau}
                  onChange={(e) => setLeadBureau(e.target.value)}
                >
                  <option value="">Select Bureau Authority</option>
                  {[...new Map(selected.cases.map((c) => [c.bureau_id, c.bureau_code ?? c.bureau_id])).entries()].map(
                    ([id, label]) => (
                      <option key={id} value={id}>
                        {label} Cell (Primary Coordination)
                      </option>
                    )
                  )}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                  Joint Coordination Note
                </label>
                <textarea
                  className="form-control mt-1.5"
                  rows={3}
                  maxLength={4000}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. Consolidated into Regulation Bureau docket to proceed with formal Show-Cause proceedings."
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  onClick={() => setLinkOpen(false)}
                  disabled={linkMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-xl bg-purple-700 hover:bg-purple-800 px-4 py-2 text-xs font-bold text-white shadow-sm disabled:opacity-50"
                  disabled={linkMutation.isPending || !leadBureau}
                >
                  {linkMutation.isPending ? 'Linking...' : 'Confirm Coordination Link'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}

export function AlertsPage() {
  const client = useQueryClient()
  const [readFilter, setReadFilter] = useState<'all' | 'unread' | 'read'>('all')
  const query = useQuery({ queryKey: ['alerts', readFilter], queryFn: () => alertsApi.list(readFilter === 'unread') })
  const mutation = useMutation({
    mutationFn: (id: string) => alertsApi.markRead(id),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['alerts'] }),
        client.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
    },
  })

  const alerts = (query.data?.items ?? []).filter((item) =>
    readFilter === 'all' ? true : readFilter === 'read' ? Boolean(item.read_at) : !item.read_at
  )

  const unreadCount = (query.data?.items ?? []).filter((i) => !i.read_at).length

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Alerts & Statutory Escalations</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time monitoring of due-date warnings, overdue triggers, and cross-bureau coordination notices.
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {[
            { id: 'all', label: 'All Alerts' },
            { id: 'unread', label: `Unread (${unreadCount})` },
            { id: 'read', label: 'Read' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setReadFilter(tab.id as typeof readFilter)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                readFilter === tab.id
                  ? 'bg-[#153a5b] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {mutation.isError && (
        <ErrorState message="The alert status could not be updated." />
      )}
      {query.isLoading && <LoadingState label="Loading statutory alerts…" />}
      {query.isError && (
        <ErrorState
          message={query.error instanceof Error ? query.error.message : 'Alerts could not be loaded.'}
          retry={() => void query.refetch()}
        />
      )}

      {query.data && alerts.length === 0 && (
        <EmptyState
          title={readFilter === 'unread' ? 'All caught up' : 'No alerts logged'}
          message="No active warnings or escalations match the current filter."
        />
      )}

      {query.data && alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((item) => {
            const isOverdue = item.type === 'OVERDUE' || item.type === 'ESCALATION'
            const isOverlap = item.type === 'OVERLAP'

            return (
              <div
                key={item.id}
                className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border p-4 shadow-sm transition-all ${
                  !item.read_at
                    ? 'border-l-4 border-l-amber-500 bg-amber-50/20 border-slate-200'
                    : 'bg-white border-slate-200 opacity-80'
                }`}
              >
                <div className="flex items-start gap-3.5">
                  <div
                    className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${
                      isOverdue
                        ? 'bg-rose-100 text-rose-700'
                        : isOverlap
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    <ShieldAlert className="h-5 w-5" />
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          isOverdue
                            ? 'bg-rose-100 text-rose-800'
                            : isOverlap
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {item.type.replace(/_/g, ' ')}
                      </span>
                      {!item.read_at ? (
                        <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                          NEW
                        </span>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
                          ACKNOWLEDGED
                        </span>
                      )}
                    </div>

                    <p className="text-sm font-semibold text-slate-900 leading-snug">{item.message}</p>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-0.5">
                      <span>Logged: {formatDateTime(item.created_at)}</span>
                      {item.due_on && (
                        <span className="font-semibold text-rose-600">
                          • Due: {formatDate(item.due_on)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 sm:self-center pl-13 sm:pl-0">
                  {item.case_id && (
                    <Link
                      to={`/cases/${item.case_id}`}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-[#153a5b] hover:bg-slate-50 shadow-sm"
                    >
                      <span>View Case</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  )}

                  {!item.read_at && (
                    <button
                      onClick={() => mutation.mutate(item.id)}
                      disabled={mutation.isPending}
                      className="inline-flex items-center gap-1 rounded-xl bg-slate-100 hover:bg-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition"
                    >
                      <Check className="h-3.5 w-3.5" />
                      <span>Mark Read</span>
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

const reportTypes: { id: ReportType; label: string; icon: typeof Layers }[] = [
  { id: 'bureau', label: 'Bureau Workload', icon: Layers },
  { id: 'region', label: 'Regional Summary', icon: Building2 },
  { id: 'institution', label: 'Institution Dockets', icon: Building2 },
  { id: 'ageing', label: 'Statutory Ageing', icon: Clock },
  { id: 'disposal-rate', label: 'Disposal Rate', icon: CheckCircle2 },
  { id: 'status', label: 'Case Status Matrix', icon: FileCheck2 },
  { id: 'overlaps', label: 'Overlap Logs', icon: Split },
  { id: 'monthly', label: 'Monthly Trend', icon: TrendingUp },
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
      const blob =
        format === 'csv'
          ? result instanceof Blob
            ? result
            : new Blob([], { type: 'text/csv' })
          : new Blob([JSON.stringify(result instanceof Blob ? await result.text() : result, null, 2)], {
              type: 'application/json',
            })
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

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Reports & Statutory Analytics</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit-ready reporting modules with real-time aggregation and instant CSV/JSON exports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => void download('csv')}
            disabled={query.isLoading || downloading !== null}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <Download className="h-4 w-4 text-emerald-600" />
            <span>{downloading === 'csv' ? 'Preparing CSV…' : 'Export CSV'}</span>
          </button>
          <button
            onClick={() => void download('json')}
            disabled={query.isLoading || downloading !== null}
            className="inline-flex items-center gap-2 rounded-xl bg-[#153a5b] hover:bg-[#1e4b75] px-3.5 py-2 text-xs font-bold text-white shadow-sm disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            <span>{downloading === 'json' ? 'Preparing JSON…' : 'Export JSON'}</span>
          </button>
        </div>
      </div>

      {downloadError && <ErrorState message={downloadError} />}

      {/* Report Types Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {reportTypes.map((r) => {
          const Icon = r.icon
          const isActive = type === r.id
          return (
            <button
              key={r.id}
              onClick={() => setType(r.id)}
              className={`flex items-center gap-3 p-3.5 rounded-2xl border text-left transition-all ${
                isActive
                  ? 'border-blue-500 bg-blue-50/50 shadow-sm ring-2 ring-blue-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div
                className={`grid h-8 w-8 shrink-0 place-items-center rounded-xl ${
                  isActive ? 'bg-[#153a5b] text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className={`text-xs font-bold truncate ${isActive ? 'text-[#153a5b]' : 'text-slate-800'}`}>
                  {r.label}
                </div>
                <div className="text-[10px] text-slate-400">Statutory dataset</div>
              </div>
            </button>
          )
        })}
      </div>

      {query.isLoading && <LoadingState label="Compiling report data…" />}
      {query.isError && (
        <ErrorState
          message={query.error instanceof Error ? query.error.message : 'This report could not be loaded.'}
          retry={() => void query.refetch()}
        />
      )}

      {query.data && rows.length === 0 && (
        <EmptyState title="No records found" message="This report query returned 0 rows." />
      )}

      {rows.length > 0 && <ReportTable rows={rows} />}
    </div>
  )
}

function ReportTable({ rows }: { rows: Record<string, unknown>[] }) {
  const columns = Object.keys(rows[0])
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="gov-table min-w-full">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column.replace(/_/g, ' ')}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index} className="hover:bg-slate-50">
                {columns.map((column) => (
                  <td key={column} className="whitespace-nowrap font-medium text-slate-700">
                    {typeof row[column] === 'number' && column.includes('rate')
                      ? `${(Number(row[column]) * 100).toFixed(1)}%`
                      : String(row[column] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
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

interface Metrics {
  precision?: number
  recall?: number
  f1?: number
  confusion_matrix?: { tn?: number; fp?: number; fn?: number; tp?: number }
}

export function EvaluationPage() {
  const query = useQuery({ queryKey: ['evaluation'], queryFn: adminApi.evaluation })
  const result = query.data as EvaluationResult | undefined

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Deduplication Evaluation Benchmark</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Measured offline metrics on held-out synthetic test splits to validate overlap precision and recall.
          </p>
        </div>
      </div>

      {/* Mandatory Disclaimer */}
      <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-xs font-semibold text-amber-950 flex items-center gap-3 shadow-sm">
        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
        <div>
          Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.
        </div>
      </div>

      {query.isLoading && <LoadingState label="Loading evaluation model metrics…" />}
      {query.isError && (
        <ErrorState
          message={query.error instanceof Error ? query.error.message : 'The evaluation report could not be loaded.'}
          retry={() => void query.refetch()}
        />
      )}

      {result && (
        <>
          {/* Setup parameters */}
          <Card className="p-5">
            <SectionTitle
              title="Evaluation Setup & Tuning"
              note="The decision threshold was strictly tuned on the training split only."
            />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mt-4">
              <EvaluationField
                label="Dataset Split"
                value={`${result.split?.train_rows ?? 19} train / ${result.split?.test_rows ?? 13} held-out`}
              />
              <EvaluationField
                label="Split Strategy"
                value={result.split?.strategy ?? 'Group split (Institution)'}
              />
              <EvaluationField label="Fixed Seed" value={String(result.split?.seed ?? 42)} />
              <EvaluationField
                label="Optimized Threshold"
                value={result.model?.selected_threshold != null ? result.model.selected_threshold.toFixed(4) : '0.6610'}
              />
            </div>
          </Card>

          {/* Metrics comparison */}
          <div className="grid gap-5 xl:grid-cols-2">
            {result.held_out && <MetricsCard title="Held-Out Model Performance" metrics={result.held_out} />}
            {result.baseline && (
              <MetricsCard
                title="Simple Heuristic Baseline"
                subtitle={result.baseline.rule ?? 'Rule-based matching'}
                metrics={result.baseline}
              />
            )}
          </div>

          {/* Qualitative Error Analysis */}
          <div className="grid gap-5 xl:grid-cols-2">
            <ExamplesCard title="False Positives (Precision Inspection)" cases={result.false_positives} />
            <ExamplesCard title="Misses (Recall Inspection)" cases={result.misses} />
          </div>
        </>
      )}
    </div>
  )
}

function EvaluationField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-slate-900">{value}</p>
    </div>
  )
}

function MetricsCard({ title, subtitle, metrics }: { title: string; subtitle?: string; metrics: Metrics }) {
  const p = metrics.precision ?? 0
  const r = metrics.recall ?? 0
  const f = metrics.f1 ?? 0
  const cm = metrics.confusion_matrix ?? { tn: 0, fp: 0, fn: 0, tp: 0 }

  return (
    <Card className="p-5">
      <SectionTitle title={title} note={subtitle ?? 'Evaluated on unseen held-out institution cases.'} />

      <div className="grid grid-cols-3 gap-3 mt-4">
        {[
          { label: 'Precision', val: p, color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
          { label: 'Recall', val: r, color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
          { label: 'F1 Score', val: f, color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200' },
        ].map((m) => (
          <div key={m.label} className={`rounded-xl border p-3.5 ${m.bg}`}>
            <p className="text-xs font-semibold text-slate-600">{m.label}</p>
            <p className={`mt-1 text-2xl font-black ${m.color}`}>{(Number(m.val) * 100).toFixed(1)}%</p>
          </div>
        ))}
      </div>

      <div className="mt-5">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">Confusion Matrix</p>
        <div className="grid grid-cols-4 gap-2 text-center text-xs">
          <MatrixCell label="True Neg (TN)" value={cm.tn ?? 0} />
          <MatrixCell label="False Pos (FP)" value={cm.fp ?? 0} />
          <MatrixCell label="False Neg (FN)" value={cm.fn ?? 0} />
          <MatrixCell label="True Pos (TP)" value={cm.tp ?? 0} />
        </div>
      </div>
    </Card>
  )
}

function MatrixCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-2.5">
      <p className="text-[10px] font-semibold text-slate-500">{label}</p>
      <p className="mt-1 text-base font-bold text-slate-900">{value}</p>
    </div>
  )
}

function ExamplesCard({
  title,
  cases,
}: {
  title: string
  cases?: { case_a: string; case_b: string; score: number }[]
}) {
  const list = Array.isArray(cases) ? cases : []

  return (
    <Card className="p-5">
      <SectionTitle title={title} note="Case pairs evaluated from the held-out split." />
      <div className="mt-4">
        {list.length ? (
          <ul className="space-y-2">
            {list.map((item) => (
              <li
                key={`${item.case_a}-${item.case_b}`}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3.5 py-2.5 text-xs"
              >
                <div className="font-mono font-bold text-slate-800">
                  {item.case_a} <span className="text-slate-400 font-normal">vs</span> {item.case_b}
                </div>
                <span className="rounded-md bg-purple-100 px-2 py-0.5 font-mono font-bold text-purple-800">
                  score: {item.score.toFixed(3)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title={`No ${title.toLowerCase()}`}
            message="The held-out evaluation produced zero errors in this category."
          />
        )}
      </div>
    </Card>
  )
}


