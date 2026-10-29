export type Role = 'ADMIN' | 'SENIOR_MGMT' | 'BUREAU_OFFICER' | 'REGIONAL_OFFICER'
export type CaseStatus = 'PENDING' | 'UNDER_PROCESS' | 'DISPOSED' | 'TRANSFERRED' | 'ESCALATED'

export interface User {
  id: string
  name: string
  email: string
  role: Role
  bureau_id?: string | null
  region_id?: string | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface CaseRecord {
  id: string
  case_no: string
  institution_id: string | null
  institution_name?: string | null
  aicte_permanent_id?: string | null
  bureau_id: string
  bureau_code?: string
  bureau_name?: string
  category_id: string
  category_name?: string
  region_id?: string | null
  status: CaseStatus
  received_on: string
  last_action_on?: string | null
  last_action_text?: string | null
  next_action_text?: string | null
  expected_disposal_on?: string | null
  priority: 'LOW' | 'MEDIUM' | 'HIGH'
  summary: string
  complainant_ref?: string | null
  source_channel: string
  source: string
  hard_deadline_on?: string | null
  hard_deadline_type?: string
  link_group_id?: string | null
  needs_institution_review?: boolean
  assigned_officer_name?: string | null
}

export interface CaseActionRecord {
  id: string
  case_id: string
  action_type: string
  action_tag?: string | null
  from_status?: string | null
  to_status?: string | null
  remarks?: string | null
  created_at: string
  actor_name?: string | null
  bureau_code?: string | null
}

export interface CaseDetail extends CaseRecord {
  actions: CaseActionRecord[]
  institution?: Institution | null
}

export interface Institution {
  id: string
  aicte_permanent_id: string
  name: string
  address?: string | null
  district?: string | null
  state?: string | null
  region_id?: string | null
  region_name?: string | null
  type?: string | null
  status?: string | null
  source: string
}

export interface OverlapCase {
  id: string
  case_no: string
  bureau_id: string
  bureau_code?: string | null
  category_id: string
  status: CaseStatus
  received_on: string
  summary?: string | null
  complainant_ref?: string | null
}

export interface OverlapFlag {
  id: string
  institution_id: string
  institution_name?: string | null
  tier: 'A' | 'B'
  score?: number | null
  reasons: string[]
  state: 'OPEN' | 'CONFIRMED' | 'DISMISSED'
  created_at?: string | null
  decided_at?: string | null
  cases: OverlapCase[]
}

export interface AlertRecord {
  id: string
  type: string
  case_id?: string | null
  institution_id?: string | null
  target_role?: string | null
  target_bureau_id?: string | null
  message: string
  due_on?: string | null
  created_at: string
  read_at?: string | null
}

export interface DashboardSummary {
  total_cases: number
  open_cases: number
  disposed_cases: number
  status_counts: Record<string, number>
  open_overlaps: number
  unread_alerts: number
}

export interface WorkloadRow {
  bureau_id: string
  bureau_code: string
  bureau_name: string
  total_cases: number
  open_cases: number
  status_counts: Record<string, number>
}

export interface TrendRow {
  month: string
  received: number
  disposed: number
}

export type ReportType =
  | 'bureau'
  | 'region'
  | 'institution'
  | 'ageing'
  | 'disposal-rate'
  | 'status'
  | 'overlaps'
  | 'monthly'

export interface CopilotItem {
  id: string
  title: string
  subtitle?: string | null
  status?: string | null
  link: string
}

export interface CopilotAction {
  label: string
  link: string
}

export interface CopilotResponse {
  query: string
  intent: string
  answer: string
  highlight?: string | null
  items: CopilotItem[]
  action?: CopilotAction | null
  suggestions: string[]
}
