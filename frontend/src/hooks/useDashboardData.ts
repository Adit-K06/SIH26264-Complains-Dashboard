import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAgeing,
  getBeyondSla,
  getOpenOverlaps,
  getSummary,
  getWorkload,
} from '../api/dashboard'

// "Real time" = polling. TanStack Query pauses interval refetches while the
// browser tab is in the background (refetchIntervalInBackground defaults to false).
export const REFRESH_MS = 45_000

const poll = { refetchInterval: REFRESH_MS }

export function useDashboardData() {
  const qc = useQueryClient()

  const summary = useQuery({ queryKey: ['dashboard', 'summary'], queryFn: getSummary, ...poll })
  const workload = useQuery({ queryKey: ['dashboard', 'workload'], queryFn: getWorkload, ...poll })
  const ageing = useQuery({ queryKey: ['dashboard', 'ageing'], queryFn: getAgeing, ...poll })
  const beyondSla = useQuery({ queryKey: ['dashboard', 'beyond-sla'], queryFn: getBeyondSla, ...poll })
  const overlaps = useQuery({ queryKey: ['dashboard', 'overlaps'], queryFn: getOpenOverlaps, ...poll })

  const all = [summary, workload, ageing, beyondSla, overlaps]
  const updatedAt = Math.max(0, ...all.map((q) => q.dataUpdatedAt))
  const isFetching = all.some((q) => q.isFetching)

  return {
    summary,
    workload,
    ageing,
    beyondSla,
    overlaps,
    updatedAt,
    isFetching,
    refreshAll: () => qc.invalidateQueries({ queryKey: ['dashboard'] }),
  }
}
