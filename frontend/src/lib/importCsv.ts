/* ------------------------------------------------------------------
 * CSV columns for POST /import/cases-csv. From the P1-10 / P1-11 prompts: the CSV reuses the
 * ingest body: case_no, bureau, aicte_permanent_id?, institution_name, category, summary,
 * received_on, priority?, complainant_ref?. If P1 changes the headers, fix ONLY this file.
 * ------------------------------------------------------------------ */
export const MAX_IMPORT_BYTES = 5 * 1024 * 1024

export interface ImportColumn {
  name: string
  required: boolean
  note: string
}

export const IMPORT_COLUMNS: ImportColumn[] = [
  { name: 'case_no', required: true, note: 'Unique per bureau. Used to detect duplicates.' },
  { name: 'bureau', required: true, note: 'RB, PGRC, APPROVAL, ACADEMIC or FINANCE' },
  { name: 'aicte_permanent_id', required: false, note: 'If present, used to match the institution.' },
  { name: 'institution_name', required: true, note: 'Matched by name when the ID is missing.' },
  { name: 'category', required: true, note: 'For example: Fee refund, Ragging.' },
  { name: 'summary', required: true, note: 'Short description of the complaint.' },
  { name: 'received_on', required: true, note: 'Date as YYYY-MM-DD.' },
  { name: 'priority', required: false, note: 'LOW, MEDIUM or HIGH.' },
  { name: 'complainant_ref', required: false, note: 'A reference only. Never real names or phone numbers.' },
]

export const REQUIRED_COLUMNS = IMPORT_COLUMNS.filter((c) => c.required).map((c) => c.name)

/** One example case, used for the sample CSV and the sample curl. All values are SYNTHETIC. */
export const SAMPLE_CASE: Record<string, string> = {
  case_no: 'RB/2026/900001',
  bureau: 'RB',
  aicte_permanent_id: 'SYN-10001',
  institution_name: 'Synthetic Institute of Technology 1',
  category: 'Fee refund',
  summary: 'Synthetic complaint text for demonstration.',
  received_on: '2026-10-01',
  priority: 'MEDIUM',
  complainant_ref: 'CR-0001',
}

const SAMPLE_CASE_2: Record<string, string> = {
  ...SAMPLE_CASE,
  case_no: 'PGRC/2026/900002',
  bureau: 'PGRC',
  summary: 'Second synthetic complaint for the same institution.',
  received_on: '2026-10-05',
  priority: 'HIGH',
  complainant_ref: 'CR-0002',
}

export function buildSampleCsv(): string {
  const names = IMPORT_COLUMNS.map((c) => c.name)
  const line = (r: Record<string, string>) => names.map((n) => r[n] ?? '').join(',')
  return [names.join(','), line(SAMPLE_CASE), line(SAMPLE_CASE_2)].join('\r\n')
}

/** Small CSV parser (quotes, escaped quotes, CRLF, BOM). Returns rows of cells. */
export function parseCsv(text: string): string[][] {
  const src = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let inQuotes = false
  for (let i = 0; i < src.length; i++) {
    const ch = src[i]
    if (inQuotes) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          cell += '"'
          i++
        } else {
          inQuotes = false
        }
      } else {
        cell += ch
      }
    } else if (ch === '"') {
      inQuotes = true
    } else if (ch === ',') {
      row.push(cell)
      cell = ''
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && src[i + 1] === '\n') i++
      row.push(cell)
      cell = ''
      rows.push(row)
      row = []
    } else {
      cell += ch
    }
  }
  if (cell !== '' || row.length > 0) {
    row.push(cell)
    rows.push(row)
  }
  return rows
}

export const normHeader = (cells: string[]) => cells.map((h) => h.trim().toLowerCase())
