import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { parseFilters, toSearchParams } from '../lib/caseFilters'
import type { CaseFilters, FilterPatch } from '../lib/caseFilters'

/** The URL is the single source of truth for Cases filters and pagination. */
export function useCaseFilters() {
  const [params, setParams] = useSearchParams()
  const filters = useMemo(() => parseFilters(params), [params])

  const setFilters = useCallback(
    (patch: FilterPatch) => {
      const next: CaseFilters = { ...filters, ...patch }
      if (patch.page === undefined) next.page = 1 // any filter change goes back to page 1
      setParams(toSearchParams(next))
    },
    [filters, setParams],
  )

  const clear = useCallback(() => setParams(new URLSearchParams()), [setParams])

  return { filters, setFilters, clear }
}
