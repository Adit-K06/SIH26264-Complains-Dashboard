import axios from 'axios'

const configuredBase = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '')
const baseURL = configuredBase
  ? configuredBase.endsWith('/api') ? configuredBase : `${configuredBase}/api`
  : '/api'

export const useMocks = import.meta.env.VITE_USE_MOCKS === 'true'

export const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
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
    if (error.code === 'ECONNABORTED') return 'The service took too long to respond. Try again.'
    if (error.message === 'Network Error') return 'Could not reach the API. Check that the backend is running.'
  }
  return error instanceof Error ? error.message : 'Something went wrong. Try again.'
}
