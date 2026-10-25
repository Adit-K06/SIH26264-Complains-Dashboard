import { NavLink, Outlet } from 'react-router-dom'
import {
  Bell,
  Building2,
  Copy,
  FileText,
  FlaskConical,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  Upload,
} from 'lucide-react'
import type { ComponentType } from 'react'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { useUnreadAlerts } from '../hooks/useUnreadAlerts'

const NAV: Array<{ to: string; label: string; icon: ComponentType<{ className?: string }> }> = [
  { to: '/dashboard',   label: 'Dashboard',    icon: LayoutDashboard },
  { to: '/cases',       label: 'Cases',         icon: FolderOpen },
  { to: '/institutions',label: 'Institutions',  icon: Building2 },
  { to: '/overlaps',    label: 'Overlap Center',icon: Copy },
  { to: '/alerts',      label: 'Alerts',        icon: Bell },
  { to: '/reports',     label: 'Reports',       icon: FileText },
  { to: '/import',      label: 'Import',        icon: Upload },
  { to: '/evaluation',  label: 'AI Evaluation', icon: FlaskConical },
]

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Admin',
  SENIOR_MGMT: 'Senior Mgmt',
  BUREAU_OFFICER: 'Bureau Officer',
  REGIONAL_OFFICER: 'Regional Officer',
}

const ROLE_COLORS: Record<string, string> = {
  ADMIN: 'bg-purple-100 text-purple-800',
  SENIOR_MGMT: 'bg-blue-100 text-blue-800',
  BUREAU_OFFICER: 'bg-green-100 text-green-800',
  REGIONAL_OFFICER: 'bg-orange-100 text-orange-800',
}

interface AppLayoutProps {
  onLogout: () => void
}

export default function AppLayout({ onLogout }: AppLayoutProps) {
  const user = useCurrentUser()
  const unread = useUnreadAlerts()
  const roleLabel = ROLE_LABELS[user.role] ?? user.role
  const roleColor = ROLE_COLORS[user.role] ?? 'bg-slate-100 text-slate-700'

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="hidden w-56 shrink-0 flex-col border-r border-slate-200 bg-white md:flex">
        {/* Logo */}
        <div className="border-b border-slate-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-navy">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <div>
              <div className="text-xs font-bold text-navy">AICTE Monitor</div>
              <div className="text-[10px] text-slate-400">SIH26264</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 p-2" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-navy text-white font-medium'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User info + logout */}
        <div className="border-t border-slate-200 p-3 space-y-2">
          <div className="px-1">
            <div className="text-xs font-semibold text-slate-800 truncate">{user.name}</div>
            <span className={`mt-1 inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${roleColor}`}>
              {roleLabel}
            </span>
          </div>
          <button
            onClick={onLogout}
            className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-xs text-slate-500 hover:bg-red-50 hover:text-red-600 transition"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top header */}
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2.5">
          <span className="hidden text-sm text-slate-500 md:inline">
            Integrated complaint monitoring and status dashboard
          </span>
          <span className="text-sm font-semibold text-navy md:hidden">AICTE Monitor</span>

          <div className="flex items-center gap-3 text-sm">
            <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-800">
              Synthetic data
            </span>

            {/* Alerts bell */}
            <NavLink
              to="/alerts"
              aria-label={unread ? `Alerts, ${unread} unread` : 'Alerts'}
              className="relative text-slate-600 hover:text-navy transition"
            >
              <Bell className="h-4 w-4" />
              {unread ? (
                <span className="absolute -right-2.5 -top-2 min-w-4 rounded-full bg-red-600 px-1 text-center text-[10px] font-semibold leading-4 text-white">
                  {unread > 99 ? '99+' : unread}
                </span>
              ) : null}
            </NavLink>

            {/* User pill */}
            <span className={`hidden rounded-full px-2.5 py-0.5 text-xs font-semibold md:inline ${roleColor}`}>
              {user.name} · {roleLabel}
            </span>

            {/* Mobile logout */}
            <button onClick={onLogout} className="md:hidden text-slate-500 hover:text-red-600 transition" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-auto p-4">
          <Outlet />
        </main>

        <footer className="border-t border-slate-200 bg-white px-4 py-1.5 text-xs text-slate-400">
          Demo uses synthetic data — not real AICTE records · SIH26264
        </footer>
      </div>
    </div>
  )
}
