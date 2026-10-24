import type { AlertType } from '../lib/alerts'

/* ------------------------------------------------------------------
 * ASSUMED RESPONSE SHAPES for the Alerts page.
 * AGENTS.md gives the alerts table columns and the endpoints, but not the JSON bodies
 * or query params. ASSUMPTIONS:
 *  - GET /alerts?unread=true&type=&page=&page_size=  -> Paged<Alert>
 *    (the backend scopes alerts to the logged-in user's role/bureau)
 *  - POST /alerts/{id}/read                           -> any 2xx
 *  - case_no and institution_name are optional extras; the UI falls back to the ids
 * If P4's alerts.py differs, change ONLY this file, src/api/alerts.ts and the mock.
 * ------------------------------------------------------------------ */

// Columns of the alerts table in AGENTS.md
export interface Alert {
  id: number
  type: AlertType
  case_id?: number | null
  case_no?: string | null
  institution_id?: number | null
  institution_name?: string | null
  target_role?: string | null
  target_bureau_id?: number | null
  message: string
  due_on?: string | null // YYYY-MM-DD
  created_at: string // ISO datetime
  read_at?: string | null // null = unread
}
