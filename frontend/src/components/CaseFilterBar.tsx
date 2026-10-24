import { useEffect, useId, useState } from 'react'
import { Search, X } from 'lucide-react'
import { PRIORITIES, STATUSES, STATUS_LABEL } from '../lib/constants'
import { BUREAUS, CATEGORIES, REGIONS } from '../lib/lookups'
import type { Option } from '../lib/lookups'
import { activeFilterCount, extraChips } from '../lib/caseFilters'
import type { CaseFilters, FilterPatch } from '../lib/caseFilters'

interface Props {
  filters: CaseFilters
  setFilters: (patch: FilterPatch) => void
  clear: () => void
}

const INPUT =
  'w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800 focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal'
const LABEL = 'mb-1 block text-xs font-medium text-slate-600'

function SelectField(props: {
  label: string
  value: string
  onChange: (v: string) => void
  options: Array<{ value: string; label: string }>
}) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className={LABEL}>
        {props.label}
      </label>
      <select
        id={id}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        className={INPUT}
      >
        <option value="">All</option>
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

const idOptions = (list: Option[]) => list.map((o) => ({ value: String(o.id), label: o.label }))
const toId = (v: string) => (v ? Number(v) : undefined)

export default function CaseFilterBar({ filters, setFilters, clear }: Props) {
  const searchId = useId()
  const fromId = useId()
  const toDateId = useId()

  // Debounced search: type freely, the URL (and the request) updates 400 ms after you stop.
  const [text, setText] = useState(filters.q)
  useEffect(() => setText(filters.q), [filters.q]) // follow external changes (Clear, back button)
  useEffect(() => {
    if (text.trim() === filters.q) return
    const t = setTimeout(() => setFilters({ q: text.trim() }), 400)
    return () => clearTimeout(t)
  }, [text, filters.q, setFilters])

  const chips = extraChips(filters)
  const active = activeFilterCount(filters)

  return (
    <section aria-label="Filters" className="rounded-md border border-slate-200 bg-white p-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
        <div className="sm:col-span-2">
          <label htmlFor={searchId} className={LABEL}>
            Search case no. or institution
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2 top-2 h-4 w-4 text-slate-400" aria-hidden />
            <input
              id={searchId}
              type="search"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="e.g. PGRC/2026 or Synthetic Polytechnic"
              className={`${INPUT} pl-8`}
            />
          </div>
        </div>

        <SelectField
          label="Status"
          value={filters.status ?? ''}
          onChange={(v) => setFilters({ status: STATUSES.find((s) => s === v) })}
          options={STATUSES.map((s) => ({ value: s, label: STATUS_LABEL[s] }))}
        />
        <SelectField
          label="Bureau"
          value={filters.bureau_id ? String(filters.bureau_id) : ''}
          onChange={(v) => setFilters({ bureau_id: toId(v) })}
          options={idOptions(BUREAUS)}
        />
        <SelectField
          label="Region"
          value={filters.region_id ? String(filters.region_id) : ''}
          onChange={(v) => setFilters({ region_id: toId(v) })}
          options={idOptions(REGIONS)}
        />
        <SelectField
          label="Category"
          value={filters.category_id ? String(filters.category_id) : ''}
          onChange={(v) => setFilters({ category_id: toId(v) })}
          options={idOptions(CATEGORIES)}
        />
        <SelectField
          label="Priority"
          value={filters.priority ?? ''}
          onChange={(v) => setFilters({ priority: PRIORITIES.find((p) => p === v) })}
          options={PRIORITIES.map((p) => ({ value: p, label: p[0] + p.slice(1).toLowerCase() }))}
        />

        <div>
          <label htmlFor={fromId} className={LABEL}>
            Received from
          </label>
          <input
            id={fromId}
            type="date"
            value={filters.from_date ?? ''}
            max={filters.to_date}
            onChange={(e) => setFilters({ from_date: e.target.value || undefined })}
            className={INPUT}
          />
        </div>
        <div>
          <label htmlFor={toDateId} className={LABEL}>
            Received to
          </label>
          <input
            id={toDateId}
            type="date"
            value={filters.to_date ?? ''}
            min={filters.from_date}
            onChange={(e) => setFilters({ to_date: e.target.value || undefined })}
            className={INPUT}
          />
        </div>

        <label className="flex items-end gap-2 pb-1.5 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={filters.beyond_sla}
            onChange={(e) => setFilters({ beyond_sla: e.target.checked })}
            className="h-4 w-4 accent-teal"
          />
          Beyond SLA only
        </label>
      </div>

      {(chips.length > 0 || active > 0) && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-xs">
          {chips.map((c) => (
            <span
              key={c.key}
              className="inline-flex items-center gap-1 rounded border border-teal/40 bg-teal/5 px-2 py-0.5 text-teal"
            >
              {c.label}
              <button
                type="button"
                onClick={() => setFilters(c.patch)}
                aria-label={`Remove filter: ${c.label}`}
                className="rounded hover:bg-teal/10"
              >
                <X className="h-3 w-3" aria-hidden />
              </button>
            </span>
          ))}
          {active > 0 && (
            <button
              type="button"
              onClick={clear}
              className="rounded border border-slate-300 bg-white px-2 py-0.5 text-slate-700 hover:bg-slate-50"
            >
              Clear all ({active})
            </button>
          )}
        </div>
      )}
    </section>
  )
}
