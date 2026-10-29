import { apiClient, isMockActive, useMocks, withFallback } from './client'
import * as mocks from './mocks'
import type {
  AlertRecord,
  CaseDetail,
  CaseRecord,
  CopilotResponse,
  DashboardSummary,
  Institution,
  OverlapFlag,
  Page,
  ReportType,
  TrendRow,
  User,
  WorkloadRow,
} from '../types'

export { isMockActive, useMocks }

export const authApi = {
  async login(username: string, password: string): Promise<{ access_token: string; token_type: string; user?: User }> {
    return withFallback(
      async () => {
        const { data } = await apiClient.post('/auth/login', { username, password })
        return data
      },
      () => mocks.mockLogin(username, password)
    )
  },
  async me(): Promise<User> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/auth/me')
        return data
      },
      () => mocks.mockMe()
    )
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
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/cases', { params: filters })
        return data
      },
      () => mocks.mockListCases({ ...filters })
    )
  },
  async detail(id: string): Promise<CaseDetail> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get(`/cases/${id}`)
        return data
      },
      () => mocks.mockGetCase(id)
    )
  },
  async create(payload: CaseCreatePayload): Promise<CaseRecord> {
    if (isMockActive()) throw new Error('Case creation is available with the backend API.')
    const { data } = await apiClient.post('/cases', payload)
    return data
  },
  async action(id: string, kind: string, payload: Record<string, string>): Promise<CaseRecord> {
    return withFallback(
      async () => {
        const body = kind === 'action' ? { action_type: 'ACTION', ...payload } : payload
        const { data } = await apiClient.post(`/cases/${id}/${kind === 'action' ? 'actions' : kind}`, body)
        return data
      },
      () => mocks.mockPerformCaseAction(id, kind, payload)
    )
  },
}

export const institutionsApi = {
  async list(q: string, page = 1, pageSize = 10): Promise<Page<Institution>> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/institutions', { params: { q, page, page_size: pageSize } })
        return data
      },
      () => mocks.mockListInstitutions(q, page, pageSize)
    )
  },
  async detail(id: string): Promise<Institution> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get(`/institutions/${id}`)
        return data
      },
      () => mocks.mockGetInstitution(id)
    )
  },
  async cases(id: string): Promise<Page<CaseRecord>> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get(`/institutions/${id}/cases`, { params: { page: 1, page_size: 100 } })
        return data
      },
      () => mocks.mockInstitutionCases(id)
    )
  },
}

export const overlapsApi = {
  async list(tier?: string, state?: string): Promise<Page<OverlapFlag>> {
    return withFallback(
      async () => {
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
      () => mocks.mockListOverlaps(tier, state)
    )
  },
  async link(id: string, leadBureauId: string, note: string) {
    return withFallback(
      async () => {
        const { data } = await apiClient.post(`/overlaps/${id}/link`, { lead_bureau_id: leadBureauId, note })
        return data
      },
      () => mocks.mockLinkOverlap(id, { lead_bureau_id: leadBureauId, note })
    )
  },
  async dismiss(id: string) {
    return withFallback(
      async () => {
        const { data } = await apiClient.post(`/overlaps/${id}/dismiss`)
        return data
      },
      () => mocks.mockDismissOverlap(id)
    )
  },
}

export const dashboardApi = {
  async summary(): Promise<DashboardSummary> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/dashboard/summary')
        return data
      },
      () => mocks.mockDashboardSummary()
    )
  },
  async workload(): Promise<Page<WorkloadRow>> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/dashboard/workload')
        return data
      },
      () => mocks.mockWorkload()
    )
  },
  async trend(): Promise<Page<TrendRow>> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/dashboard/trend')
        return data
      },
      () => mocks.mockTrend()
    )
  },
  async ageing(): Promise<Page<{ band: string; cases: number }>> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/dashboard/ageing')
        return data
      },
      () => mocks.mockAgeing()
    )
  },
  async beyondSla(): Promise<Page<CaseRecord>> {
    return casesApi.list({ beyond_sla: true, page: 1, page_size: 10 })
  },
}

export const alertsApi = {
  async list(unreadOnly = false): Promise<Page<AlertRecord>> {
    return withFallback(
      async () => {
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
      () => mocks.mockListAlerts(unreadOnly)
    )
  },
  async markRead(id: string): Promise<AlertRecord> {
    return withFallback(
      async () => {
        const { data } = await apiClient.post(`/alerts/${id}/read`)
        return data
      },
      () => mocks.mockMarkAlertRead(id)
    )
  },
}

export const reportsApi = {
  async get(type: ReportType, format: 'json' | 'csv' = 'json'): Promise<{ items: Record<string, unknown>[]; total: number } | Blob> {
    return withFallback(
      async () => {
        const { data } = await apiClient.get(`/reports/${type}`, { params: { format }, responseType: format === 'csv' ? 'blob' : 'json' })
        return data
      },
      () => mocks.mockReport(type, format)
    )
  },
}

export const adminApi = {
  async forwardDemo(days: number) {
    return withFallback(
      async () => {
        const { data } = await apiClient.post('/admin/demo/forward', null, { params: { days } })
        return data as { days_forwarded: number; as_of: string; checked: number; due_soon: number; overdue: number; reminders: number; escalations: number }
      },
      () => mocks.mockForwardDemo(days)
    )
  },
  async evaluation() {
    return withFallback(
      async () => {
        const { data } = await apiClient.get('/admin/evaluation')
        return data
      },
      () => mocks.mockEvaluation()
    )
  },
}

export const copilotApi = {
  async query(query: string): Promise<CopilotResponse> {
    return withFallback(
      async () => {
        const { data } = await apiClient.post('/copilot/query', { query })
        return data
      },
      () => mocks.mockCopilotQuery(query)
    )
  },
}
