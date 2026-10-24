import { useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { errorMessage } from '../api/client'
import { importCasesCsv } from '../api/importCsv'
import CurlSample from '../components/import/CurlSample'
import ResultPanel from '../components/import/ResultPanel'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { saveBlob } from '../lib/download'
import { fmtNum } from '../lib/format'
import {
  IMPORT_COLUMNS,
  MAX_IMPORT_BYTES,
  REQUIRED_COLUMNS,
  buildSampleCsv,
  normHeader,
  parseCsv,
} from '../lib/importCsv'

const CARD = 'rounded-md border border-slate-200 bg-white'
const CARD_H = 'border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800'

export default function ImportPage() {
  const user = useCurrentUser()
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [headerWarning, setHeaderWarning] = useState<string | null>(null)

  const canImport = user.role !== 'SENIOR_MGMT' // AGENTS.md: SENIOR_MGMT is read + escalate only

  const upload = useMutation({
    mutationFn: (f: File) => importCasesCsv(f),
    onSuccess: () => {
      setFile(null)
      setHeaderWarning(null)
      // New cases can change every list and count in the app.
      for (const key of ['cases', 'dashboard', 'overlaps', 'alerts', 'institutions', 'institution', 'report']) {
        void qc.invalidateQueries({ queryKey: [key] })
      }
    },
  })

  async function onPick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ''
    upload.reset()
    setFile(null)
    setFileError(null)
    setHeaderWarning(null)
    if (!f) return
    if (!/\.csv$/i.test(f.name)) {
      setFileError('Please choose a .csv file.')
      return
    }
    if (f.size === 0) {
      setFileError('The file is empty.')
      return
    }
    if (f.size > MAX_IMPORT_BYTES) {
      setFileError('The file is larger than 5 MB.')
      return
    }
    setFile(f)
    try {
      const first = parseCsv(await f.slice(0, 8192).text())[0] ?? []
      const have = normHeader(first)
      const missing = REQUIRED_COLUMNS.filter((c) => !have.includes(c))
      if (missing.length > 0) {
        setHeaderWarning(`The header row seems to be missing: ${missing.join(', ')}. The server will check the file again.`)
      }
    } catch {
      // The header check is only a convenience; the server validates the file.
    }
  }

  function downloadSample() {
    saveBlob(new Blob([buildSampleCsv()], { type: 'text/csv' }), 'sample-cases-import.csv')
  }

  return (
    <div className="mx-auto max-w-[1100px] space-y-3">
      <h1 className="text-lg font-semibold text-slate-900">Import cases</h1>

      <section className={CARD}>
        <h2 className={CARD_H}>Upload a CSV file</h2>
        <div className="space-y-3 px-4 py-3">
          {!canImport ? (
            <p className="text-sm text-slate-600">Your role has read-only access, so it cannot import cases.</p>
          ) : (
            <>
              <p className="text-sm text-slate-600">
                Bulk-add cases from a bureau system export. Cases already imported (same bureau and case_no) are
                ignored, so uploading a file twice is safe. Maximum size 5 MB.
              </p>

              <div className="flex flex-wrap items-center gap-3">
                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={(e) => void onPick(e)}
                />
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  disabled={upload.isPending}
                  className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Choose CSV file
                </button>
                <span className="text-sm text-slate-700">
                  {file ? `${file.name} (${fmtNum(Math.max(1, Math.round(file.size / 1024)))} KB)` : 'No file selected'}
                </span>
                <button
                  type="button"
                  onClick={() => file && upload.mutate(file)}
                  disabled={!file || upload.isPending}
                  className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
                >
                  {upload.isPending ? 'Importing…' : 'Import'}
                </button>
              </div>

              {fileError && (
                <p role="alert" className="text-sm text-red-700">
                  {fileError}
                </p>
              )}
              {headerWarning && (
                <p role="status" className="text-sm text-amber-800">
                  {headerWarning}
                </p>
              )}
              {upload.isError && (
                <p role="alert" className="text-sm text-red-700">
                  Import failed: {errorMessage(upload.error)}
                </p>
              )}
            </>
          )}
        </div>
      </section>

      {upload.data && <ResultPanel result={upload.data} />}

      <section className={CARD}>
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2">
          <h2 className="text-sm font-semibold text-slate-800">CSV format</h2>
          <button
            type="button"
            onClick={downloadSample}
            className="rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
          >
            Download sample CSV
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th scope="col" className="px-3 py-2">Column</th>
                <th scope="col" className="px-3 py-2">Required</th>
                <th scope="col" className="px-3 py-2">Notes</th>
              </tr>
            </thead>
            <tbody>
              {IMPORT_COLUMNS.map((c) => (
                <tr key={c.name} className="border-b border-slate-100">
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-slate-900">{c.name}</td>
                  <td className="px-3 py-2">{c.required ? 'Yes' : 'No'}</td>
                  <td className="px-3 py-2 text-slate-600">{c.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="px-4 py-2 text-xs text-slate-500">
          Row numbers in the error report count the header as row 1. Use synthetic data only.
        </p>
      </section>

      <CurlSample />
    </div>
  )
}
