import { STATUS_BADGE_CLASS, STATUS_LABEL } from '../lib/constants'
import type { CaseStatus } from '../lib/constants'

export default function StatusBadge({ status }: { status: CaseStatus }) {
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASS[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  )
}
