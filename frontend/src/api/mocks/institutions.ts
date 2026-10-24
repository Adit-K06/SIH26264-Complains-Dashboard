// Mock data lives ONLY in src/api/mocks. 60 SYNTHETIC institutions whose names and ids match the
// institution names used by the mock cases (see mocks/cases.ts), so the two pages stay consistent.
import { parseFilters } from '../../lib/caseFilters'
import type { InstitutionFilters } from '../../lib/institution'
import { REGIONS } from '../../lib/lookups'
import type { Institution } from '../institutionTypes'
import type { CaseRow, Paged } from '../types'
import { mockQueryCases } from './cases'

const TYPES = ['College of Engineering', 'Institute of Technology', 'Polytechnic', 'Institute of Management']

let cache: Institution[] | null = null

function build(): Institution[] {
  const cases = mockQueryCases({ ...parseFilters(new URLSearchParams()), page: 1, page_size: 1000 }).items
  const total = new Map<number, number>()
  const open = new Map<number, number>()
  for (const c of cases) {
    if (c.institution_id == null) continue
    total.set(c.institution_id, (total.get(c.institution_id) ?? 0) + 1)
    if (c.status !== 'DISPOSED') open.set(c.institution_id, (open.get(c.institution_id) ?? 0) + 1)
  }
  const out: Institution[] = []
  for (let id = 1; id <= 60; id++) {
    const region = REGIONS[(id - 1) % REGIONS.length]
    out.push({
      id,
      aicte_permanent_id: `SYN-${String(10000 + id).padStart(5, '0')}`,
      name: `Synthetic ${TYPES[id % TYPES.length]} ${id}`,
      address: `${id} Synthetic Road (demo data)`,
      district: `Synthetic District ${(id % 12) + 1}`,
      state: `Synthetic State ${(id % 9) + 1}`,
      region_id: region.id,
      region_name: region.label,
      type: TYPES[id % TYPES.length],
      status: 'ACTIVE',
      total_cases: total.get(id) ?? 0,
      open_cases: open.get(id) ?? 0,
    })
  }
  return out
}

function all(): Institution[] {
  if (!cache) cache = build()
  return cache
}

export function mockQueryInstitutions(f: InstitutionFilters): Paged<Institution> {
  const q = f.q.trim().toLowerCase()
  const rows = all().filter((i) => {
    if (q && !`${i.name} ${i.aicte_permanent_id}`.toLowerCase().includes(q)) return false
    if (f.region_id && i.region_id !== f.region_id) return false
    return true
  })
  const start = (f.page - 1) * f.page_size
  return { items: rows.slice(start, start + f.page_size), total: rows.length, page: f.page, page_size: f.page_size }
}

export function mockGetInstitution(id: number): Institution {
  const i = all().find((x) => x.id === id)
  if (!i) throw new Error('Institution not found')
  return i
}

export function mockInstitutionCases(id: number): Paged<CaseRow> {
  mockGetInstitution(id)
  return mockQueryCases({ ...parseFilters(new URLSearchParams()), institution_id: id, page: 1, page_size: 1000 })
}
