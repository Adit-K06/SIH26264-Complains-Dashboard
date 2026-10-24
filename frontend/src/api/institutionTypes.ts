/* ------------------------------------------------------------------
 * ASSUMED RESPONSE SHAPES for Institutions / Institution 360.
 * AGENTS.md lists the endpoints and the institutions table columns, but not the JSON bodies.
 * ASSUMPTIONS:
 *  - GET /institutions?q=&region_id=&page=&page_size=  -> Paged<Institution>
 *    (q matches name OR AICTE permanent id; total_cases/open_cases are optional extras)
 *  - GET /institutions/{id}                            -> Institution
 *  - GET /institutions/{id}/cases?page_size=200        -> Paged<CaseRow>
 *  - GET /overlaps?institution_id=&page_size=100       -> Paged<OverlapRow>, all states
 * If P1/P2 differ, change ONLY this file, src/api/institutions.ts and the mock.
 * ------------------------------------------------------------------ */

// Columns of the institutions table in AGENTS.md
export interface Institution {
  id: number
  aicte_permanent_id: string
  name: string
  address?: string | null
  district?: string | null
  state?: string | null
  region_id?: number | null
  region_name?: string | null
  type?: string | null
  status?: string | null
  total_cases?: number
  open_cases?: number
}
