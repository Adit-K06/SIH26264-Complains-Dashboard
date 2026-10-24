import { api } from './client'
import { USE_MOCKS } from './config'
import type { ImportResult } from './importTypes'
import { mockImport } from './mocks/importCsv'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

function normalise(data: unknown): ImportResult {
  const o = isObj(data) ? data : {}
  const num = (v: unknown) => (typeof v === 'number' ? v : 0)
  const errs = Array.isArray(o.errors) ? o.errors : []
  return {
    created: num(o.created),
    duplicates: num(o.duplicates),
    errors: errs.map((e) => {
      const x = isObj(e) ? e : {}
      return {
        row: Number(x.row) || 0,
        message: String(x.message ?? x.reason ?? x.error ?? 'Invalid row'),
      }
    }),
  }
}

// POST /import/cases-csv  (multipart field "file")
export async function importCasesCsv(file: File): Promise<ImportResult> {
  if (USE_MOCKS) {
    const text = await file.text()
    await delay(600)
    return mockImport(text)
  }
  const fd = new FormData()
  fd.append('file', file)
  const res = await api.post<unknown>('/import/cases-csv', fd)
  return normalise(res.data)
}
