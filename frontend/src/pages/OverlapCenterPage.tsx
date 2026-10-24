import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { errorMessage } from '../api/client'
import { dismissOverlap, getOverlaps, linkOverlap, scanOverlaps } from '../api/overlaps'
import AsyncBoundary from '../components/AsyncBoundary'
import DecisionDialog from '../components/overlap/DecisionDialog'
import OverlapDrawer from '../components/overlap/OverlapDrawer'
import OverlapTable from '../components/overlap/OverlapTable'
import Pagination from '../components/Pagination'
import { EmptyState } from '../components/states'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { OVERLAP_HEADING } from '../lib/constants'
import { fmtNum } from '../lib/format'
import { REGIONS } from '../lib/lookups'
import { OVERLAP_STATES, STATE_LABEL, parseOverlapFilters, toSearchParams } from '../lib/overlap'
import type { OverlapFilters } from '../lib/overlap'

const SELECT = 'rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800'
const SCORES = [0.6, 0.7, 0.8, 0.9]

interface DecideVars {
  id: number
  mode: 'link' | 'dismiss'
  lead_bureau_id?: number
  note?: string
}

export default function OverlapCenterPage() {
  const user = useCurrentUser()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const filters = useMemo(() => parseOverlapFilters(params), [params])

  const setFilters = useCallback(
    (patch: Partial<OverlapFilters>) => {
      const next: OverlapFilters = { ...filters, ...patch }
      if (patch.page === undefined) next.page = 1 // any filter change goes back to page 1
      setParams(toSearchParams(next))
    },
    [filters, setParams],
  )

  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [dialog, setDialog] = useState<'link' | 'dismiss' | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const query = useQuery({
    queryKey: ['overlaps', filters],
    queryFn: () => getOverlaps(filters),
    placeholderData: keepPreviousData,
    refetchInterval: 45_000,
  })

  const selected = query.data?.items.find((r) => r.id === selectedId) ?? null

  function refreshAll() {
    void qc.invalidateQueries({ queryKey: ['overlaps'] })
    void qc.invalidateQueries({ queryKey: ['dashboard'] })
    void qc.invalidateQueries({ queryKey: ['cases'] })
    void qc.invalidateQueries({ queryKey: ['case'] })
  }

  const decide = useMutation({
    mutationFn: (v: DecideVars) => {
      if (v.mode === 'dismiss') return dismissOverlap(v.id, v.note, user)
      if (v.lead_bureau_id === undefined) return Promise.reject(new Error('Select the lead bureau.'))
      return linkOverlap(v.id, { lead_bureau_id: v.lead_bureau_id, note: v.note }, user)
    },
    onSuccess: (_d, v) => {
      setDialog(null)
      setSelectedId(null)
      setNotice(v.mode === 'link' ? 'Cases linked and flag confirmed.' : 'Flag dismissed.')
      refreshAll()
    },
  })

  const scan = useMutation({
    mutationFn: scanOverlaps,
    onSuccess: () => {
      setNotice('Scan finished. The list has been refreshed.')
      refreshAll()
    },
  })

  const hasFilters = filters.tier !== '' || filters.region_id !== undefined || filters.min_score !== undefined

  return (
    <div className="mx-auto max-w-[1400px] space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-lg font-semibold text-slate-900">Overlap Center</h1>
        <div className="flex items-center gap-3">
          {query.data && (
            <span className="text-xs text-slate-500">{fmtNum(query.data.total)} flags</span>
          )}
          <button
            type="button"
            onClick={() => {
              setNotice(null)
              scan.mutate()
            }}
            disabled={scan.isPending}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {scan.isPending ? 'Scanning…' : 'Run scan'}
          </button>
        </div>
      </div>

      {notice && (
        <div
          role="status"
          className="flex items-center justify-between rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800"
        >
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}
      {scan.isError && (
        <p role="alert" className="text-sm text-red-700">
          {errorMessage(scan.error)}
        </p>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-white px-3 py-2">
        <div className="flex gap-1" role="group" aria-label="Flag state">
          {OVERLAP_STATES.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={filters.state === s}
              onClick={() => setFilters({ state: s })}
              className={`rounded border px-3 py-1 text-sm ${
                filters.state === s
                  ? 'border-slate-800 bg-slate-800 text-white'
                  : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              {STATE_LABEL[s]}
            </button>
          ))}
        </div>

        <label className="flex items-center gap-1 text-sm text-slate-600">
          Tier
          <select
            className={SELECT}
            value={filters.tier}
            onChange={(e) => setFilters({ tier: e.target.value as OverlapFilters['tier'] })}
          >
            <option value="">All</option>
            <option value="A">Tier A (rule)</option>
            <option value="B">Tier B (score)</option>
          </select>
        </label>

        <label className="flex items-center gap-1 text-sm text-slate-600">
          Region
          <select
            className={SELECT}
            value={filters.region_id ?? ''}
            onChange={(e) => setFilters({ region_id: e.target.value ? Number(e.target.value) : undefined })}
          >
            <option value="">All</option>
            {REGIONS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1 text-sm text-slate-600">
          Min score
          <select
            className={SELECT}
            value={filters.min_score ?? ''}
            onChange={(e) => setFilters({ min_score: e.target.value ? Number(e.target.value) : undefined })}
          >
            <option value="">Any</option>
            {SCORES.map((s) => (
              <option key={s} value={s}>
                {s.toFixed(2)}
              </option>
            ))}
          </select>
        </label>

        {hasFilters && (
          <button
            type="button"
            onClick={() => setFilters({ tier: '', region_id: undefined, min_score: undefined })}
            className="text-sm text-teal hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      <section className="rounded-md border border-slate-200 bg-white" aria-busy={query.isFetching}>
        <h2 className="border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800">
          {OVERLAP_HEADING}
        </h2>
        <AsyncBoundary query={query} height={360}>
          {(data) =>
            data.items.length === 0 ? (
              <EmptyState text="No overlap flags match these filters." />
            ) : (
              <div className={query.isPlaceholderData ? 'opacity-60 transition-opacity' : ''}>
                <OverlapTable
                  rows={data.items}
                  onReview={(r) => {
                    decide.reset()
                    setSelectedId(r.id)
                  }}
                />
                <Pagination
                  page={data.page}
                  pageSize={filters.page_size}
                  total={data.total}
                  onPage={(page) => setFilters({ page })}
                  onPageSize={(page_size) => setFilters({ page_size })}
                />
              </div>
            )
          }
        </AsyncBoundary>
      </section>

      {selected && (
        <OverlapDrawer
          row={selected}
          blocked={dialog !== null}
          onClose={() => setSelectedId(null)}
          onDecide={(mode) => {
            decide.reset()
            setNotice(null)
            setDialog(mode)
          }}
        />
      )}

      {selected && dialog && (
        <DecisionDialog
          mode={dialog}
          row={selected}
          busy={decide.isPending}
          error={decide.isError ? errorMessage(decide.error) : null}
          onSubmit={(input) => decide.mutate({ id: selected.id, mode: dialog, ...input })}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  )
}
