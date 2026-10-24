/* ------------------------------------------------------------------
 * ASSUMED RESPONSE SHAPE for POST /import/cases-csv (multipart field "file", max 5 MB).
 * From the P1-11 prompt: {"created":n,"duplicates":n,"errors":[{"row","message"}]}.
 * Row numbers: the page assumes the header is row 1 (so the first data row is row 2).
 * Confirm that with P1; if they count differently, only the hint text on the page changes.
 * ------------------------------------------------------------------ */
export interface ImportRowError {
  row: number
  message: string
}

export interface ImportResult {
  created: number
  duplicates: number
  errors: ImportRowError[]
}
