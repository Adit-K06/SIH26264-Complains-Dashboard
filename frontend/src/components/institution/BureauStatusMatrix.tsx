import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { STATUSES, STATUS_LABEL } from '../../lib/constants'
import { fmtNum } from '../../lib/format'
import { casesLink } from '../../lib/institution'
import type { InstSummary } from '../../lib/institution'

const TH =
  'whitespace-nowrap bg-slate-50 px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-slate-500'

function Num({ n, to }: { n: number; to?: string }): ReactNode {
  if (n === 0 || !to) return <span className="text-slate-400">{fmtNum(n)}</span>
  return (
    <Link to={to} className="font-medium text-teal hover:underline">
      {fmtNum(n)}
    </Link>
  )
}

/** Bureau x status counts for one institution. Every non-zero number opens the filtered Cases list. */
export default function BureauStatusMatrix({
  institutionId,
  summary,
}: {
  institutionId: number
  summary: InstSummary
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[680px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th scope="col" className={`${TH} text-left`}>Bureau</th>
            {STATUSES.map((s) => (
              <th key={s} scope="col" className={TH}>
                {STATUS_LABEL[s]}
              </th>
            ))}
            <th scope="col" className={TH}>Total</th>
          </tr>
        </thead>
        <tbody>
          {summary.rows.map((r) => (
            <tr key={r.key} className="border-b border-slate-100">
              <th scope="row" className="whitespace-nowrap px-3 py-2 text-left font-medium text-slate-900">
                {r.label}
              </th>
              {STATUSES.map((s) => (
                <td key={s} className="px-3 py-2 text-right tabular-nums">
                  <Num
                    n={r.counts[s]}
                    to={r.bureau_id ? casesLink(institutionId, { bureau_id: r.bureau_id, status: s }) : undefined}
                  />
                </td>
              ))}
              <td className="px-3 py-2 text-right tabular-nums">
                <Num n={r.total} to={r.bureau_id ? casesLink(institutionId, { bureau_id: r.bureau_id }) : undefined} />
              </td>
            </tr>
          ))}
          <tr className="bg-slate-50">
            <th scope="row" className="px-3 py-2 text-left font-semibold text-slate-900">
              All bureaus
            </th>
            {STATUSES.map((s) => (
              <td key={s} className="px-3 py-2 text-right tabular-nums">
                <Num n={summary.totals[s]} to={casesLink(institutionId, { status: s })} />
              </td>
            ))}
            <td className="px-3 py-2 text-right tabular-nums">
              <Num n={summary.total} to={casesLink(institutionId)} />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
