import { fmtNum } from '../../lib/format'
import type { Confusion } from '../../lib/evaluation'

function Cell({ label, value }: { label: string; value: number }) {
  return (
    <td className="border border-slate-200 px-4 py-3 text-center">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-xl font-semibold tabular-nums text-slate-900">{fmtNum(value)}</div>
    </td>
  )
}

/** Rows = what is true, columns = what the method predicted. */
export default function ConfusionMatrix({ title, m }: { title: string; m: Confusion }) {
  const th = 'border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600'
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-800">{title}</h3>
      <table className="border-collapse text-sm">
        <thead>
          <tr>
            <th className={th} />
            <th scope="col" className={th}>Predicted overlap</th>
            <th scope="col" className={th}>Predicted not overlap</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row" className={th}>Truly overlap</th>
            <Cell label="True positive" value={m.tp} />
            <Cell label="False negative (missed)" value={m.fn} />
          </tr>
          <tr>
            <th scope="row" className={th}>Truly not overlap</th>
            <Cell label="False positive" value={m.fp} />
            <Cell label="True negative" value={m.tn} />
          </tr>
        </tbody>
      </table>
    </div>
  )
}
