import { api } from './client'
import { USE_MOCKS } from './config'
import { mockEvaluation } from './mocks/evaluation'
import { normalizeEvaluation } from '../lib/evaluation'
import type { EvalView } from '../lib/evaluation'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

export interface EvaluationData {
  view: EvalView
  raw: unknown // kept so the page can show the file exactly as the backend sent it
}

// GET /admin/evaluation  (serves docs/evaluation.json)
export async function getEvaluation(): Promise<EvaluationData> {
  let raw: unknown
  if (USE_MOCKS) {
    await delay(250)
    raw = mockEvaluation()
  } else {
    raw = (await api.get<unknown>('/admin/evaluation')).data
  }
  return { view: normalizeEvaluation(raw), raw }
}
