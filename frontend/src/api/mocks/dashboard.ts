// Mock data lives ONLY here. All values are synthetic and invented for layout.
import type { Ageing, CaseRow, DashboardSummary, OverlapFlag, Paged, Workload } from '../types'

const monthly: Array<[string, number, number]> = [
  ['2025-11', 310, 240],
  ['2025-12', 335, 262],
  ['2026-01', 352, 301],
  ['2026-02', 344, 318],
  ['2026-03', 371, 330],
  ['2026-04', 366, 352],
  ['2026-05', 390, 361],
  ['2026-06', 402, 377],
  ['2026-07', 398, 384],
  ['2026-08', 415, 391],
  ['2026-09', 421, 402],
  ['2026-10', 276, 199],
]

export const mockSummary: DashboardSummary = {
  total: 6000,
  by_status: {
    PENDING: 812,
    UNDER_PROCESS: 1940,
    DISPOSED: 2950,
    TRANSFERRED: 190,
    ESCALATED: 108,
  },
  beyond_sla: 143,
  open_overlaps: 37,
  confirmed_groups: 21,
  monthly: monthly.map(([month, received, disposed]) => ({ month, received, disposed })),
}

export const mockWorkload: Workload = {
  items: [
    { bureau: 'RB', counts: { PENDING: 210, UNDER_PROCESS: 520, DISPOSED: 760, TRANSFERRED: 40, ESCALATED: 30 } },
    { bureau: 'PGRC', counts: { PENDING: 260, UNDER_PROCESS: 610, DISPOSED: 980, TRANSFERRED: 70, ESCALATED: 41 } },
    { bureau: 'APPROVAL', counts: { PENDING: 150, UNDER_PROCESS: 340, DISPOSED: 520, TRANSFERRED: 30, ESCALATED: 18 } },
    { bureau: 'ACADEMIC', counts: { PENDING: 120, UNDER_PROCESS: 290, DISPOSED: 410, TRANSFERRED: 28, ESCALATED: 12 } },
    { bureau: 'FINANCE', counts: { PENDING: 72, UNDER_PROCESS: 180, DISPOSED: 280, TRANSFERRED: 22, ESCALATED: 7 } },
  ],
}

export const mockAgeing: Ageing = {
  items: [
    { bucket: '0-7', count: 540 },
    { bucket: '8-15', count: 612 },
    { bucket: '16-30', count: 905 },
    { bucket: '31-60', count: 640 },
    { bucket: '60+', count: 353 },
  ],
}

const bureaus = ['RB', 'PGRC', 'APPROVAL', 'ACADEMIC', 'FINANCE']
const statuses = ['UNDER_PROCESS', 'PENDING', 'ESCALATED'] as const

export const mockBeyondSla: Paged<CaseRow> = {
  items: Array.from({ length: 8 }, (_, i): CaseRow => {
    const due = new Date()
    due.setDate(due.getDate() - (3 + i * 4))
    return {
      id: 1000 + i,
      case_no: `${bureaus[i % 5]}/2026/${String(1800 + i * 37).padStart(6, '0')}`,
      institution_name: `Synthetic Institute of Technology ${i + 1}`,
      bureau_code: bureaus[i % 5],
      status: statuses[i % 3],
      priority: i % 3 === 0 ? 'HIGH' : 'MEDIUM',
      expected_disposal_on: due.toISOString().slice(0, 10),
    }
  }),
  total: 143,
  page: 1,
  page_size: 8,
}

export const mockOverlaps: Paged<OverlapFlag> = {
  items: [
    {
      id: 1,
      institution_id: 20381,
      institution_name: 'Synthetic College of Engineering 12',
      tier: 'B',
      score: 0.86,
      reasons: ['HIGH_TEXT_SIMILARITY', 'SAME_CATEGORY', 'WITHIN_30_DAYS', 'DIFFERENT_BUREAU'],
      state: 'OPEN',
    },
    {
      id: 2,
      institution_id: 10977,
      institution_name: 'Synthetic Institute of Management 7',
      tier: 'B',
      score: 0.74,
      reasons: ['SAME_CATEGORY', 'HIGH_TEXT_SIMILARITY', 'DIFFERENT_BUREAU'],
      state: 'OPEN',
    },
    {
      id: 3,
      institution_id: 33102,
      institution_name: 'Synthetic Polytechnic 31',
      tier: 'A',
      score: null,
      reasons: ['DIFFERENT_BUREAU'],
      state: 'OPEN',
    },
    {
      id: 4,
      institution_id: 44120,
      institution_name: 'Synthetic University of Technology 4',
      tier: 'B',
      score: 0.68,
      reasons: ['SHARED_COMPLAINANT_REF', 'WITHIN_30_DAYS', 'DIFFERENT_BUREAU'],
      state: 'OPEN',
    },
  ],
  total: 37,
  page: 1,
  page_size: 5,
}
