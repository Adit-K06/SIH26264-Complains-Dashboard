import { Component, ErrorInfo, lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { ProtectedLayout } from './components/Layout'
import { LoadingState } from './components/Shared'
import { LoginPage } from './pages/LoginPage'

const CasesPage = lazy(() => import('./pages/CasePages').then((module) => ({ default: module.CasesPage })))
const CaseDetailPage = lazy(() => import('./pages/CasePages').then((module) => ({ default: module.CaseDetailPage })))
const InstitutionsPage = lazy(() => import('./pages/CasePages').then((module) => ({ default: module.InstitutionsPage })))
const InstitutionDetailPage = lazy(() => import('./pages/CasePages').then((module) => ({ default: module.InstitutionDetailPage })))
const DashboardPage = lazy(() => import('./pages/OtherPages').then((module) => ({ default: module.DashboardPage })))
const AlertsPage = lazy(() => import('./pages/OtherPages').then((module) => ({ default: module.AlertsPage })))
const EvaluationPage = lazy(() => import('./pages/OtherPages').then((module) => ({ default: module.EvaluationPage })))
const OverlapsPage = lazy(() => import('./pages/OtherPages').then((module) => ({ default: module.OverlapsPage })))
const ReportsPage = lazy(() => import('./pages/OtherPages').then((module) => ({ default: module.ReportsPage })))

class ErrorBoundary extends Component<{ children: React.ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-900">
            <h3 className="text-base font-bold">Something went wrong on this screen</h3>
            <p className="mt-2 text-sm text-red-700">{this.state.error?.message ?? 'An unexpected error occurred.'}</p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
              className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700"
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function SuspendedPage({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingState label="Opening page…" />}>{children}</Suspense>
    </ErrorBoundary>
  )
}

function RequireAuth() {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <LoadingState label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

function RequireAdmin() {
  const { user } = useAuth()
  return user?.role === 'ADMIN' ? <EvaluationPage /> : <Navigate to="/dashboard" replace />
}

export default function App() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<ProtectedLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<SuspendedPage><DashboardPage /></SuspendedPage>} />
          <Route path="cases" element={<SuspendedPage><CasesPage /></SuspendedPage>} />
          <Route path="cases/:caseId" element={<SuspendedPage><CaseDetailPage /></SuspendedPage>} />
          <Route path="institutions" element={<SuspendedPage><InstitutionsPage /></SuspendedPage>} />
          <Route path="institutions/:institutionId" element={<SuspendedPage><InstitutionDetailPage /></SuspendedPage>} />
          <Route path="overlaps" element={<SuspendedPage><OverlapsPage /></SuspendedPage>} />
          <Route path="alerts" element={<SuspendedPage><AlertsPage /></SuspendedPage>} />
          <Route path="reports" element={<SuspendedPage><ReportsPage /></SuspendedPage>} />
          <Route path="evaluation" element={<SuspendedPage><RequireAdmin /></SuspendedPage>} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} />
    </Routes>
  )
}
