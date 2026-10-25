import axios from 'axios'

const apiBase = import.meta.env.VITE_API_BASE_URL || ''
export const api = axios.create({ baseURL: `${apiBase}/api/v1` })

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401: clear tokens and reload to show LoginPage
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      // Don't redirect if this is the login call itself
      const url = error.config?.url ?? ''
      if (!url.includes('/auth/login')) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        // Reload: App.tsx will see no token and show LoginPage
        window.location.reload()
      }
    }
    return Promise.reject(error)
  }
)

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
