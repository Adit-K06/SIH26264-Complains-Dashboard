import { api } from './client'
import { USE_MOCKS } from './config'
import { mockQueryCases } from './mocks/cases'
import type { CaseRow, Paged } from './types'
import { toApiParams } from '../lib/caseFilters'
import type { CaseFilters } from '../lib/caseFilters'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

// GET /cases  (filters per AGENTS.md; response is {items,total,page,page_size})
export async function getCases(filters: CaseFilters): Promise<Paged<CaseRow>> {
  if (USE_MOCKS) {
    await delay(250)
    return mockQueryCases(filters)
  }
  return (await api.get<Paged<CaseRow>>('/cases', { params: toApiParams(filters) })).data
}
