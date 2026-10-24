import { api } from './client'
import type { Ageing, CaseRow, DashboardSummary, OverlapFlag, Paged, Workload } from './types'
import {
  mockAgeing,
  mockBeyondSla,
  mockOverlaps,
  mockSummary,
  mockWorkload,
} from './mocks/dashboard'

// Mocks are ON by default in `npm run dev`; set VITE_USE_MOCKS=false to use the real API.
// A production build can never use mocks.
const USE_MOCKS = import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS !== 'false'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))
async function mock<T>(data: T): Promise<T> {
  await delay(350) // lets you see the loading skeletons
  return data
}

export async function getSummary(): Promise<DashboardSummary> {
  if (USE_MOCKS) return mock(mockSummary)
  return (await api.get<DashboardSummary>('/dashboard/summary')).data
}

export async function getWorkload(): Promise<Workload> {
  if (USE_MOCKS) return mock(mockWorkload)
  return (await api.get<Workload>('/dashboard/workload')).data
}

export async function getAgeing(): Promise<Ageing> {
  if (USE_MOCKS) return mock(mockAgeing)
  return (await api.get<Ageing>('/dashboard/ageing')).data
}

// beyond_sla = expected_disposal_on < today AND case is open (AGENTS.md)
export async function getBeyondSla(): Promise<Paged<CaseRow>> {
  if (USE_MOCKS) return mock(mockBeyondSla)
  return (
    await api.get<Paged<CaseRow>>('/cases', { params: { beyond_sla: true, page_size: 8 } })
  ).data
}

export async function getOpenOverlaps(): Promise<Paged<OverlapFlag>> {
  if (USE_MOCKS) return mock(mockOverlaps)
  return (
    await api.get<Paged<OverlapFlag>>('/overlaps', { params: { state: 'OPEN', page_size: 5 } })
  ).data
}
