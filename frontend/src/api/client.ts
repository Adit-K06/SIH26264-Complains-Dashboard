import axios from 'axios'

const configuredBase = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '')
const hasBackend = Boolean(configuredBase)

// Auto-detect mock mode:
// - Explicitly VITE_USE_MOCKS=true -> use mocks
// - Explicitly VITE_USE_MOCKS=false -> use real backend
// - Standalone production preview (e.g. Vercel without backend URL set) -> auto fallback to mocks so app never fails!
export const useMocks =
  import.meta.env.VITE_USE_MOCKS === 'true' ||
  (!hasBackend && import.meta.env.VITE_USE_MOCKS !== 'false')

const baseURL = configuredBase
  ? (configuredBase.endsWith('/api') ? configuredBase : `${configuredBase}/api`)
  : '/api'

export const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000, // 60s to accommodate cloud cold starts (e.g. Render free tier)
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('aicte_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      localStorage.removeItem('aicte_access_token')
      localStorage.removeItem('aicte_user')
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const apiMessage = error.response?.data?.error?.message
    if (typeof apiMessage === 'string') return apiMessage
    if (error.response?.status === 404) {
      return 'API endpoint not found (404). If deployed without an external backend, the app operates in standalone demo mode.'
    }
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      return 'The backend service took longer than expected to respond. If running on free cloud tier, the server may be waking up from sleep. Please wait 15 seconds and try again.'
    }
    if (error.message === 'Network Error') {
      return 'Could not connect to the API. If deployed, verify VITE_API_BASE_URL points to your active backend.'
    }
  }
  return error instanceof Error ? error.message : 'Something went wrong. Try again.'
}
