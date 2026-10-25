import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
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
 * Falls back to a safe mock if no token is stored (should not happen
 * since App.tsx guards the layout behind a login check).
 */
export function useCurrentUser(): CurrentUser {
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
