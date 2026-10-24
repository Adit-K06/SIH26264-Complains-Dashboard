import { useMemo } from 'react'
import { ROLES } from '../api/caseDetailTypes'
import type { Role } from '../api/caseDetailTypes'
import type { CurrentUser } from '../lib/casePermissions'

/**
 * TEMPORARY. There is no auth in the app yet, so this returns a mock user.
 * To test other roles, run in the browser console, then reload:
 *   localStorage.setItem('mock_role', 'SENIOR_MGMT')   // or REGIONAL_OFFICER / ADMIN / BUREAU_OFFICER
 *   localStorage.setItem('mock_bureau_id', '1')        // 1=RB 2=PGRC 3=APPROVAL 4=ACADEMIC 5=FINANCE
 *   localStorage.setItem('mock_region_id', '4')        // 1..7 as in lib/lookups.ts
 * When real auth (GET /auth/me) is wired, replace the body of this hook only.
 */
export function useCurrentUser(): CurrentUser {
  return useMemo(() => {
    const r = localStorage.getItem('mock_role') ?? ''
    const role: Role = (ROLES as readonly string[]).includes(r) ? (r as Role) : 'BUREAU_OFFICER'
    const num = (key: string, fallback: number) => {
      const n = Number(localStorage.getItem(key))
      return Number.isInteger(n) && n > 0 ? n : fallback
    }
    return {
      id: 1,
      name: 'Demo User (mock)',
      role,
      bureau_id: num('mock_bureau_id', 2),
      region_id: num('mock_region_id', 4),
    }
  }, [])
}
