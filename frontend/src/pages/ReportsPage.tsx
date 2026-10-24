import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { errorMessage } from '../api/client'
import { downloadReport, getReport } from '../api/reports'
import { USE_MOCKS } from '../api/config'
import AsyncBoundary from '../components/AsyncBoundary'
import ReportChart from '../components/report/ReportChart'
import ReportTableView from '../components/report/ReportTableView'
import { EmptyState } from '../components/states'
import { STATUSES, STATUS_LABEL } from '../lib/constants'
import type { CaseStatus } from '../lib/constants'
import { fmtNum } from '../lib/format'
import { BUREAUS, CATEGORIES, REGIONS } from '../lib/lookups'
import { REPORT_LABEL, REPORT_TYPES, parseReportFilters, toSearchParams } from '../lib/reports'
import type { ReportFilters, ReportFormat, ReportType } from '../lib/reports'
import { numericColumns } from '../lib/reportTable'
import type { ReportTable } from '../lib/reportTable'

const INPUT = 'rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800'
const LABEL = 'flex flex-col gap-1 text-xs font-medium text-slate-600'

const FORMATS: Array<[ReportFormat, string]> = [
  ['csv', 'CSV'],
  ['json', 'JSON'],
  ['pdf', 'PDF'],
]

function Preview({ table, title }: { table: ReportTable; title: string }) {
  const metrics = numericColumns(table).filter((i) => i > 0)
  const [metric, setMetric] = useState(-1)
  const current = metrics.includes(metric) ? metric : (metrics[0] ?? -1)

  if (table.rows.length === 0) return <EmptyState text="No data for these filters." />

  return (
    <div>
      {current >= 0 && (
        <div className="border-b border-slate-100 px-4 py-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
            {metrics.length > 1 && (
              <label className="flex items-center gap-1 text-xs text-slate-600">
                Chart column
                <select className={INPUT} value={current} onChange={(e) => setMetric(Number(e.target.value))}>
                  {metrics.map((i) => (
                    <option key={i} value={i}>
                      {table.columns[i]}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <ReportChart table={table} metric={current} />
        </div>
      )}
      <ReportTableView table={table} />
    </div>
  )
}

export default function ReportsPage() {
  const [params, setParams] = useSearchParams()
  const filters = useMemo(() => parseReportFilters(params), [params])

  const setFilters = useCallback(
    (patch: Partial<ReportFilters>) => setParams(toSearchParams({ ...filters, ...patch })),
    [filters, setParams],
  )

  const query = useQuery({
    queryKey: ['report', filters],
    queryFn: () => getReport(filters),
    placeholderData: keepPreviousData,
  })

  const [busy, setBusy] = useState<ReportFormat | null>(null)
  const [dlError, setDlError] = useState<string | null>(null)

  async function onDownload(format: ReportFormat) {
    setBusy(format)
    setDlError(null)
    try {
      await downloadReport(filters, format)
    } catch (e) {
      setDlError(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const badRange = filters.from_date !== '' && filters.to_date !== '' && filters.from_date > filters.to_date
  const hasFilters =
    filters.from_date !== '' ||
    filters.to_date !== '' ||
    filters.bureau_id !== undefined ||
    filters.region_id !== undefined ||
    filters.category_id !== undefined ||
    filters.status !== ''

  const num = (v: string) => (v ? Number(v) : undefined)

  return (
    <div className="mx-auto max-w-[1400px] space-y-3">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold text-slate-900">Reports</h1>
        {query.data && <span className="text-xs text-slate-500">{fmtNum(query.data.rows.length)} rows</span>}
      </div>

      <section className="space-y-3 rounded-md border border-slate-200 bg-white px-4 py-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className={LABEL}>
            Report type
            <select
              className={INPUT}
              value={filters.type}
              onChange={(e) => setFilters({ type: e.target.value as ReportType })}
            >
              {REPORT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {REPORT_LABEL[t]}
                </option>
              ))}
            </select>
          </label>

          <label className={LABEL}>
            From (received)
            <input type="date" className={INPUT} value={filters.from_date} onChange={(e) => setFilters({ from_date: e.target.value })} />
          </label>
          <label className={LABEL}>
            To (received)
            <input type="date" className={INPUT} value={filters.to_date} onChange={(e) => setFilters({ to_date: e.target.value })} />
          </label>

          <label className={LABEL}>
            Bureau
            <select className={INPUT} value={filters.bureau_id ?? ''} onChange={(e) => setFilters({ bureau_id: num(e.target.value) })}>
              <option value="">All</option>
              {BUREAUS.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.label}
                </option>
              ))}
            </select>
          </label>
          <label className={LABEL}>
            Region
            <select className={INPUT} value={filters.region_id ?? ''} onChange={(e) => setFilters({ region_id: num(e.target.value) })}>
              <option value="">All</option>
              {REGIONS.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className={LABEL}>
            Category
            <select className={INPUT} value={filters.category_id ?? ''} onChange={(e) => setFilters({ category_id: num(e.target.value) })}>
              <option value="">All</option>
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className={LABEL}>
            Status
            <select
              className={INPUT}
              value={filters.status}
              onChange={(e) => setFilters({ status: e.target.value as '' | CaseStatus })}
            >
              <option value="">All</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
          </label>

          {hasFilters && (
            <button
              type="button"
              onClick={() => setFilters({ from_date: '', to_date: '', bureau_id: undefined, region_id: undefined, category_id: undefined, status: '' })}
              className="pb-1.5 text-sm text-teal hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>

        {badRange && (
          <p role="alert" className="text-sm text-red-700">
            The From date is after the To date.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
          <span className="text-sm text-slate-600">Download:</span>
          {FORMATS.map(([fmt, label]) => {
            const unavailable = fmt === 'pdf' && USE_MOCKS
            return (
              <button
                key={fmt}
                type="button"
                onClick={() => void onDownload(fmt)}
                disabled={busy !== null || unavailable}
                title={unavailable ? 'PDF is generated by the backend (not available with mock data)' : undefined}
                className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                {busy === fmt ? 'Preparing…' : label}
              </button>
            )
          })}
          {dlError && (
            <span role="alert" className="text-sm text-red-700">
              {dlError}
            </span>
          )}
        </div>
      </section>

      <section className="rounded-md border border-slate-200 bg-white" aria-busy={query.isFetching}>
        <h2 className="border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800">
          {REPORT_LABEL[filters.type]} report
        </h2>
        <AsyncBoundary query={query} height={360}>
          {(table) => (
            <div className={query.isPlaceholderData ? 'opacity-60 transition-opacity' : ''}>
              <Preview key={filters.type} table={table} title={REPORT_LABEL[filters.type]} />
            </div>
          )}
        </AsyncBoundary>
      </section>

      <p className="text-xs text-slate-500">
        Demo data is synthetic. SLA-based figures use placeholder SLA values, not official AICTE norms.
      </p>
    </div>
  )
}
