import { Link } from 'react-router-dom'
import type { CaseRow } from '../api/types'
import { daysOverdue, fmtDate } from '../lib/format'
import StatusBadge from './StatusBadge'

const TH = 'sticky top-0 bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500'

export default function BeyondSlaTable({ rows }: { rows: CaseRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className={TH}>Case no.</th>
            <th className={TH}>Institution</th>
            <th className={TH}>Bureau</th>
            <th className={TH}>Status</th>
            <th className={TH}>Priority</th>
            <th className={TH}>Due</th>
            <th className={`${TH} text-right`}>Days overdue</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => {
            const od = daysOverdue(c.expected_disposal_on)
            return (
              <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2 font-medium">
                  <Link to={`/cases/${c.id}`} className="text-teal hover:underline">
                    {c.case_no}
                  </Link>
                </td>
                <td className="px-3 py-2">{c.institution_name ?? '—'}</td>
                <td className="px-3 py-2">{c.bureau_code ?? '—'}</td>
                <td className="px-3 py-2">
                  <StatusBadge status={c.status} />
                </td>
                <td className="px-3 py-2">{c.priority ?? '—'}</td>
                <td className="px-3 py-2">{fmtDate(c.expected_disposal_on)}</td>
                <td className="px-3 py-2 text-right font-semibold text-red-700">
                  {od !== null && od > 0 ? od : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
