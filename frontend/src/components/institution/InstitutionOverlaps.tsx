import { Link } from 'react-router-dom'
import type { OverlapRow } from '../../api/overlapTypes'
import { bureausOf } from '../../lib/overlap'
import { OverlapStateBadge, ReasonChips, ScoreBar, TierBadge } from '../overlap/OverlapBits'
import { EmptyState } from '../states'

const TH =
  'whitespace-nowrap bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500'

export default function InstitutionOverlaps({ rows }: { rows: OverlapRow[] }) {
  if (rows.length === 0) return <EmptyState text="No overlap flags for this institution." />
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th scope="col" className={TH}>Bureaus</th>
            <th scope="col" className={TH}>Tier</th>
            <th scope="col" className={TH}>Score</th>
            <th scope="col" className={TH}>Why flagged</th>
            <th scope="col" className={TH}>State</th>
            <th scope="col" className={TH}>
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-slate-100 align-top">
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
              <td className="whitespace-nowrap px-3 py-2 text-right">
                <Link to={`/overlaps?state=${r.state}`} className="text-teal hover:underline">
                  Overlap Center
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
