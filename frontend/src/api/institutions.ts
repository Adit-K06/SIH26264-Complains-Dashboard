import { api } from './client'
import { USE_MOCKS } from './config'
import type { Institution } from './institutionTypes'
import {
  mockGetInstitution,
  mockInstitutionCases,
  mockQueryInstitutions,
} from './mocks/institutions'
import { mockQueryOverlaps } from './mocks/overlaps'
import type { OverlapRow } from './overlapTypes'
import type { CaseRow, Paged } from './types'
import { toApiParams } from '../lib/institution'
import type { InstitutionFilters } from '../lib/institution'
import { OVERLAP_STATES } from '../lib/overlap'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

// GET /institutions
export async function getInstitutions(f: InstitutionFilters): Promise<Paged<Institution>> {
  if (USE_MOCKS) {
    await delay(250)
    return mockQueryInstitutions(f)
  }
  return (await api.get<Paged<Institution>>('/institutions', { params: toApiParams(f) })).data
}

// GET /institutions/{id}
export async function getInstitution(id: number): Promise<Institution> {
  if (USE_MOCKS) {
    await delay(200)
    return mockGetInstitution(id)
  }
  return (await api.get<Institution>(`/institutions/${id}`)).data
}

// GET /institutions/{id}/cases
export async function getInstitutionCases(id: number): Promise<Paged<CaseRow>> {
  if (USE_MOCKS) {
    await delay(250)
    return mockInstitutionCases(id)
  }
  return (await api.get<Paged<CaseRow>>(`/institutions/${id}/cases`, { params: { page_size: 200 } })).data
}

// GET /overlaps?institution_id=  (assumed filter, all states)
export async function getInstitutionOverlaps(id: number): Promise<OverlapRow[]> {
  if (USE_MOCKS) {
    await delay(250)
    const out: OverlapRow[] = []
    for (const state of OVERLAP_STATES) {
      out.push(
        ...mockQueryOverlaps({ state, tier: '', page: 1, page_size: 1000 }).items.filter(
          (r) => r.institution_id === id,
        ),
      )
    }
    return out
  }
  return (await api.get<Paged<OverlapRow>>('/overlaps', { params: { institution_id: id, page_size: 100 } })).data
    .items
}
