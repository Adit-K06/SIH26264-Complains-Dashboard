import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import AlertsPage from './pages/AlertsPage'
import CaseDetailPage from './pages/CaseDetailPage'
import CasesPage from './pages/CasesPage'
import DashboardPage from './pages/DashboardPage'
import EvaluationPage from './pages/EvaluationPage'
import ImportPage from './pages/ImportPage'
import InstitutionDetailPage from './pages/InstitutionDetailPage'
import InstitutionsPage from './pages/InstitutionsPage'
import OverlapCenterPage from './pages/OverlapCenterPage'
import Placeholder from './pages/Placeholder'
import ReportsPage from './pages/ReportsPage'

// Built: Dashboard, Cases list + detail, Overlap Center, Institutions list + 360, Alerts, Reports,
// Import, Evaluation. The catch-all keeps unknown URLs from showing a blank page.
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
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
