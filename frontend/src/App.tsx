import { useState, useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import CasesPage from './pages/CasesPage'
import CaseDetailPage from './pages/CaseDetailPage'
import InstitutionsPage from './pages/InstitutionsPage'
import InstitutionDetailPage from './pages/InstitutionDetailPage'
import OverlapCenterPage from './pages/OverlapCenterPage'
import AlertsPage from './pages/AlertsPage'
import ReportsPage from './pages/ReportsPage'
import ImportPage from './pages/ImportPage'
import EvaluationPage from './pages/EvaluationPage'
import Placeholder from './pages/Placeholder'

function useAuth() {
  const [isLoggedIn, setIsLoggedIn] = useState(
    () => !!localStorage.getItem('access_token')
  )

  // Listen for storage changes (logout from another tab)
  useEffect(() => {
    const handler = () => setIsLoggedIn(!!localStorage.getItem('access_token'))
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [])

  function login() { setIsLoggedIn(true) }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setIsLoggedIn(false)
  }

  return { isLoggedIn, login, logout }
}

export default function App() {
  const { isLoggedIn, login, logout } = useAuth()

  if (!isLoggedIn) {
    return <LoginPage onLogin={login} />
  }

  return (
    <Routes>
      <Route element={<AppLayout onLogout={logout} />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="cases/:id" element={<CaseDetailPage />} />
        <Route path="institutions" element={<InstitutionsPage />} />
        <Route path="institutions/:id" element={<InstitutionDetailPage />} />
        <Route path="overlaps" element={<OverlapCenterPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="import" element={<ImportPage />} />
        <Route path="evaluation" element={<EvaluationPage />} />
        <Route path="*" element={<Placeholder title="Page not found" />} />
      </Route>
    </Routes>
  )
}
