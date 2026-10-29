import { lazy, Suspense } from 'react'
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

function SuspendedPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingState label="Opening page…" />}>{children}</Suspense>
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
