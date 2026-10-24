import { ChevronLeft, ChevronRight } from 'lucide-react'
import { PAGE_SIZES } from '../lib/caseFilters'
import { fmtNum } from '../lib/format'

interface Props {
  page: number
  pageSize: number
  total: number
  onPage: (p: number) => void
  onPageSize: (s: number) => void
}

const BTN =
  'inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40'

export default function Pagination({ page, pageSize, total, onPage, onPageSize }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)

  return (
    <nav
      aria-label="Pagination"
      className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-3 py-2 text-sm text-slate-600"
    >
      <span>
        Showing {fmtNum(from)}–{fmtNum(to)} of {fmtNum(total)}
      </span>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1 text-xs">
          Rows
          <select
            value={pageSize}
            onChange={(e) => onPageSize(Number(e.target.value))}
            className="rounded border border-slate-300 bg-white px-1 py-1 text-sm"
          >
            {PAGE_SIZES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className={BTN} disabled={page <= 1} onClick={() => onPage(page - 1)}>
          <ChevronLeft className="h-4 w-4" aria-hidden /> Prev
        </button>
        <span className="tabular-nums">
          Page {page} of {pages}
        </span>
        <button type="button" className={BTN} disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next <ChevronRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </nav>
  )
}
