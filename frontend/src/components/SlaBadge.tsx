import { slaState } from '../lib/sla'
import type { CaseStatus } from '../lib/constants'

interface Props {
  status: CaseStatus
  expected_disposal_on?: string | null
  received_on?: string | null
}

const BASE = 'inline-block whitespace-nowrap rounded border px-1.5 py-0.5 text-xs font-medium'

// Colour is never the only signal: the text always says what the state is.
export default function SlaBadge(props: Props) {
  const s = slaState(props)
  switch (s.kind) {
    case 'overdue':
      return <span className={`${BASE} border-red-200 bg-red-50 text-red-700`}>Overdue {s.days}d</span>
    case 'warn':
      return <span className={`${BASE} border-amber-200 bg-amber-50 text-amber-700`}>Due in {s.days}d</span>
    case 'ok':
      return <span className={`${BASE} border-green-200 bg-green-50 text-green-700`}>{s.days}d left</span>
    case 'closed':
      return <span className={`${BASE} border-slate-200 bg-slate-50 text-slate-500`}>Closed</span>
    default:
      return <span className="text-slate-400">—</span>
  }
}
