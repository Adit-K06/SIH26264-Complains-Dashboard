import { reasonLabel, STATE_LABEL } from '../../lib/overlap'
import type { OverlapState } from '../../lib/overlap'

export function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-slate-500">Rule match</span>
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)))
  return (
    <div className="flex items-center gap-2" title={`Score ${score.toFixed(2)}`}>
      <div className="h-2 w-20 overflow-hidden rounded bg-slate-100">
        <div className="h-full bg-sky-600" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-slate-700">{score.toFixed(2)}</span>
    </div>
  )
}

export function ReasonChips({ reasons }: { reasons: string[] }) {
  if (reasons.length === 0) return <span className="text-slate-400">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {reasons.map((r) => (
        <span
          key={r}
          title={r}
          className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-xs text-slate-700"
        >
          {reasonLabel(r)}
        </span>
      ))}
    </div>
  )
}

export function TierBadge({ tier }: { tier: 'A' | 'B' }) {
  const cls = tier === 'A' ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-blue-200 bg-blue-50 text-blue-800'
  return (
    <span className={`rounded border px-1.5 py-0.5 text-xs font-medium ${cls}`}>
      Tier {tier}
    </span>
  )
}

const STATE_CLS: Record<OverlapState, string> = {
  OPEN: 'border-amber-200 bg-amber-50 text-amber-800',
  CONFIRMED: 'border-green-200 bg-green-50 text-green-800',
  DISMISSED: 'border-slate-200 bg-slate-50 text-slate-600',
}

export function OverlapStateBadge({ state }: { state: OverlapState }) {
  return (
    <span className={`rounded border px-1.5 py-0.5 text-xs font-medium ${STATE_CLS[state]}`}>
      {STATE_LABEL[state]}
    </span>
  )
}
