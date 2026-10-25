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

function getMockUser(): CurrentUser {
  try {
    const raw = localStorage.getItem('mock_user')
    if (raw) {
      const u = JSON.parse(raw) as { name?: string; role?: string }
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

/**
 * Returns the currently authenticated user.
 * In mock/demo mode: reads from localStorage (set during mock login).
 * In real API mode: fetches from GET /auth/me.
 */
export function useCurrentUser(): CurrentUser {
  // Always call useQuery (hooks must not be conditional) but disable it in mock mode
  const { data } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
    staleTime: 5 * 60 * 1000, // 5 min
    retry: false,
    enabled: !USE_MOCKS && !!localStorage.getItem('access_token'),
  })

  if (USE_MOCKS) {
    return getMockUser()
  }

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
