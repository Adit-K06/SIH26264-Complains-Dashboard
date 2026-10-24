import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { errorMessage } from '../api/client'
import { getAlerts, markAlertRead } from '../api/alerts'
import AsyncBoundary from '../components/AsyncBoundary'
import AlertList from '../components/alert/AlertList'
import Pagination from '../components/Pagination'
import { EmptyState } from '../components/states'
import { ALERT_LABEL, ALERT_TYPES, parseAlertFilters, toSearchParams } from '../lib/alerts'
import type { AlertFilters } from '../lib/alerts'
import { fmtNum } from '../lib/format'

const chip = (active: boolean) =>
  `rounded border px-3 py-1 text-sm ${
    active
      ? 'border-slate-800 bg-slate-800 text-white'
      : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
  }`

export default function AlertsPage() {
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const filters = useMemo(() => parseAlertFilters(params), [params])

  const setFilters = useCallback(
    (patch: Partial<AlertFilters>) => {
      const next: AlertFilters = { ...filters, ...patch }
      if (patch.page === undefined) next.page = 1 // any filter change goes back to page 1
      setParams(toSearchParams(next))
    },
    [filters, setParams],
  )

  const query = useQuery({
    queryKey: ['alerts', filters],
    queryFn: () => getAlerts(filters),
    placeholderData: keepPreviousData,
    refetchInterval: 45_000,
  })

  // Callbacks live in the mutation options so they still run if the user has already
  // navigated away (clicking an alert opens its case and marks it read).
  const mark = useMutation({
    mutationFn: (id: number) => markAlertRead(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  return (
    <div className="mx-auto max-w-[1100px] space-y-3">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold text-slate-900">Alerts</h1>
        {query.data && (
          <span className="text-xs text-slate-500">
            {fmtNum(query.data.total)} {filters.unread ? 'unread' : 'alerts'}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-md border border-slate-200 bg-white px-3 py-2">
        <div className="flex gap-1" role="group" aria-label="Read state">
          <button type="button" aria-pressed={!filters.unread} onClick={() => setFilters({ unread: false })} className={chip(!filters.unread)}>
            All
          </button>
          <button type="button" aria-pressed={filters.unread} onClick={() => setFilters({ unread: true })} className={chip(filters.unread)}>
            Unread
          </button>
        </div>

        <div className="flex flex-wrap gap-1" role="group" aria-label="Alert type">
          <button type="button" aria-pressed={filters.type === ''} onClick={() => setFilters({ type: '' })} className={chip(filters.type === '')}>
            All types
          </button>
          {ALERT_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              aria-pressed={filters.type === t}
              onClick={() => setFilters({ type: t })}
              className={chip(filters.type === t)}
            >
              {ALERT_LABEL[t]}
            </button>
          ))}
        </div>
      </div>

      {mark.isError && (
        <p role="alert" className="text-sm text-red-700">
          Could not mark the alert as read: {errorMessage(mark.error)}
        </p>
      )}

      <section className="rounded-md border border-slate-200 bg-white" aria-busy={query.isFetching}>
        <AsyncBoundary query={query} height={360}>
          {(data) =>
            data.items.length === 0 ? (
              <EmptyState text={filters.unread ? 'No unread alerts.' : 'No alerts to show.'} />
            ) : (
              <div className={query.isPlaceholderData ? 'opacity-60 transition-opacity' : ''}>
                <AlertList
                  alerts={data.items}
                  pendingId={mark.isPending ? mark.variables : undefined}
                  onMarkRead={(id) => mark.mutate(id)}
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

      <p className="text-xs text-slate-500">
        Alert timings use placeholder SLA values, not official AICTE norms. Demo data is synthetic.
      </p>
    </div>
  )
}
