import axios from 'axios'

export const api = axios.create({ baseURL: '/api/v1' })

// The login/refresh flow belongs to the integration owner. Until then the
// client just attaches a token if one has been stored.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Backend error format: {"error":{"code":"STRING","message":"text"}}
export function errorMessage(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const m = (e.response?.data as { error?: { message?: unknown } } | undefined)?.error
      ?.message
    if (typeof m === 'string') return m
    return e.message
  }
  return e instanceof Error ? e.message : 'Unexpected error'
}
