import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { authApi } from '../api'
import { useMocks } from '../api/client'
import type { User } from '../types'

interface AuthState {
  user: User | null
  ready: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

function readCachedUser(): User | null {
  try {
    const value = localStorage.getItem('aicte_user')
    return value ? JSON.parse(value) as User : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(readCachedUser)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('aicte_access_token')
    if (!token) {
      setReady(true)
      return
    }
    if (useMocks) {
      if (!user) {
        const cached = readCachedUser()
        if (cached) {
          setUser(cached)
        } else {
          localStorage.removeItem('aicte_access_token')
        }
      }
      setReady(true)
      return
    }
    authApi.me()
      .then((currentUser) => {
        setUser(currentUser)
        localStorage.setItem('aicte_user', JSON.stringify(currentUser))
      })
      .catch(() => {
        localStorage.removeItem('aicte_access_token')
        localStorage.removeItem('aicte_user')
        setUser(null)
      })
      .finally(() => setReady(true))
  // A cached session is checked once during startup.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const value = useMemo<AuthState>(() => ({
    user,
    ready,
    async login(username, password) {
      const session = await authApi.login(username, password)
      localStorage.setItem('aicte_access_token', session.access_token)
      const currentUser = session.user ?? await authApi.me()
      localStorage.setItem('aicte_user', JSON.stringify(currentUser))
      setUser(currentUser)
      setReady(true)
    },
    logout() {
      localStorage.removeItem('aicte_access_token')
      localStorage.removeItem('aicte_user')
      setUser(null)
    },
  }), [ready, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
