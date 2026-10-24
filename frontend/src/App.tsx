import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import CasesPage from './pages/CasesPage'
import DashboardPage from './pages/DashboardPage'
import Placeholder from './pages/Placeholder'

// Built so far: Dashboard, Cases list. Other routes are placeholders so that
// every link (e.g. /cases/12, /overlaps?state=OPEN) lands somewhere valid.
const OTHER_PAGES: Array<[string, string]> = [
  ['cases/:id', 'Case detail'],
  ['institutions', 'Institutions'],
  ['overlaps', 'Overlap Center'],
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
        {OTHER_PAGES.map(([path, title]) => (
          <Route key={path} path={path} element={<Placeholder title={title} />} />
        ))}
        <Route path="*" element={<Placeholder title="Page not found" />} />
      </Route>
    </Routes>
  )
}
