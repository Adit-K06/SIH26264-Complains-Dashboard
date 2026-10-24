import { useQuery } from '@tanstack/react-query'
import { getUnreadCount } from '../api/alerts'

/**
 * Unread alert count for the top-bar bell (undefined while loading / on error).
 * Query key starts with 'alerts', so marking an alert read on the Alerts page refreshes it.
 * Usage in the top bar:  const unread = useUnreadAlerts()
 */
export function useUnreadAlerts(): number | undefined {
  const q = useQuery({
    queryKey: ['alerts', 'unread-count'],
    queryFn: getUnreadCount,
    refetchInterval: 45_000,
  })
  return q.data
}
