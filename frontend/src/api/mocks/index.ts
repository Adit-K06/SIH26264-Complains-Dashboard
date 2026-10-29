import type {
  AlertRecord,
  CaseActionRecord,
  CaseDetail,
  CaseRecord,
  CaseStatus,
  CopilotResponse,
  DashboardSummary,
  Institution,
  OverlapFlag,
  Page,
  ReportType,
  TrendRow,
  User,
  WorkloadRow,
} from '../../types'

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const bureauRows = [
  { id: 'bureau-rb', code: 'RB', name: 'Regional Bureau' },
  { id: 'bureau-pgrc', code: 'PGRC', name: 'Public Grievance Redressal Cell' },
  { id: 'bureau-approval', code: 'APPROVAL', name: 'Approval Bureau' },
  { id: 'bureau-academic', code: 'ACADEMIC', name: 'Academic Bureau' },
  { id: 'bureau-finance', code: 'FINANCE', name: 'Finance Bureau' },
]

const institutionRows: Institution[] = [
  { id: 'inst-1', aicte_permanent_id: 'SYN-00001', name: 'Synthetic Aster Institute of Engineering', address: 'Demo Campus 1', district: 'Demo District North', state: 'North', region_id: 'region-north', region_name: 'North', type: 'Engineering Institute', status: 'ACTIVE', source: 'SYNTHETIC' },
  { id: 'inst-2', aicte_permanent_id: 'SYN-00002', name: 'Synthetic Blue Cedar College of Applied Technology', address: 'Demo Campus 2', district: 'Demo District South', state: 'South', region_id: 'region-south', region_name: 'South', type: 'Technology College', status: 'ACTIVE', source: 'SYNTHETIC' },
  { id: 'inst-3', aicte_permanent_id: 'SYN-00003', name: 'Synthetic Cobalt Technical University', address: 'Demo Campus 3', district: 'Demo District East', state: 'East', region_id: 'region-east', region_name: 'East', type: 'Technical University', status: 'ACTIVE', source: 'SYNTHETIC' },
  { id: 'inst-4', aicte_permanent_id: 'SYN-00004', name: 'Synthetic Dawnridge Polytechnic Institute', address: 'Demo Campus 4', district: 'Demo District West', state: 'West', region_id: 'region-west', region_name: 'West', type: 'Polytechnic Institute', status: 'ACTIVE', source: 'SYNTHETIC' },
  { id: 'inst-5', aicte_permanent_id: 'SYN-00005', name: 'Synthetic Evergreen College of Engineering', address: 'Demo Campus 5', district: 'Demo District Central', state: 'Central', region_id: 'region-central', region_name: 'Central', type: 'Engineering College', status: 'ACTIVE', source: 'SYNTHETIC' },
]

const byId = (id: string) => institutionRows.find((institution) => institution.id === id)

const caseRows: CaseRecord[] = [
  { id: 'case-001', case_no: 'RB-2026-00001', institution_id: 'inst-1', institution_name: institutionRows[0].name, aicte_permanent_id: institutionRows[0].aicte_permanent_id, bureau_id: 'bureau-rb', bureau_code: 'RB', bureau_name: 'Regional Bureau', category_id: 'cat-scholarship', category_name: 'Scholarships', region_id: 'region-north', status: 'PENDING', received_on: '2026-10-01', last_action_on: '2026-10-01T08:00:00Z', last_action_text: 'Synthetic complaint recorded.', next_action_text: 'Review submitted scholarship records.', expected_disposal_on: '2026-10-31', priority: 'HIGH', summary: 'Students reported delayed merit scholarship payments for the current academic year.', complainant_ref: 'SYN-CMP-0001', source_channel: 'DIRECT', source: 'SYNTHETIC', hard_deadline_type: 'NONE', link_group_id: 'group-01', needs_institution_review: false, assigned_officer_name: 'R. Sharma' },
  { id: 'case-002', case_no: 'PGRC-2026-00001', institution_id: 'inst-1', institution_name: institutionRows[0].name, aicte_permanent_id: institutionRows[0].aicte_permanent_id, bureau_id: 'bureau-pgrc', bureau_code: 'PGRC', bureau_name: 'Public Grievance Redressal Cell', category_id: 'cat-scholarship', category_name: 'Scholarships', region_id: 'region-north', status: 'UNDER_PROCESS', received_on: '2026-10-05', last_action_on: '2026-10-12T09:30:00Z', last_action_text: 'Initial review started.', next_action_text: 'Coordinate with the Regional Bureau.', expected_disposal_on: '2026-11-04', priority: 'MEDIUM', summary: 'A complaint says merit scholarship funds for this academic year remain pending.', complainant_ref: 'SYN-CMP-0001', source_channel: 'CPGRAMS', source: 'SYNTHETIC', hard_deadline_type: 'NONE', link_group_id: 'group-01', needs_institution_review: false, assigned_officer_name: 'P. Iyer' },
  { id: 'case-003', case_no: 'RB-2026-00002', institution_id: 'inst-2', institution_name: institutionRows[1].name, aicte_permanent_id: institutionRows[1].aicte_permanent_id, bureau_id: 'bureau-rb', bureau_code: 'RB', bureau_name: 'Regional Bureau', category_id: 'cat-exam', category_name: 'Examination Services', region_id: 'region-south', status: 'UNDER_PROCESS', received_on: '2026-09-22', last_action_on: '2026-10-20T11:10:00Z', last_action_text: 'Requested supporting result sheets.', next_action_text: 'Review the institution reply.', expected_disposal_on: '2026-10-22', priority: 'HIGH', summary: 'Students requested correction of examination results for the recent semester.', complainant_ref: 'SYN-CMP-0002', source_channel: 'DIRECT', source: 'SYNTHETIC', hard_deadline_type: 'NONE', needs_institution_review: false, assigned_officer_name: 'R. Sharma' },
  { id: 'case-004', case_no: 'APPROVAL-2026-00001', institution_id: 'inst-3', institution_name: institutionRows[2].name, aicte_permanent_id: institutionRows[2].aicte_permanent_id, bureau_id: 'bureau-approval', bureau_code: 'APPROVAL', bureau_name: 'Approval Bureau', category_id: 'cat-approval', category_name: 'Approval Process', region_id: 'region-east', status: 'PENDING', received_on: '2026-10-18', last_action_on: '2026-10-18T08:00:00Z', last_action_text: 'Synthetic complaint recorded.', next_action_text: 'Check the pending application status.', expected_disposal_on: '2026-11-17', priority: 'MEDIUM', summary: 'The institution requested a status update on its pending approval application.', complainant_ref: 'SYN-CMP-0003', source_channel: 'API', source: 'SYNTHETIC', hard_deadline_type: 'NONE', needs_institution_review: true, assigned_officer_name: 'A. Khan' },
  { id: 'case-005', case_no: 'PGRC-2026-00002', institution_id: 'inst-4', institution_name: institutionRows[3].name, aicte_permanent_id: institutionRows[3].aicte_permanent_id, bureau_id: 'bureau-pgrc', bureau_code: 'PGRC', bureau_name: 'Public Grievance Redressal Cell', category_id: 'cat-faculty', category_name: 'Faculty', region_id: 'region-west', status: 'ESCALATED', received_on: '2026-08-12', last_action_on: '2026-10-25T12:00:00Z', last_action_text: 'Escalated for review.', next_action_text: 'Senior review required.', expected_disposal_on: '2026-09-11', priority: 'HIGH', summary: 'A complaint asks the bureau to review reported teaching vacancies in a programme.', complainant_ref: 'SYN-CMP-0004', source_channel: 'CPGRAMS', source: 'SYNTHETIC', hard_deadline_type: 'NONE', needs_institution_review: false, assigned_officer_name: 'P. Iyer' },
  { id: 'case-006', case_no: 'FINANCE-2026-00001', institution_id: 'inst-5', institution_name: institutionRows[4].name, aicte_permanent_id: institutionRows[4].aicte_permanent_id, bureau_id: 'bureau-finance', bureau_code: 'FINANCE', bureau_name: 'Finance Bureau', category_id: 'cat-scholarship', category_name: 'Scholarships', region_id: 'region-central', status: 'DISPOSED', received_on: '2026-06-03', last_action_on: '2026-06-21T12:00:00Z', last_action_text: 'Disposed in synthetic demo history.', next_action_text: null, expected_disposal_on: '2026-07-03', priority: 'LOW', summary: 'A synthetic scholarship payment question was reviewed and disposed.', complainant_ref: null, source_channel: 'CSV_IMPORT', source: 'SYNTHETIC', hard_deadline_type: 'NONE', needs_institution_review: false, assigned_officer_name: 'A. Khan' },
  { id: 'case-007', case_no: 'RB-2026-00003', institution_id: 'inst-1', institution_name: institutionRows[0].name, aicte_permanent_id: institutionRows[0].aicte_permanent_id, bureau_id: 'bureau-rb', bureau_code: 'RB', bureau_name: 'Regional Bureau', category_id: 'cat-admission', category_name: 'Admissions', region_id: 'region-north', status: 'TRANSFERRED', received_on: '2026-09-03', last_action_on: '2026-09-05T10:00:00Z', last_action_text: 'Transferred for synthetic coordination.', next_action_text: 'Await acknowledgement.', expected_disposal_on: '2026-10-03', priority: 'MEDIUM', summary: 'Applicants requested a review of a synthetic admission fee schedule.', complainant_ref: null, source_channel: 'DIRECT', source: 'SYNTHETIC', hard_deadline_type: 'NONE', needs_institution_review: false, assigned_officer_name: 'R. Sharma' },
  { id: 'case-008', case_no: 'ACADEMIC-2026-00001', institution_id: null, institution_name: null, bureau_id: 'bureau-academic', bureau_code: 'ACADEMIC', bureau_name: 'Academic Bureau', category_id: 'cat-infrastructure', category_name: 'Infrastructure', region_id: null, status: 'PENDING', received_on: '2026-10-27', last_action_on: '2026-10-27T08:00:00Z', last_action_text: 'Synthetic complaint recorded.', next_action_text: 'Initial screening.', expected_disposal_on: '2026-11-26', priority: 'LOW', summary: 'A synthetic request for campus maintenance review.', complainant_ref: null, source_channel: 'DIRECT', source: 'SYNTHETIC', hard_deadline_type: 'NONE', needs_institution_review: true, assigned_officer_name: 'A. Khan' },
  { id: 'case-009', case_no: 'PGRC-2026-00003', institution_id: 'inst-2', institution_name: institutionRows[1].name, aicte_permanent_id: institutionRows[1].aicte_permanent_id, bureau_id: 'bureau-pgrc', bureau_code: 'PGRC', bureau_name: 'Public Grievance Redressal Cell', category_id: 'cat-infrastructure', category_name: 'Infrastructure', region_id: 'region-south', status: 'PENDING', received_on: '2026-10-24', last_action_on: '2026-10-24T08:00:00Z', last_action_text: 'Synthetic complaint recorded.', next_action_text: 'Review the submitted details.', expected_disposal_on: '2026-11-23', priority: 'MEDIUM', summary: 'A synthetic campus safety concern was submitted for review.', complainant_ref: null, source_channel: 'RTI', source: 'SYNTHETIC', hard_deadline_type: 'NONE', needs_institution_review: false, assigned_officer_name: 'P. Iyer' },
  { id: 'case-010', case_no: 'RB-2026-00004', institution_id: 'inst-3', institution_name: institutionRows[2].name, aicte_permanent_id: institutionRows[2].aicte_permanent_id, bureau_id: 'bureau-rb', bureau_code: 'RB', bureau_name: 'Regional Bureau', category_id: 'cat-faculty', category_name: 'Faculty', region_id: 'region-east', status: 'PENDING', received_on: '2026-10-11', last_action_on: '2026-10-11T08:00:00Z', last_action_text: 'Synthetic complaint recorded.', next_action_text: 'Review faculty records.', expected_disposal_on: '2026-11-10', priority: 'HIGH', summary: 'Students reported unfilled teaching posts in a programme and requested review.', complainant_ref: 'SYN-CMP-0010', source_channel: 'DIRECT', source: 'SYNTHETIC', hard_deadline_type: 'NONE', link_group_id: 'group-10', needs_institution_review: false, assigned_officer_name: 'R. Sharma' },
]

const actionRows = new Map<string, CaseActionRecord[]>(caseRows.map((item) => [item.id, [
  { id: `action-${item.id}`, case_id: item.id, action_type: 'CREATED', from_status: null, to_status: 'PENDING', remarks: 'Synthetic case created.', created_at: `${item.received_on}T08:00:00Z`, actor_name: item.assigned_officer_name ?? 'System', bureau_code: item.bureau_code },
  ...(item.last_action_text && item.last_action_text !== 'Synthetic case created.' ? [{ id: `action-last-${item.id}`, case_id: item.id, action_type: item.status === 'ESCALATED' ? 'ESCALATED' : item.status === 'DISPOSED' ? 'DISPOSED' : 'ACTION', from_status: null, to_status: item.status, remarks: item.last_action_text, created_at: item.last_action_on ?? `${item.received_on}T08:00:00Z`, actor_name: item.assigned_officer_name ?? 'System', bureau_code: item.bureau_code }] : []),
]]))

const overlapRows: OverlapFlag[] = [
  { id: 'overlap-a-1', institution_id: 'inst-1', institution_name: institutionRows[0].name, tier: 'A', score: null, reasons: ['DIFFERENT_BUREAU'], state: 'OPEN', created_at: '2026-10-12T09:00:00Z', cases: [caseRows[0], caseRows[1]].map((item) => ({ id: item.id, case_no: item.case_no, bureau_id: item.bureau_id, bureau_code: item.bureau_code, category_id: item.category_id, status: item.status, received_on: item.received_on, summary: item.summary, complainant_ref: item.complainant_ref })) },
  { id: 'overlap-b-1', institution_id: 'inst-1', institution_name: institutionRows[0].name, tier: 'B', score: null, reasons: ['HIGH_TEXT_SIMILARITY', 'SAME_CATEGORY', 'WITHIN_30_DAYS', 'SHARED_REFERENCE', 'DIFFERENT_BUREAU'], state: 'OPEN', created_at: '2026-10-12T09:00:00Z', cases: [caseRows[0], caseRows[1]].map((item) => ({ id: item.id, case_no: item.case_no, bureau_id: item.bureau_id, bureau_code: item.bureau_code, category_id: item.category_id, status: item.status, received_on: item.received_on, summary: item.summary, complainant_ref: item.complainant_ref })) },
]

const alertRows: AlertRecord[] = [
  { id: 'alert-1', type: 'DUE_SOON', case_id: 'case-001', institution_id: 'inst-1', target_bureau_id: 'bureau-rb', message: 'SLA placeholder: this case is approaching its expected disposal date.', due_on: '2026-10-31', created_at: '2026-10-29T08:00:00Z', read_at: null },
  { id: 'alert-2', type: 'OVERDUE', case_id: 'case-003', institution_id: 'inst-2', target_bureau_id: 'bureau-rb', message: 'SLA placeholder: this case is past its expected disposal date.', due_on: '2026-10-22', created_at: '2026-10-29T08:00:00Z', read_at: null },
  { id: 'alert-3', type: 'OVERLAP', case_id: null, institution_id: 'inst-1', message: 'Potential overlapping cases need coordination.', due_on: null, created_at: '2026-10-29T08:00:00Z', read_at: '2026-10-29T09:00:00Z' },
]

const demoUsers: Record<string, User> = {
  admin: { id: 'user-admin', name: 'Demo Administrator', email: 'admin@demo.aicte.invalid', role: 'ADMIN' },
  senior: { id: 'user-senior', name: 'Demo Senior Manager', email: 'senior@demo.aicte.invalid', role: 'SENIOR_MGMT' },
  rb_officer: { id: 'user-rb', name: 'Demo RB Officer', email: 'rb_officer@demo.aicte.invalid', role: 'BUREAU_OFFICER', bureau_id: 'bureau-rb' },
  pgrc_officer: { id: 'user-pgrc', name: 'Demo PGRC Officer', email: 'pgrc_officer@demo.aicte.invalid', role: 'BUREAU_OFFICER', bureau_id: 'bureau-pgrc' },
  regional_north: { id: 'user-north', name: 'Demo North Regional Officer', email: 'regional_north@demo.aicte.invalid', role: 'REGIONAL_OFFICER', region_id: 'region-north' },
}

export async function mockLogin(username: string, password: string) {
  const loginName = username.trim().toLowerCase().split('@')[0]
  const user = demoUsers[loginName]
  if (!user || password !== 'Demo@12345') throw new Error('Username or password is incorrect.')
  return { access_token: `mock.${user.id}`, token_type: 'bearer', user: clone(user) }
}

export async function mockListCases(params: Record<string, string | number | boolean | undefined>): Promise<Page<CaseRecord>> {
  const q = String(params.q ?? '').trim().toLowerCase()
  const filtered = caseRows.filter((item) => {
    if (q && ![item.case_no, item.institution_name, item.summary, item.aicte_permanent_id].some((value) => value?.toLowerCase().includes(q))) return false
    if (params.status && item.status !== params.status) return false
    if (params.priority && item.priority !== params.priority) return false
    if (params.bureau_id && item.bureau_id !== params.bureau_id) return false
    if (params.institution_id && item.institution_id !== params.institution_id) return false
    if (params.category_id && item.category_id !== params.category_id) return false
    if (params.linked === true && !item.link_group_id) return false
    if (params.linked === false && item.link_group_id) return false
    if (params.from_date && item.received_on < String(params.from_date)) return false
    if (params.to_date && item.received_on > String(params.to_date)) return false
    if (params.beyond_sla) {
      const today = new Date().toISOString().slice(0, 10)
      if (item.status === 'DISPOSED' || !item.expected_disposal_on || item.expected_disposal_on >= today) return false
    }
    return true
  }).sort((a, b) => b.received_on.localeCompare(a.received_on))
  const page = Number(params.page ?? 1)
  const pageSize = Number(params.page_size ?? 10)
  return clone({ items: filtered.slice((page - 1) * pageSize, page * pageSize), total: filtered.length, page, page_size: pageSize })
}

export async function mockGetCase(id: string): Promise<CaseDetail> {
  const record = caseRows.find((item) => item.id === id || item.case_no === id)
  if (!record) throw new Error('Case was not found.')
  return clone({ ...record, actions: actionRows.get(record.id) ?? [], institution: record.institution_id ? byId(record.institution_id) ?? null : null })
}

export async function mockPerformCaseAction(id: string, kind: string, payload: Record<string, string>) {
  const record = caseRows.find((item) => item.id === id)
  if (!record) throw new Error('Case was not found.')
  const now = new Date().toISOString()
  const statusByKind: Record<string, CaseStatus> = { transfer: 'TRANSFERRED', escalate: 'ESCALATED', dispose: 'DISPOSED', reopen: 'PENDING' }
  const nextStatus = statusByKind[kind]
  const action: CaseActionRecord = { id: `action-${Date.now()}`, case_id: record.id, action_type: kind === 'action' ? 'ACTION' : kind.toUpperCase(), from_status: record.status, to_status: nextStatus ?? record.status, remarks: payload.remarks, created_at: now, actor_name: 'Demo Officer', bureau_code: record.bureau_code }
  if (nextStatus) record.status = nextStatus
  record.last_action_on = now
  record.last_action_text = payload.remarks
  if (kind === 'transfer' && payload.to_bureau_id) record.bureau_id = payload.to_bureau_id
  actionRows.set(record.id, [action, ...(actionRows.get(record.id) ?? [])])
  return clone(record)
}

export async function mockListInstitutions(q: string, page: number, pageSize: number): Promise<Page<Institution>> {
  const normalized = q.trim().toLowerCase()
  const filtered = institutionRows.filter((item) => !normalized || `${item.name} ${item.aicte_permanent_id} ${item.state}`.toLowerCase().includes(normalized))
  return clone({ items: filtered.slice((page - 1) * pageSize, page * pageSize), total: filtered.length, page, page_size: pageSize })
}

export async function mockGetInstitution(id: string): Promise<Institution> {
  const institution = byId(id) ?? institutionRows.find((item) => item.aicte_permanent_id === id)
  if (!institution) throw new Error('Institution was not found.')
  return clone(institution)
}

export async function mockInstitutionCases(id: string): Promise<Page<CaseRecord>> {
  const items = caseRows.filter((item) => item.institution_id === id || item.aicte_permanent_id === id)
  return clone({ items, total: items.length, page: 1, page_size: items.length })
}

export async function mockListOverlaps(tier?: string, state?: string): Promise<Page<OverlapFlag>> {
  const items = overlapRows.filter((item) => (!tier || item.tier === tier) && (!state || item.state === state))
  return clone({ items, total: items.length, page: 1, page_size: items.length })
}

export async function mockLinkOverlap(id: string, payload: { lead_bureau_id: string; note: string }) {
  void payload
  const flag = overlapRows.find((item) => item.id === id)
  if (!flag) throw new Error('Overlap flag was not found.')
  flag.state = 'CONFIRMED'
  flag.decided_at = new Date().toISOString()
  return { id, state: flag.state, group_id: 'group-linked-demo' }
}

export async function mockDismissOverlap(id: string) {
  const flag = overlapRows.find((item) => item.id === id)
  if (!flag) throw new Error('Overlap flag was not found.')
  flag.state = 'DISMISSED'
  flag.decided_at = new Date().toISOString()
  return { id, state: flag.state, decided_at: flag.decided_at }
}

export async function mockDashboardSummary(): Promise<DashboardSummary> {
  const statusCounts = Object.fromEntries(['PENDING', 'UNDER_PROCESS', 'DISPOSED', 'TRANSFERRED', 'ESCALATED'].map((status) => [status, caseRows.filter((item) => item.status === status).length]))
  return { total_cases: caseRows.length, open_cases: caseRows.filter((item) => item.status !== 'DISPOSED').length, disposed_cases: statusCounts.DISPOSED, status_counts: statusCounts, open_overlaps: overlapRows.filter((item) => item.state === 'OPEN').length, unread_alerts: alertRows.filter((item) => !item.read_at).length }
}

export async function mockWorkload(): Promise<Page<WorkloadRow>> {
  const items = bureauRows.map((bureau) => {
    const cases = caseRows.filter((item) => item.bureau_id === bureau.id)
    const statusCounts = Object.fromEntries(['PENDING', 'UNDER_PROCESS', 'DISPOSED', 'TRANSFERRED', 'ESCALATED'].map((status) => [status, cases.filter((item) => item.status === status).length]))
    return { bureau_id: bureau.id, bureau_code: bureau.code, bureau_name: bureau.name, total_cases: cases.length, open_cases: cases.filter((item) => item.status !== 'DISPOSED').length, status_counts: statusCounts }
  })
  return clone({ items, total: items.length, page: 1, page_size: items.length })
}

export async function mockTrend(): Promise<Page<TrendRow>> {
  const grouped = new Map<string, number>()
  for (const item of caseRows) {
    const month = item.received_on.slice(0, 7)
    grouped.set(month, (grouped.get(month) ?? 0) + 1)
  }
  const items = [...grouped].sort(([a], [b]) => a.localeCompare(b)).map(([month, received]) => ({ month, received, disposed: caseRows.filter((item) => item.status === 'DISPOSED' && item.received_on.slice(0, 7) === month).length }))
  return clone({ items, total: items.length, page: 1, page_size: items.length })
}

export async function mockAgeing() {
  const today = new Date().toISOString().slice(0, 10)
  const bins = [{ band: '0-7 days', min: 0, max: 7, cases: 0 }, { band: '8-30 days', min: 8, max: 30, cases: 0 }, { band: '31-60 days', min: 31, max: 60, cases: 0 }, { band: '61+ days', min: 61, max: Number.POSITIVE_INFINITY, cases: 0 }]
  caseRows.filter((item) => item.status !== 'DISPOSED').forEach((item) => {
    const age = Math.floor((Date.parse(today) - Date.parse(item.received_on)) / 86400000)
    const band = bins.find((entry) => age >= entry.min && age <= entry.max)
    if (band) band.cases += 1
  })
  return { items: bins.map(({ band, cases }) => ({ band, cases })), total: bins.length, page: 1, page_size: bins.length }
}

export async function mockListAlerts(unreadOnly: boolean): Promise<Page<AlertRecord>> {
  const items = alertRows.filter((item) => !unreadOnly || !item.read_at).sort((a, b) => b.created_at.localeCompare(a.created_at))
  return clone({ items, total: items.length, page: 1, page_size: items.length })
}

export async function mockMarkAlertRead(id: string) {
  const alert = alertRows.find((item) => item.id === id)
  if (!alert) throw new Error('Alert was not found.')
  alert.read_at = alert.read_at ?? new Date().toISOString()
  return clone(alert)
}

export async function mockReport(type: ReportType, format: 'json' | 'csv') {
  let rows: Record<string, unknown>[]
  if (type === 'bureau') rows = (await mockWorkload()).items.map((row) => ({ ...row, status_counts: JSON.stringify(row.status_counts) }))
  else if (type === 'institution') rows = institutionRows.map((institution) => ({ institution_id: institution.id, aicte_permanent_id: institution.aicte_permanent_id, institution_name: institution.name, total_cases: caseRows.filter((item) => item.institution_id === institution.id).length, open_cases: caseRows.filter((item) => item.institution_id === institution.id && item.status !== 'DISPOSED').length }))
  else if (type === 'status') rows = Object.entries((await mockDashboardSummary()).status_counts).map(([status, cases]) => ({ status, cases }))
  else if (type === 'overlaps') rows = overlapRows.map((flag) => ({ tier: flag.tier, state: flag.state, flags: 1 }))
  else if (type === 'monthly') rows = (await mockTrend()).items.map((row) => ({ ...row }))
  else if (type === 'ageing') rows = (await mockAgeing()).items
  else if (type === 'region') rows = [...new Set(institutionRows.map((institution) => institution.region_name ?? 'Unassigned'))].map((region) => ({ region, total_cases: caseRows.filter((item) => item.region_id && institutionRows.find((institution) => institution.id === item.institution_id)?.region_name === region).length }))
  else rows = bureauRows.map((bureau) => { const cases = caseRows.filter((item) => item.bureau_id === bureau.id); const disposed = cases.filter((item) => item.status === 'DISPOSED').length; return { bureau_code: bureau.code, total_cases: cases.length, disposed_cases: disposed, disposal_rate: cases.length ? disposed / cases.length : null } })

  if (format === 'json') return { items: clone(rows), total: rows.length }
  const keys = rows.length ? Object.keys(rows[0]) : ['empty']
  const escape = (value: unknown) => `"${String(value ?? '').replace(/"/g, '""')}"`
  return new Blob([`${keys.map(escape).join(',')}\n${rows.map((row) => keys.map((key) => escape(row[key])).join(',')).join('\n')}\n`], { type: 'text/csv' })
}

export async function mockMe(): Promise<User> {
  const cached = localStorage.getItem('aicte_user')
  if (cached) {
    try {
      return JSON.parse(cached) as User
    } catch {}
  }
  return clone(demoUsers.admin)
}

export async function mockForwardDemo(days: number) {
  const asOf = new Date(Date.now() + days * 86400000).toISOString()
  return {
    days_forwarded: days,
    as_of: asOf,
    checked: caseRows.length,
    due_soon: 3,
    overdue: 4,
    reminders: 2,
    escalations: 1,
  }
}

export async function mockEvaluation(): Promise<Record<string, unknown>> {
  return {
    disclaimer: 'All records and labels are synthetic. Results describe this demo dataset only and are not operational performance claims.',
    source: 'SYNTHETIC',
    split: {
      strategy: 'fixed-seed institution group holdout',
      seed: 42,
      test_size: 0.4,
      train_rows: 19,
      test_rows: 13,
      train_institutions: 19,
      test_institutions: 13,
    },
    model: {
      score: '0.45*text_sim + 0.30*category_match + 0.15*time_proximity + 0.10*ref_overlap',
      threshold_tuned_on: 'train split only',
      selected_threshold: 0.6609589720359174,
      train_metrics: {
        precision: 1.0,
        recall: 1.0,
        f1: 1.0,
        confusion_matrix: { tn: 14, fp: 0, fn: 0, tp: 5 },
      },
    },
    held_out: {
      precision: 0.6666666666666666,
      recall: 0.8571428571428571,
      f1: 0.75,
      confusion_matrix: { tn: 3, fp: 3, fn: 1, tp: 6 },
    },
    baseline: {
      rule: 'same institution + same category + within 30 days',
      precision: 0.6363636363636364,
      recall: 1.0,
      f1: 0.7777777777777778,
      confusion_matrix: { tn: 2, fp: 4, fn: 0, tp: 7 },
    },
    false_positives: [
      {
        case_a: 'RB-2026-00028',
        case_b: 'RB-2026-00029',
        label: 0,
        score: 0.672628,
        kind: 'same_bureau_near_duplicate',
        summary_a: 'Students requested review of student transcript verification records at the synthetic institution.',
        summary_b: 'Students asked the bureau to check the student transcript verification records at this synthetic institution.',
      },
    ],
    misses: [
      {
        case_a: 'RB-2026-00008',
        case_b: 'PGRC-2026-00008',
        label: 1,
        score: 0.649007,
        kind: 'planted_overlap',
        summary_a: 'Applicants reported that submitted scholarship documents were not reviewed. Synthetic reference SYN-REF-0008.',
        summary_b: 'A complaint says scholarship applications remain pending despite document submission. Reference SYN-REF-0008.',
      },
    ],
  }
}

export async function mockCopilotQuery(query: string): Promise<CopilotResponse> {
  const q = query.toLowerCase()
  if (q.includes('overlap') || q.includes('conflict') || q.includes('duplicate')) {
    const openFlags = overlapRows.filter((f) => f.state === 'OPEN')
    return {
      query,
      intent: 'OVERLAP_LOOKUP',
      answer: `Found ${openFlags.length} active cross-bureau overlap flags requiring coordination.`,
      highlight: `${openFlags.length} active overlap cases detected`,
      items: openFlags.slice(0, 4).map((f) => ({
        id: f.id,
        title: f.institution_name ?? 'Unknown Institution',
        subtitle: `Tier ${f.tier}${f.score != null ? ` • Score ${(f.score * 100).toFixed(0)}%` : ''}`,
        status: f.state,
        link: `/overlaps`,
      })),
      action: {
        label: 'Open Overlap Coordination Center',
        link: '/overlaps',
      },
      suggestions: ['Show pending complaints', 'Check workload by bureau', 'Cases beyond SLA'],
    }
  }
  if (q.includes('overdue') || q.includes('sla') || q.includes('pending')) {
    const pendingCases = caseRows.filter((c) => c.status === 'PENDING')
    return {
      query,
      intent: 'PENDING_STATUS',
      answer: `There are ${pendingCases.length} pending cases currently tracked across bureaus.`,
      highlight: `${pendingCases.length} pending complaints`,
      items: pendingCases.slice(0, 4).map((c) => ({
        id: c.id,
        title: c.case_no,
        subtitle: c.institution_name ?? 'General complaint',
        status: c.status,
        link: `/cases/${c.id}`,
      })),
      action: {
        label: 'View Pending Cases',
        link: '/cases?status=PENDING',
      },
      suggestions: ['Show overlapping cases', 'Summary of all cases', 'Overdue cases beyond SLA'],
    }
  }
  return {
    query,
    intent: 'GENERAL_QUERY',
    answer: `Analysis complete for "${query}". Tracking ${caseRows.length} total synthetic complaints in demo mode.`,
    highlight: `${caseRows.length} total cases recorded`,
    items: caseRows.slice(0, 4).map((c) => ({
      id: c.id,
      title: c.case_no,
      subtitle: `${c.bureau_code} • ${c.institution_name ?? 'General'}`,
      status: c.status,
      link: `/cases/${c.id}`,
    })),
    action: {
      label: 'Go to Dashboard',
      link: '/dashboard',
    },
    suggestions: ['Show open overlaps', 'Pending cases', 'Cases in North region'],
  }
}

