import { Link } from 'react-router-dom'
import type { OverlapFlag } from '../api/types'

export default function OverlapList({ flags }: { flags: OverlapFlag[] }) {
  return (
    <ul className="divide-y divide-slate-100">
      {flags.map((f) => (
        <li key={f.id}>
          <Link
            to={`/overlaps?state=OPEN&institution_id=${f.institution_id}`}
            className="block px-1 py-2.5 hover:bg-slate-50"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-sm font-medium text-slate-800">
                {f.institution_name ?? `Institution #${f.institution_id}`}
              </span>
              <span className="flex shrink-0 items-center gap-2 text-xs">
                <span className="rounded border border-slate-300 px-1.5 py-0.5 text-slate-600">
                  Tier {f.tier}
                </span>
                {f.score !== null && (
                  <span className="font-semibold text-navy">{f.score.toFixed(2)}</span>
                )}
              </span>
            </div>

            {f.score !== null && (
              <div className="mt-1.5 h-1.5 w-full rounded bg-slate-100" aria-hidden>
                <div
                  className="h-1.5 rounded bg-teal"
                  style={{ width: `${Math.round(Math.min(1, Math.max(0, f.score)) * 100)}%` }}
                />
              </div>
            )}

            <div className="mt-1.5 flex flex-wrap gap-1">
              {f.reasons.map((r) => (
                <span
                  key={r}
                  className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600"
                >
                  {r}
                </span>
              ))}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}
