import { Link } from 'react-router-dom'
import { fmtNum } from '../lib/format'

interface Props {
  label: string
  value?: number
  to: string // every number is a link to a filtered list
  color: string
}

export default function KpiTile({ label, value, to, color }: Props) {
  return (
    <Link
      to={to}
      className="block rounded-md border border-slate-200 bg-white px-4 py-3 hover:border-teal focus:outline-none focus-visible:ring-2 focus-visible:ring-teal"
      style={{ borderLeftWidth: 4, borderLeftColor: color }}
      aria-label={`${label}: ${value ?? 'loading'}. Open list`}
    >
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">
        {value === undefined ? '—' : fmtNum(value)}
      </div>
    </Link>
  )
}
