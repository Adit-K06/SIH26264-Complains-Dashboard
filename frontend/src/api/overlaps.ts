import { api } from './client'
import { USE_MOCKS } from './config'
import type { Actor } from './caseDetailTypes'
import { mockDecide, mockQueryOverlaps } from './mocks/overlaps'
import type { LinkBody, OverlapRow } from './overlapTypes'
import type { Paged } from './types'
import { toApiParams } from '../lib/overlap'
import type { OverlapFilters } from '../lib/overlap'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

// GET /overlaps
export async function getOverlaps(f: OverlapFilters): Promise<Paged<OverlapRow>> {
  if (USE_MOCKS) {
    await delay(250)
    return mockQueryOverlaps(f)
  }
  return (await api.get<Paged<OverlapRow>>('/overlaps', { params: toApiParams(f) })).data
}

// POST /overlaps/{id}/link  (lead_bureau_id, note)
export async function linkOverlap(id: number, body: LinkBody, actor: Actor): Promise<void> {
  if (USE_MOCKS) {
    await delay(300)
    mockDecide(id, 'link', body, actor)
    return
  }
  await api.post(`/overlaps/${id}/link`, body)
}

// POST /overlaps/{id}/dismiss
export async function dismissOverlap(id: number, note: string | undefined, actor: Actor): Promise<void> {
  if (USE_MOCKS) {
    await delay(300)
    mockDecide(id, 'dismiss', { note }, actor)
    return
  }
  await api.post(`/overlaps/${id}/dismiss`, { note })
}

// POST /overlaps/scan
export async function scanOverlaps(): Promise<void> {
  if (USE_MOCKS) {
    await delay(800)
    return
  }
  await api.post('/overlaps/scan')
}
