/* ------------------------------------------------------------------
 * ASSUMED LOOKUP IDs.
 * The contract has NO endpoint that lists bureaus, regions or categories,
 * but GET /cases filters by bureau_id / region_id / category_id.
 * The ids below assume the seed inserts rows in this order starting at 1.
 * ASK P2 (seed) or P1 for the real ids, or for a lookup endpoint,
 * then fix ONLY this file.
 * Names come from AGENTS.md (bureaus, regions) and the data-generator
 * prompt (categories).
 * ------------------------------------------------------------------ */
export interface Option {
  id: number
  label: string
}

export const BUREAUS: Option[] = ['RB', 'PGRC', 'APPROVAL', 'ACADEMIC', 'FINANCE'].map(
  (label, i) => ({ id: i + 1, label }),
)

export const REGIONS: Option[] = [
  'Central',
  'Eastern',
  'North-Eastern',
  'Northern',
  'Southern',
  'South-Western',
  'Western',
].map((label, i) => ({ id: i + 1, label }))

export const CATEGORIES: Option[] = [
  'Fee refund',
  'Faculty salary',
  'Infrastructure',
  'Affiliation / approval',
  'Ragging',
  'Admission irregularity',
  'Fake documents',
].map((label, i) => ({ id: i + 1, label }))
