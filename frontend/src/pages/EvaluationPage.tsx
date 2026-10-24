import { useQuery } from '@tanstack/react-query'
import { getEvaluation } from '../api/evaluation'
import { USE_MOCKS } from '../api/config'
import type { EvaluationData } from '../api/evaluation'
import AsyncBoundary from '../components/AsyncBoundary'
import ConfusionMatrix from '../components/evaluation/ConfusionMatrix'
import ExampleList from '../components/evaluation/ExampleList'
import { fmtNum } from '../lib/format'
import { fmtScore } from '../lib/evaluation'
import type { Prf } from '../lib/evaluation'

const CARD = 'rounded-md border border-slate-200 bg-white'
const CARD_H = 'border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800'
const DEFAULT_DISCLAIMER =
  'Synthetic data gives optimistic numbers. These figures describe the matcher on our generated test set, not on real AICTE complaints.'

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-4 py-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-semibold tabular-nums text-slate-900">{value}</div>
    </div>
  )
}

function PrfRow({ label, p }: { label: string; p?: Prf }) {
  return (
    <tr className="border-b border-slate-100">
      <th scope="row" className="px-3 py-2 text-left font-medium text-slate-900">
        {label}
      </th>
      <td className="px-3 py-2 text-right tabular-nums">{fmtScore(p?.precision)}</td>
      <td className="px-3 py-2 text-right tabular-nums">{fmtScore(p?.recall)}</td>
      <td className="px-3 py-2 text-right tabular-nums">{fmtScore(p?.f1)}</td>
    </tr>
  )
}

function Body({ data }: { data: EvaluationData }) {
  const v = data.view
  const TH = 'bg-slate-50 px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-slate-500'

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-4">
        <Tile label="Tuned threshold" value={v.threshold === undefined ? 'not in file' : String(v.threshold)} />
        <Tile label="Precision (held-out)" value={fmtScore(v.matcher.precision)} />
        <Tile label="Recall (held-out)" value={fmtScore(v.matcher.recall)} />
        <Tile label="F1 (held-out)" value={fmtScore(v.matcher.f1)} />
      </div>

      <section className={CARD}>
        <h2 className={CARD_H}>Matcher compared with a simple baseline</h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th scope="col" className="bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Method
                </th>
                <th scope="col" className={TH}>Precision</th>
                <th scope="col" className={TH}>Recall</th>
                <th scope="col" className={TH}>F1</th>
              </tr>
            </thead>
            <tbody>
              <PrfRow label="Our matcher (Tier B score)" p={v.matcher} />
              <PrfRow label="Baseline: same institution + category + within 30 days" p={v.baseline} />
            </tbody>
          </table>
        </div>
      </section>

      {(v.matcherConfusion || v.baselineConfusion) && (
        <section className={CARD}>
          <h2 className={CARD_H}>Confusion matrices (held-out split)</h2>
          <div className="flex flex-wrap gap-8 px-4 py-4">
            {v.matcherConfusion && <ConfusionMatrix title="Our matcher" m={v.matcherConfusion} />}
            {v.baselineConfusion && <ConfusionMatrix title="Baseline" m={v.baselineConfusion} />}
          </div>
        </section>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        <section className={CARD}>
          <h2 className={CARD_H}>False positives ({fmtNum(v.falsePositives.length)} shown)</h2>
          <div className="px-4 py-3">
            <ExampleList items={v.falsePositives} emptyText="No false-positive examples in the file." />
          </div>
        </section>
        <section className={CARD}>
          <h2 className={CARD_H}>Missed overlaps ({fmtNum(v.missed.length)} shown)</h2>
          <div className="px-4 py-3">
            <ExampleList items={v.missed} emptyText="No missed-overlap examples in the file." />
          </div>
        </section>
      </div>

      <section className={CARD}>
        <h2 className={CARD_H}>Re-run it yourself</h2>
        <div className="space-y-2 px-4 py-3">
          <p className="text-sm text-slate-600">
            Every number on this page comes from the evaluation script, not from the interface. To reproduce it:
          </p>
          <pre className="overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
            <code>docker compose exec api python -m app.ai.evaluate</code>
          </pre>
        </div>
      </section>

      <details className={CARD}>
        <summary className={`${CARD_H} cursor-pointer`}>Raw evaluation file</summary>
        <pre className="max-h-96 overflow-auto px-4 py-3 text-xs text-slate-800">
          <code>{JSON.stringify(data.raw, null, 2)}</code>
        </pre>
      </details>
    </div>
  )
}

export default function EvaluationPage() {
  const query = useQuery({ queryKey: ['evaluation'], queryFn: getEvaluation })

  return (
    <div className="mx-auto max-w-[1100px] space-y-3">
      <h1 className="text-lg font-semibold text-slate-900">Overlap matcher evaluation</h1>

      {USE_MOCKS && (
        <div role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800">
          MOCK DATA: every number below is a placeholder for layout testing. These are not results.
        </div>
      )}

      <div role="note" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
        {query.data?.view.disclaimer ?? DEFAULT_DISCLAIMER}
      </div>

      <AsyncBoundary query={query} height={320}>
        {(data) => <Body data={data} />}
      </AsyncBoundary>
    </div>
  )
}
