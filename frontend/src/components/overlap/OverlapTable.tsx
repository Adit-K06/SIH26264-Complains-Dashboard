import type { OverlapRow } from '../../api/overlapTypes'
import { bureausOf } from '../../lib/overlap'
import { OverlapStateBadge, ReasonChips, ScoreBar, TierBadge } from './OverlapBits'

const TH =
  'whitespace-nowrap bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500'

export default function OverlapTable({
  rows,
  onReview,
}: {
  rows: OverlapRow[]
  onReview: (row: OverlapRow) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th scope="col" className={TH}>Institution</th>
            <th scope="col" className={TH}>Bureaus involved</th>
            <th scope="col" className={TH}>Tier</th>
            <th scope="col" className={TH}>Score</th>
            <th scope="col" className={TH}>Why flagged</th>
            <th scope="col" className={TH}>State</th>
            <th scope="col" className={TH}>
              <span className="sr-only">Action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-slate-100 align-top hover:bg-slate-50">
              <td className="px-3 py-2">
                <div className="font-medium text-slate-900">
                  {r.institution_name ?? `Institution ${r.institution_id}`}
                </div>
                <div className="text-xs text-slate-500">ID {r.institution_id}</div>
              </td>
              <td className="whitespace-nowrap px-3 py-2">{bureausOf(r).join(' + ') || '—'}</td>
              <td className="px-3 py-2">
                <TierBadge tier={r.tier} />
              </td>
              <td className="px-3 py-2">
                <ScoreBar score={r.score} />
              </td>
              <td className="max-w-[26rem] px-3 py-2">
                <ReasonChips reasons={r.reasons} />
              </td>
              <td className="px-3 py-2">
                <OverlapStateBadge state={r.state} />
              </td>
              <td className="px-3 py-2 text-right">
                <button
                  type="button"
                  onClick={() => onReview(r)}
                  className="rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
                >
                  {r.state === 'OPEN' ? 'Review' : 'View'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
