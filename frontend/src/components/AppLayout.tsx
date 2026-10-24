import { NavLink, Outlet } from 'react-router-dom'
import {
  Bell,
  Building2,
  Copy,
  FileText,
  FlaskConical,
  FolderOpen,
  LayoutDashboard,
  Upload,
} from 'lucide-react'
import type { ComponentType } from 'react'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { useUnreadAlerts } from '../hooks/useUnreadAlerts'

const NAV: Array<{ to: string; label: string; icon: ComponentType<{ className?: string }> }> = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/cases', label: 'Cases', icon: FolderOpen },
  { to: '/institutions', label: 'Institutions', icon: Building2 },
  { to: '/overlaps', label: 'Overlaps', icon: Copy },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/import', label: 'Import', icon: Upload },
  { to: '/evaluation', label: 'Evaluation', icon: FlaskConical },
]

// Login and the real user/role are still to be wired by whoever does integration (/auth/me):
// useCurrentUser() currently returns a MOCK user. The role-based "Admin" link is not built yet.
export default function AppLayout() {
  const user = useCurrentUser()
  const unread = useUnreadAlerts()

  return (
    <div className="flex h-full">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-slate-200 bg-white md:flex">
        <div className="border-b border-slate-200 px-4 py-3">
          <div className="text-sm font-semibold text-navy">AICTE Complaint Monitor</div>
          <div className="text-xs text-slate-500">SIH26264</div>
        </div>
        <nav className="flex-1 space-y-0.5 p-2" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3 py-2 text-sm ${
                  isActive
                    ? 'bg-navy text-white'
                    : 'text-slate-700 hover:bg-slate-100'
                }`
              }
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2.5">
          <span className="text-sm font-semibold text-navy md:hidden">AICTE Complaint Monitor</span>
          <span className="hidden text-sm text-slate-500 md:inline">
            Integrated complaint monitoring and status dashboard
          </span>
          <div className="flex items-center gap-3 text-sm">
            <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-800">
              Synthetic data
            </span>
            <NavLink
              to="/alerts"
              aria-label={unread ? `Alerts, ${unread} unread` : 'Alerts'}
              className="relative text-slate-600 hover:text-navy"
            >
              <Bell className="h-4 w-4" />
              {unread ? (
                <span className="absolute -right-2.5 -top-2 min-w-4 rounded-full bg-red-600 px-1 text-center text-[10px] font-semibold leading-4 text-white">
                  {unread > 99 ? '99+' : unread}
                </span>
              ) : null}
            </NavLink>
            <span className="text-slate-700">
              {user.name} ({user.role.replace(/_/g, ' ').toLowerCase()})
            </span>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-auto p-4">
          <Outlet />
        </main>

        <footer className="border-t border-slate-200 bg-white px-4 py-1.5 text-xs text-slate-500">
          Demo uses synthetic data. Not real AICTE data.
        </footer>
      </div>
    </div>
  )
}
