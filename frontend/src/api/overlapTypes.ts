import type { CaseStatus, Priority } from '../lib/constants'
import type { OverlapFlag } from './types'

/* ------------------------------------------------------------------
 * ASSUMED RESPONSE SHAPES for the Overlap Center.
 * AGENTS.md lists /overlaps endpoints but not the JSON bodies, and GET /overlaps
 * query params are not specified either. ASSUMPTIONS:
 *  - GET /overlaps?state=&tier=&region_id=&min_score=&page=&page_size= -> Paged<OverlapRow>
 *  - each row embeds `cases` (Tier B: the 2 cases; Tier A: the open cases across bureaus)
 *  - POST /overlaps/{id}/link    body {lead_bureau_id, note}
 *  - POST /overlaps/{id}/dismiss body {note}
 * If P1/P2 differ, change ONLY this file, src/api/overlaps.ts and the mock.
 * ------------------------------------------------------------------ */

export interface OverlapCase {
  id: number
  case_no: string
  status: CaseStatus
  bureau_id?: number | null
  bureau_code?: string | null
  category_name?: string | null
  priority?: Priority | null
  received_on?: string | null
  assigned_officer_name?: string | null
  last_action_on?: string | null
  last_action_text?: string | null
  next_action_text?: string | null
  summary?: string | null
}

// OverlapFlag (types.ts): id, institution_id, institution_name, tier, score, reasons, state
export interface OverlapRow extends OverlapFlag {
  region_id?: number | null
  bureaus?: string[] // bureau codes involved
  cases?: OverlapCase[]
  lead_bureau_id?: number | null
  note?: string | null
  decided_by_name?: string | null
  decided_at?: string | null
}

export interface LinkBody {
  lead_bureau_id: number
  note?: string
}
