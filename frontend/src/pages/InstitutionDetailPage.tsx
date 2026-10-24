import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import type { UseQueryResult } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { getInstitution, getInstitutionCases, getInstitutionOverlaps } from '../api/institutions'
import type { Institution } from '../api/institutionTypes'
import type { OverlapRow } from '../api/overlapTypes'
import type { CaseRow, Paged } from '../api/types'
import AsyncBoundary from '../components/AsyncBoundary'
import BureauStatusMatrix from '../components/institution/BureauStatusMatrix'
import InstitutionOverlaps from '../components/institution/InstitutionOverlaps'
import InstitutionTimeline from '../components/institution/InstitutionTimeline'
import CasesTable from '../components/CasesTable'
import { EmptyState } from '../components/states'
import { OVERLAP_HEADING } from '../lib/constants'
import { fmtNum } from '../lib/format'
import { casesLink, summarise } from '../lib/institution'
import { REGIONS } from '../lib/lookups'

const CARD = 'rounded-md border border-slate-200 bg-white'
const CARD_H = 'border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800'
const POLL = 45_000

type Tab = 'cases' | 'overlaps' | 'timeline'
const TABS: Array<[Tab, string]> = [
  ['cases', 'All cases'],
  ['overlaps', 'Overlaps'],
  ['timeline', 'Timeline'],
]

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-900">{children || '—'}</dd>
    </div>
  )
}

function IdentityCard({ inst }: { inst: Institution }) {
  const region = inst.region_name ?? REGIONS.find((r) => r.id === inst.region_id)?.label
  return (
    <section className={`${CARD} px-4 py-3`}>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-lg font-semibold text-slate-900">{inst.name}</h1>
        {inst.status && (
          <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600">
            {inst.status}
          </span>
        )}
      </div>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="AICTE permanent ID">{inst.aicte_permanent_id}</Field>
        <Field label="Type">{inst.type}</Field>
        <Field label="Region">{region}</Field>
        <Field label="State">{inst.state}</Field>
        <Field label="District">{inst.district}</Field>
        <div className="sm:col-span-2">
          <Field label="Address">{inst.address}</Field>
        </div>
      </dl>
    </section>
  )
}

function Tile({ label, value, to }: { label: string; value: number; to?: string }) {
  const inner = (
    <>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-semibold tabular-nums text-slate-900">{fmtNum(value)}</div>
    </>
  )
  const cls = 'block rounded-md border border-slate-200 bg-white px-4 py-3'
  return to ? (
    <Link to={to} className={`${cls} hover:bg-slate-50`}>
      {inner}
    </Link>
  ) : (
    <div className={cls}>{inner}</div>
  )
}

function Body({
  inst,
  cases,
  overlapsQ,
}: {
  inst: Institution
  cases: Paged<CaseRow>
  overlapsQ: UseQueryResult<OverlapRow[]>
}) {
  const [tab, setTab] = useState<Tab>('cases')
  const summary = useMemo(() => summarise(cases.items), [cases.items])
  const tierAOpen = overlapsQ.data?.some((o) => o.tier === 'A' && o.state === 'OPEN') ?? false

  return (
    <div className="space-y-3">
      {tierAOpen && (
        <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          <div className="font-semibold">{OVERLAP_HEADING}</div>
          <div>
            Open cases in {summary.openBureaus.join(' + ') || 'more than one bureau'} for this institution.{' '}
            <Link to="/overlaps?state=OPEN" className="underline">
              Open Overlap Center
            </Link>
          </div>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Tile label="Total cases" value={summary.total} to={casesLink(inst.id)} />
        <Tile label="Open cases" value={summary.open} />
        <Tile label="Beyond SLA" value={summary.beyondSla} />
      </div>

      {cases.total > cases.items.length && (
        <p className="text-xs text-amber-800">
          Showing the first {fmtNum(cases.items.length)} of {fmtNum(cases.total)} cases; the numbers below cover
          only those.
        </p>
      )}

      <section className={CARD}>
        <h2 className={CARD_H}>Cases by bureau and status</h2>
        {summary.rows.length === 0 ? (
          <EmptyState text="No cases for this institution." />
        ) : (
          <BureauStatusMatrix institutionId={inst.id} summary={summary} />
        )}
      </section>

      <section className={CARD}>
        <div role="tablist" aria-label="Institution sections" className="flex gap-1 border-b border-slate-200 px-3 pt-2">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`-mb-px border-b-2 px-3 py-2 text-sm ${
                tab === key
                  ? 'border-slate-800 font-semibold text-slate-900'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              {label}
              {key === 'cases' && ` (${fmtNum(cases.total)})`}
            </button>
          ))}
        </div>

        <div role="tabpanel">
          {tab === 'cases' &&
            (cases.items.length === 0 ? (
              <EmptyState text="No cases for this institution." />
            ) : (
              <CasesTable rows={cases.items} />
            ))}
          {tab === 'overlaps' && (
            <AsyncBoundary query={overlapsQ} height={160}>
              {(rows) => <InstitutionOverlaps rows={rows} />}
            </AsyncBoundary>
          )}
          {tab === 'timeline' && (
            <div className="px-4 py-3">
              <InstitutionTimeline cases={cases.items} />
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

function Loader({ id }: { id: number }) {
  const instQ = useQuery({ queryKey: ['institution', id], queryFn: () => getInstitution(id) })
  const casesQ = useQuery({
    queryKey: ['institution', id, 'cases'],
    queryFn: () => getInstitutionCases(id),
    refetchInterval: POLL,
  })
  const overlapsQ = useQuery({
    queryKey: ['institution', id, 'overlaps'],
    queryFn: () => getInstitutionOverlaps(id),
    refetchInterval: POLL,
  })

  return (
    <div className="space-y-3">
      <AsyncBoundary query={instQ} height={140}>
        {(inst) => (
          <>
            <IdentityCard inst={inst} />
            <AsyncBoundary query={casesQ} height={320}>
              {(cases) => <Body inst={inst} cases={cases} overlapsQ={overlapsQ} />}
            </AsyncBoundary>
          </>
        )}
      </AsyncBoundary>
    </div>
  )
}

export default function InstitutionDetailPage() {
  const { id: idParam } = useParams<{ id: string }>()
  const id = Number(idParam)
  const valid = Number.isInteger(id) && id > 0

  return (
    <div className="mx-auto max-w-[1400px] space-y-3">
      <Link to="/institutions" className="inline-flex items-center gap-1 text-sm text-teal hover:underline">
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Back to institutions
      </Link>
      {valid ? <Loader key={id} id={id} /> : <EmptyState text="Invalid institution id." />}
    </div>
  )
}
