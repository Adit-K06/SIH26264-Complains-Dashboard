import { fmtVal } from '../../lib/evaluation'
import type { Example } from '../../lib/evaluation'
import { humanize } from '../../lib/reportTable'
import { EmptyState } from '../states'

export default function ExampleList({ items, emptyText }: { items: Example[]; emptyText: string }) {
  if (items.length === 0) return <EmptyState text={emptyText} />
  return (
    <ol className="space-y-3">
      {items.map((it, i) => (
        <li key={i} className="rounded border border-slate-200 bg-slate-50 p-3">
          <dl className="grid gap-x-3 gap-y-1 text-sm sm:grid-cols-[10rem_1fr]">
            {Object.entries(it).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-slate-500">{humanize(k)}</dt>
                <dd className="min-w-0 break-words text-slate-900">{fmtVal(v)}</dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ol>
  )
}
