/* ------------------------------------------------------------------
 * GET /admin/evaluation returns docs/evaluation.json written by `python -m app.ai.evaluate`
 * (P2). The exact key names are NOT in the contract. The playbook says the file holds: tuned
 * threshold, precision / recall / F1 on the held-out split, a confusion matrix, baseline numbers,
 * 5 false positives, 5 missed overlaps with reasons, and a synthetic-data disclaimer.
 *
 * normalizeEvaluation() looks for those under several likely key names. Anything it cannot find is
 * shown as "not in the file", and the page always offers the raw JSON, so no number is ever
 * invented or silently dropped. If P2 uses other names, add them to the alias lists below.
 * The confusion matrix is only read as an object with tp/fp/fn/tn keys (a bare 2x2 array is
 * ambiguous, so it is left to the raw JSON view).
 * ------------------------------------------------------------------ */
export interface Prf {
  precision?: number
  recall?: number
  f1?: number
}

export interface Confusion {
  tp: number
  fp: number
  fn: number
  tn: number
}

export type Example = Record<string, unknown>

export interface EvalView {
  threshold?: number
  matcher: Prf
  matcherConfusion?: Confusion
  baseline?: Prf
  baselineConfusion?: Confusion
  falsePositives: Example[]
  missed: Example[]
  disclaimer?: string
}

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v)

const num = (v: unknown): number | undefined => (typeof v === 'number' && Number.isFinite(v) ? v : undefined)

function first(o: Record<string, unknown>, keys: string[]): unknown {
  for (const k of keys) if (o[k] !== undefined) return o[k]
  return undefined
}

function prf(o: Record<string, unknown>): Prf {
  return {
    precision: num(first(o, ['precision'])),
    recall: num(first(o, ['recall'])),
    f1: num(first(o, ['f1', 'f1_score'])),
  }
}

function confusion(v: unknown): Confusion | undefined {
  if (!isObj(v)) return undefined
  const tp = num(first(v, ['tp', 'true_positive', 'true_positives']))
  const fp = num(first(v, ['fp', 'false_positive', 'false_positives']))
  const fn = num(first(v, ['fn', 'false_negative', 'false_negatives']))
  const tn = num(first(v, ['tn', 'true_negative', 'true_negatives']))
  if (tp === undefined || fp === undefined || fn === undefined || tn === undefined) return undefined
  return { tp, fp, fn, tn }
}

function examples(v: unknown): Example[] {
  if (!Array.isArray(v)) return []
  return v.map((x) => (isObj(x) ? x : { detail: String(x) }))
}

export function normalizeEvaluation(data: unknown): EvalView {
  const o = isObj(data) ? data : {}
  let m: Record<string, unknown> = o
  for (const k of ['test', 'heldout', 'held_out', 'holdout', 'metrics', 'matcher']) {
    const c = o[k]
    if (isObj(c)) {
      m = c
      break
    }
  }

  const b = o.baseline
  const bm = isObj(b) ? (isObj(b.metrics) ? b.metrics : b) : undefined
  const cmKeys = ['confusion_matrix', 'confusion']
  const dis = first(o, ['disclaimer', 'synthetic_disclaimer', 'note'])

  return {
    threshold: num(first(o, ['threshold', 'tuned_threshold', 'overlap_threshold'])) ?? num(first(m, ['threshold'])),
    matcher: prf(m),
    matcherConfusion: confusion(first(m, cmKeys) ?? first(o, cmKeys)),
    baseline: bm ? prf(bm) : undefined,
    baselineConfusion: isObj(b) ? confusion(first(b, cmKeys) ?? (bm ? first(bm, cmKeys) : undefined)) : undefined,
    falsePositives: examples(first(o, ['false_positives', 'top_false_positives', 'fp_examples'])),
    missed: examples(first(o, ['missed_overlaps', 'false_negatives', 'misses', 'missed'])),
    disclaimer: typeof dis === 'string' ? dis : undefined,
  }
}

/** Display helper for numbers and arbitrary example values. */
export function fmtVal(v: unknown): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'number') return v.toLocaleString('en-IN', { maximumFractionDigits: 3 })
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (typeof v === 'string') return v
  if (Array.isArray(v)) return v.map(fmtVal).join(', ')
  return JSON.stringify(v)
}

export const fmtScore = (v?: number) => (v === undefined ? 'not in file' : v.toFixed(3))
