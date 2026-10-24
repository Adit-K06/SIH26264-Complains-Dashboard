// Mock importer. It validates the CSV like the real endpoint should, but NOTHING IS STORED:
// imported rows do not appear in Cases (the mock lists are fixed). Duplicate detection only
// remembers rows imported since the page was loaded.
import { REQUIRED_COLUMNS, normHeader, parseCsv } from '../../lib/importCsv'
import { BUREAUS } from '../../lib/lookups'
import type { ImportResult, ImportRowError } from '../importTypes'

const seen = new Set<string>()
const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH']
const BUREAU_CODES = BUREAUS.map((b) => b.label)

const isRealDate = (v: string) =>
  /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(`${v}T00:00:00Z`)) && new Date(`${v}T00:00:00Z`).toISOString().slice(0, 10) === v

export function mockImport(text: string): ImportResult {
  const rows = parseCsv(text)
  if (rows.length === 0 || rows[0].every((c) => c.trim() === '')) throw new Error('The file is empty.')

  const header = normHeader(rows[0])
  const missing = REQUIRED_COLUMNS.filter((c) => !header.includes(c))
  if (missing.length > 0) throw new Error(`Missing required column(s): ${missing.join(', ')}`)

  const today = new Date().toISOString().slice(0, 10)
  const errors: ImportRowError[] = []
  let created = 0
  let duplicates = 0

  for (let i = 1; i < rows.length; i++) {
    const r = rows[i]
    if (r.every((c) => c.trim() === '')) continue // blank line
    const get = (name: string) => (r[header.indexOf(name)] ?? '').trim()
    const problems: string[] = []

    for (const col of REQUIRED_COLUMNS) if (!get(col)) problems.push(`${col} is required`)
    const bureau = get('bureau').toUpperCase()
    if (bureau && !BUREAU_CODES.includes(bureau)) problems.push(`unknown bureau "${get('bureau')}"`)
    const received = get('received_on')
    if (received && !isRealDate(received)) problems.push('received_on must be a valid date as YYYY-MM-DD')
    else if (received && received > today) problems.push('received_on cannot be in the future')
    const priority = get('priority').toUpperCase()
    if (priority && !PRIORITIES.includes(priority)) problems.push('priority must be LOW, MEDIUM or HIGH')

    if (problems.length > 0) {
      errors.push({ row: i + 1, message: problems.join('; ') }) // header = row 1
      continue
    }
    const key = `${bureau}|${get('case_no')}`
    if (seen.has(key)) duplicates += 1
    else {
      seen.add(key)
      created += 1
    }
  }
  return { created, duplicates, errors }
}
