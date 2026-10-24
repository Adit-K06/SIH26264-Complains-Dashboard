/* ------------------------------------------------------------------
 * AGENTS.md gives the report endpoints but not the JSON body. To survive whatever P4 returns,
 * the page accepts any of these and turns it into one table:
 *   [ {col: value, ...}, ... ]          array of objects
 *   { items: [ {...}, ... ] }           paged-style envelope
 *   { columns: [...], rows: [[...]] }   explicit columns + array rows
 * If P4 picks something else, adjust normalizeReport() only.
 * ------------------------------------------------------------------ */
export type Cell = string | number | boolean | null

export interface ReportTable {
  columns: string[]
  rows: Cell[][]
}

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v)

const asCell = (v: unknown): Cell => {
  if (v === null || v === undefined) return null
  if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return v
  return JSON.stringify(v)
}

/** "disposal_rate" -> "Disposal rate" */
export function humanize(key: string): string {
  const s = key.replace(/[_-]+/g, ' ').trim()
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : key
}

export function normalizeReport(data: unknown): ReportTable {
  let rows: unknown[] = []
  let cols: string[] | null = null

  if (Array.isArray(data)) {
    rows = data
  } else if (isObj(data)) {
    if (Array.isArray(data.columns) && Array.isArray(data.rows)) {
      cols = data.columns.map(String)
      rows = data.rows
    } else if (Array.isArray(data.items)) {
      rows = data.items
    } else if (Array.isArray(data.rows)) {
      rows = data.rows
    }
  }

  if (rows.length > 0 && rows.every((r) => Array.isArray(r))) {
    const arrays = rows as unknown[][]
    const width = Math.max(...arrays.map((r) => r.length))
    const columns = cols ?? Array.from({ length: width }, (_, i) => `Column ${i + 1}`)
    return { columns, rows: arrays.map((r) => columns.map((_c, i) => asCell(r[i]))) }
  }

  const objs = rows.filter(isObj)
  const keys: string[] = cols ?? []
  if (!cols) {
    for (const o of objs) for (const k of Object.keys(o)) if (!keys.includes(k)) keys.push(k)
  }
  return {
    columns: cols ?? keys.map(humanize),
    rows: objs.map((o) => keys.map((k) => asCell(o[k]))),
  }
}

/** Indexes of columns whose non-empty cells are all numbers. */
export function numericColumns(t: ReportTable): number[] {
  const out: number[] = []
  t.columns.forEach((_c, i) => {
    const vals = t.rows.map((r) => r[i]).filter((v) => v !== null)
    if (vals.length > 0 && vals.every((v) => typeof v === 'number')) out.push(i)
  })
  return out
}

export function fmtCell(v: Cell): string {
  if (v === null) return '—'
  if (typeof v === 'number') return v.toLocaleString('en-IN', { maximumFractionDigits: 2 })
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  return v
}

const csvEscape = (v: Cell) => {
  const s = v === null ? '' : String(v)
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv(t: ReportTable): string {
  return [t.columns, ...t.rows].map((r) => r.map(csvEscape).join(',')).join('\r\n')
}
