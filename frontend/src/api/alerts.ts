import { api } from './client'
import { USE_MOCKS } from './config'
import type { Alert } from './alertTypes'
import { mockMarkRead, mockQueryAlerts } from './mocks/alerts'
import type { Paged } from './types'
import { toApiParams } from '../lib/alerts'
import type { AlertFilters } from '../lib/alerts'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

// GET /alerts
export async function getAlerts(f: AlertFilters): Promise<Paged<Alert>> {
  if (USE_MOCKS) {
    await delay(250)
    return mockQueryAlerts(f)
  }
  return (await api.get<Paged<Alert>>('/alerts', { params: toApiParams(f) })).data
}

// POST /alerts/{id}/read
export async function markAlertRead(id: number): Promise<void> {
  if (USE_MOCKS) {
    await delay(150)
    mockMarkRead(id)
    return
  }
  await api.post(`/alerts/${id}/read`)
}

/** Unread count for the top-bar bell: GET /alerts?unread=true&page_size=1 -> total. */
export async function getUnreadCount(): Promise<number> {
  if (USE_MOCKS) {
    await delay(100)
    return mockQueryAlerts({ unread: true, type: '', page: 1, page_size: 1 }).total
  }
  return (await api.get<Paged<Alert>>('/alerts', { params: { unread: 'true', page_size: 1 } })).data.total
}
