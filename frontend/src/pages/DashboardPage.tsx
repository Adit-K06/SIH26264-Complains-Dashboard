import { Link } from 'react-router-dom'
import AsyncBoundary from '../components/AsyncBoundary'
import BeyondSlaTable from '../components/BeyondSlaTable'
import KpiTile from '../components/KpiTile'
import OverlapList from '../components/OverlapList'
import Panel from '../components/Panel'
import UpdatedIndicator from '../components/UpdatedIndicator'
import AgeingChart from '../components/charts/AgeingChart'
import TrendChart from '../components/charts/TrendChart'
import WorkloadChart from '../components/charts/WorkloadChart'
import { useDashboardData } from '../hooks/useDashboardData'
import { OVERLAP_HEADING, STATUS_COLOR } from '../lib/constants'
import type { DashboardSummary } from '../api/types'

// Every tile links to a filtered list. Query names follow AGENTS.md case filters.
function kpis(s: DashboardSummary) {
  return [
    { label: 'Total cases', value: s.total, to: '/cases', color: '#0f2a4a' },
    { label: 'Pending', value: s.by_status.PENDING ?? 0, to: '/cases?status=PENDING', color: STATUS_COLOR.PENDING },
    { label: 'Under process', value: s.by_status.UNDER_PROCESS ?? 0, to: '/cases?status=UNDER_PROCESS', color: STATUS_COLOR.UNDER_PROCESS },
    { label: 'Disposed', value: s.by_status.DISPOSED ?? 0, to: '/cases?status=DISPOSED', color: STATUS_COLOR.DISPOSED },
    { label: 'Transferred', value: s.by_status.TRANSFERRED ?? 0, to: '/cases?status=TRANSFERRED', color: STATUS_COLOR.TRANSFERRED },
    { label: 'Beyond SLA', value: s.beyond_sla, to: '/cases?beyond_sla=true', color: STATUS_COLOR.ESCALATED },
    { label: 'Open overlaps', value: s.open_overlaps, to: '/overlaps?state=OPEN', color: '#0e7c86' },
  ]
}

const viewAll = (to: string, text: string) => (
  <Link to={to} className="text-xs font-medium text-teal hover:underline">
    {text}
  </Link>
)

export default function DashboardPage() {
  const d = useDashboardData()

  return (
    <div className="mx-auto max-w-[1400px] space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-slate-900">Dashboard</h1>
        <UpdatedIndicator
          updatedAt={d.updatedAt}
          isFetching={d.isFetching}
          onRefresh={d.refreshAll}
        />
      </div>

      {/* KPI tiles */}
      <AsyncBoundary query={d.summary} height={72}>
        {(s) => (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            {kpis(s).map((k) => (
              <KpiTile key={k.label} {...k} />
            ))}
          </div>
        )}
      </AsyncBoundary>

      {/* Workload + overlaps */}
      <div className="grid gap-4 xl:grid-cols-3">
        <Panel
          className="xl:col-span-2"
          title="Bureau-wise workload"
          subtitle="Cases by bureau and status"
        >
          <AsyncBoundary
            query={d.workload}
            isEmpty={(w) => w.items.length === 0}
            emptyText="No workload data yet."
            height={280}
          >
            {(w) => <WorkloadChart rows={w.items} />}
          </AsyncBoundary>
        </Panel>

        <Panel
          title={OVERLAP_HEADING}
          action={viewAll('/overlaps?state=OPEN', 'View all')}
        >
          <AsyncBoundary
            query={d.overlaps}
            isEmpty={(o) => o.items.length === 0}
            emptyText="No open overlaps."
            height={280}
          >
            {(o) => <OverlapList flags={o.items} />}
          </AsyncBoundary>
        </Panel>
      </div>

      {/* Trend + ageing */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Monthly trend" subtitle="Received vs disposed">
          <AsyncBoundary
            query={d.summary}
            isEmpty={(s) => !s.monthly || s.monthly.length === 0}
            emptyText="Monthly trend is not provided by the API yet."
            height={240}
          >
            {(s) => <TrendChart points={s.monthly ?? []} />}
          </AsyncBoundary>
        </Panel>

        <Panel title="Ageing of open cases" subtitle="Days since receipt">
          <AsyncBoundary
            query={d.ageing}
            isEmpty={(a) => a.items.length === 0}
            emptyText="No ageing data yet."
            height={240}
          >
            {(a) => <AgeingChart buckets={a.items} />}
          </AsyncBoundary>
        </Panel>
      </div>

      {/* Beyond SLA */}
      <Panel
        title="Cases beyond SLA"
        subtitle="Open cases past expected disposal date"
        action={viewAll('/cases?beyond_sla=true', 'View all')}
      >
        <AsyncBoundary
          query={d.beyondSla}
          isEmpty={(c) => c.items.length === 0}
          emptyText="No cases are beyond SLA."
          height={200}
        >
          {(c) => <BeyondSlaTable rows={c.items} />}
        </AsyncBoundary>
      </Panel>
    </div>
  )
}
