import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { USE_MOCKS } from '../api/config'
import type { CurrentUser } from '../lib/casePermissions'

interface MeResponse {
  id: number
  name: string
  email: string
  role: string
  bureau_id: number | null
  region_id: number | null
  active: boolean
}

async function fetchMe(): Promise<MeResponse> {
  const res = await api.get('/auth/me')
  return res.data
}

/**
 * Returns the currently authenticated user from GET /auth/me.
 * In mock mode, reads from the mock_user key set during mock login.
 * Falls back to a safe default if data is not yet loaded.
 */
export function useCurrentUser(): CurrentUser {
  // In mock mode, read the stored mock user — no API call needed
  if (USE_MOCKS) {
    try {
      const raw = localStorage.getItem('mock_user')
      if (raw) {
        const u = JSON.parse(raw)
        return {
          id: 1,
          name: u.name ?? 'Demo User',
          role: (u.role ?? 'SENIOR_MGMT') as CurrentUser['role'],
          bureau_id: null,
          region_id: null,
        }
      }
    } catch {
      // ignore parse errors
    }
    return { id: 1, name: 'Demo User', role: 'SENIOR_MGMT', bureau_id: null, region_id: null }
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const { data } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
    staleTime: 5 * 60 * 1000,   // 5 min
    retry: false,
    enabled: !!localStorage.getItem('access_token'),
  })

  if (!data) {
    return { id: 0, name: 'Loading…', role: 'BUREAU_OFFICER', bureau_id: null, region_id: null }
  }

  return {
    id: data.id,
    name: data.name,
    role: data.role as CurrentUser['role'],
    bureau_id: data.bureau_id,
    region_id: data.region_id,
  }
}
