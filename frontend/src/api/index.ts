import { apiClient, useMocks } from './client'
import * as mocks from './mocks'
import type { AlertRecord, CaseDetail, CaseRecord, CopilotResponse, DashboardSummary, Institution, OverlapFlag, Page, ReportType, TrendRow, User, WorkloadRow } from '../types'

export const authApi = {
  async login(username: string, password: string): Promise<{ access_token: string; token_type: string; user?: User }> {
    if (useMocks) return mocks.mockLogin(username, password)
    const { data } = await apiClient.post('/auth/login', { username, password })
    return data
  },
  async me(): Promise<User> {
    const { data } = await apiClient.get('/auth/me')
    return data
  },
}

export interface CaseFilters {
  q?: string
  status?: string
  priority?: string
  bureau_id?: string
  institution_id?: string
  category_id?: string
  linked?: boolean
  from_date?: string
  to_date?: string
  beyond_sla?: boolean
  page?: number
  page_size?: number
}

export interface CaseCreatePayload {
  case_no: string
  institution_id: string | null
  bureau_id: string
  category_id: string
  received_on: string
  summary: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH'
  source_channel: string
  complainant_ref?: string | null
}

export const casesApi = {
  async list(filters: CaseFilters): Promise<Page<CaseRecord>> {
    if (useMocks) return mocks.mockListCases({ ...filters })
    const { data } = await apiClient.get('/cases', { params: filters })
    return data
  },
  async detail(id: string): Promise<CaseDetail> {
    if (useMocks) return mocks.mockGetCase(id)
    const { data } = await apiClient.get(`/cases/${id}`)
    return data
  },
  async create(payload: CaseCreatePayload): Promise<CaseRecord> {
    if (useMocks) throw new Error('Case creation is available with the backend API.')
    const { data } = await apiClient.post('/cases', payload)
    return data
  },
  async action(id: string, kind: string, payload: Record<string, string>): Promise<CaseRecord> {
    if (useMocks) return mocks.mockPerformCaseAction(id, kind, payload)
    const body = kind === 'action' ? { action_type: 'ACTION', ...payload } : payload
    const { data } = await apiClient.post(`/cases/${id}/${kind === 'action' ? 'actions' : kind}`, body)
    return data
  },
}

export const institutionsApi = {
  async list(q: string, page = 1, pageSize = 10): Promise<Page<Institution>> {
    if (useMocks) return mocks.mockListInstitutions(q, page, pageSize)
    const { data } = await apiClient.get('/institutions', { params: { q, page, page_size: pageSize } })
    return data
  },
  async detail(id: string): Promise<Institution> {
    if (useMocks) return mocks.mockGetInstitution(id)
    const { data } = await apiClient.get(`/institutions/${id}`)
    return data
  },
  async cases(id: string): Promise<Page<CaseRecord>> {
    if (useMocks) return mocks.mockInstitutionCases(id)
    const { data } = await apiClient.get(`/institutions/${id}/cases`, { params: { page: 1, page_size: 100 } })
    return data
  },
}

export const overlapsApi = {
  async list(tier?: string, state?: string): Promise<Page<OverlapFlag>> {
    if (useMocks) return mocks.mockListOverlaps(tier, state)
    const pageSize = 200
    const { data: first } = await apiClient.get('/overlaps', { params: { tier, state, page: 1, page_size: pageSize } })
    const items: OverlapFlag[] = [...first.items]
    const pageCount = Math.ceil(first.total / pageSize)
    for (let page = 2; page <= pageCount; page += 1) {
      const { data } = await apiClient.get('/overlaps', { params: { tier, state, page, page_size: pageSize } })
      items.push(...data.items)
    }
    return { ...first, items }
  },
  async link(id: string, leadBureauId: string, note: string) {
    if (useMocks) return mocks.mockLinkOverlap(id, { lead_bureau_id: leadBureauId, note })
    const { data } = await apiClient.post(`/overlaps/${id}/link`, { lead_bureau_id: leadBureauId, note })
    return data
  },
  async dismiss(id: string) {
    if (useMocks) return mocks.mockDismissOverlap(id)
    const { data } = await apiClient.post(`/overlaps/${id}/dismiss`)
    return data
  },
}

export const dashboardApi = {
  async summary(): Promise<DashboardSummary> {
    if (useMocks) return mocks.mockDashboardSummary()
    const { data } = await apiClient.get('/dashboard/summary')
    return data
  },
  async workload(): Promise<Page<WorkloadRow>> {
    if (useMocks) return mocks.mockWorkload()
    const { data } = await apiClient.get('/dashboard/workload')
    return data
  },
  async trend(): Promise<Page<TrendRow>> {
    if (useMocks) return mocks.mockTrend()
    const { data } = await apiClient.get('/dashboard/trend')
    return data
  },
  async ageing(): Promise<Page<{ band: string; cases: number }>> {
    if (useMocks) return mocks.mockAgeing()
    const { data } = await apiClient.get('/dashboard/ageing')
    return data
  },
  async beyondSla(): Promise<Page<CaseRecord>> {
    if (useMocks) return mocks.mockListCases({ beyond_sla: true, page: 1, page_size: 10 })
    return casesApi.list({ beyond_sla: true, page: 1, page_size: 10 })
  },
}

export const alertsApi = {
  async list(unreadOnly = false): Promise<Page<AlertRecord>> {
    if (useMocks) return mocks.mockListAlerts(unreadOnly)
    const pageSize = 200
    const { data: first } = await apiClient.get('/alerts', { params: { unread_only: unreadOnly, page: 1, page_size: pageSize } })
    const items: AlertRecord[] = [...first.items]
    const pageCount = Math.ceil(first.total / pageSize)
    for (let page = 2; page <= pageCount; page += 1) {
      const { data } = await apiClient.get('/alerts', { params: { unread_only: unreadOnly, page, page_size: pageSize } })
      items.push(...data.items)
    }
    return { ...first, items }
  },
  async markRead(id: string): Promise<AlertRecord> {
    if (useMocks) return mocks.mockMarkAlertRead(id)
    const { data } = await apiClient.post(`/alerts/${id}/read`)
    return data
  },
}

export const reportsApi = {
  async get(type: ReportType, format: 'json' | 'csv' = 'json'): Promise<{ items: Record<string, unknown>[]; total: number } | Blob> {
    if (useMocks) return mocks.mockReport(type, format)
    const { data } = await apiClient.get(`/reports/${type}`, { params: { format }, responseType: format === 'csv' ? 'blob' : 'json' })
    return data
  },
}

export const adminApi = {
  async forwardDemo(days: number) {
    const { data } = await apiClient.post('/admin/demo/forward', null, { params: { days } })
    return data as { days_forwarded: number; as_of: string; checked: number; due_soon: number; overdue: number; reminders: number; escalations: number }
  },
  async evaluation() {
    if (useMocks) return mocks.mockEvaluation()
    const { data } = await apiClient.get('/admin/evaluation')
    return data
  },
}

export const copilotApi = {
  async query(query: string): Promise<CopilotResponse> {
    const { data } = await apiClient.post('/copilot/query', { query })
    return data
  },
}
