import { Link } from 'react-router-dom'
import { USE_MOCKS } from '../../api/config'
import type { ImportResult } from '../../api/importTypes'
import { saveBlob } from '../../lib/download'
import { fmtNum } from '../../lib/format'
import { toCsv } from '../../lib/reportTable'

const LIMIT = 200

function Tile({ label, value, cls }: { label: string; value: number; cls: string }) {
  return (
    <div className={`rounded-md border px-4 py-3 ${cls}`}>
      <div className="text-xs">{label}</div>
      <div className="text-2xl font-semibold tabular-nums">{fmtNum(value)}</div>
    </div>
  )
}

export default function ResultPanel({ result }: { result: ImportResult }) {
  const { created, duplicates, errors } = result

  function downloadErrors() {
    const csv = toCsv({ columns: ['Row', 'Message'], rows: errors.map((e) => [e.row || null, e.message]) })
    saveBlob(new Blob([csv], { type: 'text/csv' }), `import-errors-${new Date().toISOString().slice(0, 10)}.csv`)
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white" aria-live="polite">
      <h2 className="border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800">Import result</h2>
      <div className="space-y-3 px-4 py-3">
        {USE_MOCKS && (
          <p className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
            Mock mode: the file was checked like the real import would check it, but nothing was stored.
          </p>
        )}

        <div className="grid gap-3 sm:grid-cols-3">
          <Tile label="Created" value={created} cls="border-green-200 bg-green-50 text-green-800" />
          <Tile label="Duplicates ignored" value={duplicates} cls="border-slate-200 bg-slate-50 text-slate-700" />
          <Tile
            label="Rows with errors"
            value={errors.length}
            cls={errors.length > 0 ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 bg-slate-50 text-slate-700'}
          />
        </div>

        {created > 0 && !USE_MOCKS && (
          <p className="text-sm text-slate-600">
            Overlap detection runs in the background after an import, so new flags can take a moment to appear.{' '}
            <Link to="/cases" className="text-teal hover:underline">
              View cases
            </Link>
            {' · '}
            <Link to="/overlaps?state=OPEN" className="text-teal hover:underline">
              Overlap Center
            </Link>
          </p>
        )}

        {errors.length > 0 && (
          <div>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-slate-800">Rows that were rejected</h3>
              <button
                type="button"
                onClick={downloadErrors}
                className="rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
              >
                Download error report (CSV)
              </button>
            </div>
            <div className="overflow-x-auto rounded border border-slate-200">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th scope="col" className="w-20 px-3 py-2">Row</th>
                    <th scope="col" className="px-3 py-2">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {errors.slice(0, LIMIT).map((e, i) => (
                    <tr key={i} className="border-b border-slate-100 align-top">
                      <td className="px-3 py-2 tabular-nums">{e.row || '—'}</td>
                      <td className="px-3 py-2 text-slate-800">{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {errors.length > LIMIT && (
              <p className="mt-1 text-xs text-slate-500">
                Showing the first {fmtNum(LIMIT)} of {fmtNum(errors.length)} errors. Download the report for all of them.
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
