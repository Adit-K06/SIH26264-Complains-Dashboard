import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getInstitutions } from '../api/institutions'
import AsyncBoundary from '../components/AsyncBoundary'
import InstitutionTable from '../components/institution/InstitutionTable'
import Pagination from '../components/Pagination'
import { EmptyState } from '../components/states'
import { fmtNum } from '../lib/format'
import { parseInstitutionFilters, toSearchParams } from '../lib/institution'
import type { InstitutionFilters } from '../lib/institution'
import { REGIONS } from '../lib/lookups'

const INPUT = 'rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800'

export default function InstitutionsPage() {
  const [params, setParams] = useSearchParams()
  const filters = useMemo(() => parseInstitutionFilters(params), [params])

  const setFilters = useCallback(
    (patch: Partial<InstitutionFilters>) => {
      const next: InstitutionFilters = { ...filters, ...patch }
      if (patch.page === undefined) next.page = 1 // any filter change goes back to page 1
      setParams(toSearchParams(next))
    },
    [filters, setParams],
  )

  // Search text is applied on submit (Enter or the Search button); keep it in sync with the URL.
  const [text, setText] = useState(filters.q)
  useEffect(() => {
    setText(filters.q)
  }, [filters.q])

  const query = useQuery({
    queryKey: ['institutions', filters],
    queryFn: () => getInstitutions(filters),
    placeholderData: keepPreviousData,
  })

  function onSearch(e: FormEvent) {
    e.preventDefault()
    setFilters({ q: text.trim() })
  }

  const hasFilters = filters.q !== '' || filters.region_id !== undefined

  return (
    <div className="mx-auto max-w-[1400px] space-y-3">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold text-slate-900">Institutions</h1>
        {query.data && <span className="text-xs text-slate-500">{fmtNum(query.data.total)} institutions</span>}
      </div>

      <form
        onSubmit={onSearch}
        className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-white px-3 py-2"
      >
        <label className="flex items-center gap-1 text-sm text-slate-600">
          <span className="sr-only">Search by institution name or AICTE permanent ID</span>
          <input
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Name or AICTE permanent ID"
            className={`${INPUT} w-72`}
          />
        </label>
        <button
          type="submit"
          className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          Search
        </button>

        <label className="flex items-center gap-1 text-sm text-slate-600">
          Region
          <select
            className={INPUT}
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

        {hasFilters && (
          <button
            type="button"
            onClick={() => setParams(new URLSearchParams())}
            className="text-sm text-teal hover:underline"
          >
            Clear filters
          </button>
        )}
      </form>

      <section className="rounded-md border border-slate-200 bg-white" aria-busy={query.isFetching}>
        <AsyncBoundary query={query} height={360}>
          {(data) =>
            data.items.length === 0 ? (
              <EmptyState text="No institutions match your search." />
            ) : (
              <div className={query.isPlaceholderData ? 'opacity-60 transition-opacity' : ''}>
                <InstitutionTable rows={data.items} />
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
    </div>
  )
}
