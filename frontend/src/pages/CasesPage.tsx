import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getCases } from '../api/cases'
import AsyncBoundary from '../components/AsyncBoundary'
import CaseFilterBar from '../components/CaseFilterBar'
import CasesTable from '../components/CasesTable'
import Pagination from '../components/Pagination'
import { EmptyState } from '../components/states'
import { useCaseFilters } from '../hooks/useCaseFilters'
import { fmtNum } from '../lib/format'

export default function CasesPage() {
  const { filters, setFilters, clear } = useCaseFilters()

  // The whole filter object is the query key: any change refetches, and
  // keepPreviousData keeps the old rows on screen (dimmed) so the table never flickers.
  const query = useQuery({
    queryKey: ['cases', filters],
    queryFn: () => getCases(filters),
    placeholderData: keepPreviousData,
  })

  return (
    <div className="mx-auto max-w-[1400px] space-y-3">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold text-slate-900">Cases</h1>
        {query.data && (
          <span className="text-xs text-slate-500">{fmtNum(query.data.total)} matching cases</span>
        )}
      </div>

      <CaseFilterBar filters={filters} setFilters={setFilters} clear={clear} />

      <section className="rounded-md border border-slate-200 bg-white" aria-busy={query.isFetching}>
        <AsyncBoundary query={query} height={360}>
          {(data) =>
            data.items.length === 0 ? (
              <div className="p-4">
                <EmptyState text="No cases match these filters." />
                <div className="text-center">
                  <button
                    type="button"
                    onClick={clear}
                    className="rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    Clear filters
                  </button>
                </div>
              </div>
            ) : (
              <div className={query.isPlaceholderData ? 'opacity-60 transition-opacity' : ''}>
                <CasesTable rows={data.items} />
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
