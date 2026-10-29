import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Activity, Bell, Building2, ChevronLeft, ChevronRight, ClipboardList, FileBarChart2,
  Gauge, GraduationCap, LogOut, Menu, SearchCheck, ShieldCheck, Sparkles,
} from 'lucide-react'
import { alertsApi } from '../api'
import { useAuth } from '../auth/AuthContext'
import { CopilotModal } from './CopilotModal'
import { SyntheticFooter } from './Shared'

const navItems = [
  { label: 'Dashboard', to: '/dashboard', icon: Gauge },
  { label: 'Cases', to: '/cases', icon: ClipboardList },
  { label: 'Institutions', to: '/institutions', icon: Building2 },
  { label: 'Overlaps', to: '/overlaps', icon: SearchCheck },
  { label: 'Alerts', to: '/alerts', icon: Bell },
  { label: 'Reports', to: '/reports', icon: FileBarChart2 },
  { label: 'Evaluation', to: '/evaluation', icon: Activity, adminOnly: true },
]

const roleNames: Record<string, string> = {
  ADMIN: 'Administrator', SENIOR_MGMT: 'Senior management', BUREAU_OFFICER: 'Bureau officer', REGIONAL_OFFICER: 'Regional officer',
}

export function ProtectedLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [copilotOpen, setCopilotOpen] = useState(false)
  const unreadQuery = useQuery({ queryKey: ['alerts', 'unread-count'], queryFn: () => alertsApi.list(true), enabled: Boolean(user), staleTime: 30000 })
  const unreadCount = unreadQuery.data?.total ?? 0
  const current = navItems.find((item) => location.pathname === item.to || (item.to !== '/dashboard' && location.pathname.startsWith(`${item.to}/`)))

  const sidebar = (
    <aside className={`flex h-full flex-col bg-[#102b46] text-white ${collapsed ? 'w-[78px]' : 'w-[252px]'}`}>
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-5">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-teal-600"><GraduationCap className="h-5 w-5" /></div>
        {!collapsed && <div className="min-w-0"><p className="truncate text-sm font-bold tracking-wide">AICTE COORDINATION</p><p className="text-[10px] uppercase tracking-[0.18em] text-slate-300">Complaint dashboard</p></div>}
      </div>
      <nav className="flex-1 space-y-1 px-3 py-5" aria-label="Main navigation">
        {navItems.filter((item) => !item.adminOnly || user?.role === 'ADMIN').map(({ label, to, icon: Icon }) => (
          <NavLink key={to} to={to} onClick={() => setMobileOpen(false)} title={collapsed ? label : undefined} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-teal-700 text-white shadow-sm' : 'text-slate-200 hover:bg-white/10 hover:text-white'} ${collapsed ? 'justify-center px-2' : ''}`}>
            <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 p-3">
        {!collapsed && <div className="mb-2 rounded-lg bg-white/5 px-3 py-2"><p className="truncate text-xs font-semibold">{user?.name}</p><p className="truncate text-[11px] text-slate-300">{roleNames[user?.role ?? '']}</p></div>}
        <button onClick={() => setCollapsed((value) => !value)} className="hidden w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs text-slate-300 hover:bg-white/10 lg:flex" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <><ChevronLeft className="h-4 w-4" />Collapse menu</>}
        </button>
      </div>
    </aside>
  )

  return (
    <div className="min-h-screen bg-slate-50 lg:flex">
      <div className="hidden lg:block">{sidebar}</div>
      {mobileOpen && <div className="fixed inset-0 z-40 lg:hidden"><button className="absolute inset-0 bg-slate-950/50" onClick={() => setMobileOpen(false)} aria-label="Close menu" /> <div className="relative h-full w-[280px]">{sidebar}</div></div>}
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Open menu" onClick={() => setMobileOpen(true)}><Menu className="h-5 w-5" /></button>
            <div className="hidden h-9 w-9 place-items-center rounded-lg bg-teal-50 text-teal-800 sm:grid"><ShieldCheck className="h-5 w-5" /></div>
            <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-900">{current?.label ?? 'AICTE Coordination'}</p><p className="hidden text-xs text-slate-500 sm:block">Monitoring across existing Bureau and Cell systems</p></div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={() => setCopilotOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50 px-2.5 py-1.5 text-xs font-bold text-teal-900 shadow-xs transition hover:bg-teal-100 hover:border-teal-300"
              title="Open AICTE Intelligence Copilot"
            >
              <Sparkles className="h-4 w-4 text-teal-700" />
              <span className="hidden sm:inline">AI Copilot</span>
            </button>
            <NavLink to="/alerts" className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100" aria-label={`Alerts${unreadCount ? `, ${unreadCount} unread` : ''}`}><Bell className="h-5 w-5" />{unreadCount > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-red-600 px-1 text-[9px] font-bold text-white">{unreadCount > 9 ? '9+' : unreadCount}</span>}</NavLink>
            <div className="hidden text-right sm:block"><p className="max-w-40 truncate text-xs font-semibold text-slate-800">{user?.name}</p><p className="text-[11px] text-slate-500">{roleNames[user?.role ?? '']}</p></div>
            <button onClick={() => { logout(); navigate('/login', { replace: true }) }} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50" title="Sign out"><LogOut className="h-4 w-4" /><span className="hidden md:inline">Sign out</span></button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-6 sm:px-6 lg:px-8"><Outlet /></main>
        <SyntheticFooter />
        <CopilotModal open={copilotOpen} onClose={() => setCopilotOpen(false)} />
      </div>
    </div>
  )
}
