import { fmtNum } from '../../lib/format'
import { fmtCell, numericColumns } from '../../lib/reportTable'
import type { ReportTable } from '../../lib/reportTable'

const TH =
  'whitespace-nowrap bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500'

const LIMIT = 200

export default function ReportTableView({ table }: { table: ReportTable }) {
  const numeric = new Set(numericColumns(table))
  const shown = table.rows.slice(0, LIMIT)

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              {table.columns.map((c, i) => (
                <th key={`${c}-${i}`} scope="col" className={`${TH} ${numeric.has(i) ? 'text-right' : 'text-left'}`}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((r, ri) => (
              <tr key={ri} className="border-b border-slate-100 hover:bg-slate-50">
                {r.map((v, ci) => (
                  <td
                    key={ci}
                    className={`whitespace-nowrap px-3 py-2 ${numeric.has(ci) ? 'text-right tabular-nums' : ''}`}
                  >
                    {fmtCell(v)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.rows.length > LIMIT && (
        <p className="px-4 py-2 text-xs text-slate-500">
          Showing the first {fmtNum(LIMIT)} of {fmtNum(table.rows.length)} rows. Download the report for all rows.
        </p>
      )}
    </div>
  )
}
