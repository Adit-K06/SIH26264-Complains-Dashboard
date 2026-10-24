import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import DashboardPage from './pages/DashboardPage'
import Placeholder from './pages/Placeholder'

// Only the Dashboard is built here. Other routes are placeholders so that
// every dashboard link (e.g. /cases?status=PENDING) lands somewhere valid.
// Teammates replace the placeholders with real pages.
const OTHER_PAGES: Array<[string, string]> = [
  ['cases', 'Cases'],
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
        {OTHER_PAGES.map(([path, title]) => (
          <Route key={path} path={path} element={<Placeholder title={title} />} />
        ))}
        <Route path="*" element={<Placeholder title="Page not found" />} />
      </Route>
    </Routes>
  )
}
