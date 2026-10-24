import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import CaseDetailPage from './pages/CaseDetailPage'
import CasesPage from './pages/CasesPage'
import DashboardPage from './pages/DashboardPage'
import OverlapCenterPage from './pages/OverlapCenterPage'
import Placeholder from './pages/Placeholder'

// Built so far: Dashboard, Cases list, Case detail, Overlap Center. Other routes are
// placeholders so that every link lands somewhere valid.
const OTHER_PAGES: Array<[string, string]> = [
  ['institutions', 'Institutions'],
  ['alerts', 'Alerts'],
  ['reports', 'Reports'],
  ['import', 'Import'],
]

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="cases/:id" element={<CaseDetailPage />} />
        <Route path="overlaps" element={<OverlapCenterPage />} />
        {OTHER_PAGES.map(([path, title]) => (
          <Route key={path} path={path} element={<Placeholder title={title} />} />
        ))}
        <Route path="*" element={<Placeholder title="Page not found" />} />
      </Route>
    </Routes>
  )
}
