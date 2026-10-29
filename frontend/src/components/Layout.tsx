import React, { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  BarChart3,
  Bell,
  Building2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Layers,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { alertsApi, casesApi, overlapsApi } from '../api'
import { useAuth } from '../auth/AuthContext'
import { CopilotModal } from './CopilotModal'
import { SyntheticFooter } from './Shared'

const navItems = [
  { label: 'Overview Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Complaint Management', to: '/cases', icon: FileText, showCaseCount: true },
  { label: 'Overlap Management', to: '/overlaps', icon: Layers, showOverlapBadge: true },
  { label: 'Institutions Directory', to: '/institutions', icon: Building2 },
  { label: 'Alerts Center', to: '/alerts', icon: Bell, showAlertBadge: true },
  { label: 'Reports & Analytics', to: '/reports', icon: BarChart3 },
  { label: 'Model Evaluation', to: '/evaluation', icon: Activity, adminOnly: true },
]

const roleNames: Record<string, string> = {
  ADMIN: 'Administrator',
  SENIOR_MGMT: 'Senior Management',
  BUREAU_OFFICER: 'Bureau Officer',
  REGIONAL_OFFICER: 'Regional Officer',
}

export function ProtectedLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [copilotOpen, setCopilotOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearchFocused, setIsSearchFocused] = useState(false)

  const unreadQuery = useQuery({
    queryKey: ['alerts', 'unread-count'],
    queryFn: () => alertsApi.list(true),
    enabled: Boolean(user),
    staleTime: 30000,
  })
  const unreadCount = unreadQuery.data?.total ?? 0

  const overlapsQuery = useQuery({
    queryKey: ['overlaps', 'count'],
    queryFn: () => overlapsApi.list(undefined, 'OPEN'),
    staleTime: 45000,
  })
  const overlapsCount = overlapsQuery.data?.total ?? 0

  const casesCountQuery = useQuery({
    queryKey: ['cases', 'total-count'],
    queryFn: () => casesApi.list({ page: 1, page_size: 1 }),
    staleTime: 60000,
  })
  const totalCasesCount = casesCountQuery.data?.total ?? 301

  const handleGlobalSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/cases?q=${encodeURIComponent(searchQuery.trim())}`)
      setSearchQuery('')
      setIsSearchFocused(false)
    }
  }

  const sidebar = (
    <aside
      className={`flex h-full flex-col bg-[#0a1128] text-slate-300 transition-all duration-200 select-none ${
        collapsed ? 'w-[78px]' : 'w-[260px]'
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-800/80 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-800 text-white shadow-md shadow-blue-500/20 border border-blue-400/30 font-extrabold text-xs tracking-tight">
          AICTE
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-xs font-bold tracking-wider uppercase text-blue-400">SIH-26264</p>
            <p className="truncate text-xs font-semibold text-white">Complaint Central</p>
          </div>
        )}
      </div>

      {/* Coordinating Bureaus Matrix */}
      {!collapsed && (
        <div className="p-3 border-b border-slate-800/70 bg-slate-900/40">
          <div className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase mb-2">
            Coordinating Bureaus
          </div>
          <div className="grid grid-cols-2 gap-1.5 text-xs">
            <div className="px-2 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-between">
              <span className="font-bold text-blue-400">RB</span>
              <span className="text-[10px] text-slate-400">Regulation</span>
            </div>
            <div className="px-2 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-between">
              <span className="font-bold text-emerald-400">PGRC</span>
              <span className="text-[10px] text-slate-400">Grievance</span>
            </div>
            <div className="px-2 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-between">
              <span className="font-bold text-amber-400">AB</span>
              <span className="text-[10px] text-slate-400">Approval</span>
            </div>
            <div className="px-2 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-between">
              <span className="font-bold text-rose-400">FIN</span>
              <span className="text-[10px] text-slate-400">Finance</span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-3 overflow-y-auto" aria-label="Main navigation">
        {!collapsed && (
          <div className="px-2 pb-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Platform Navigation
          </div>
        )}
        {navItems
          .filter((item) => !item.adminOnly || user?.role === 'ADMIN')
          .map(({ label, to, icon: Icon, showCaseCount, showOverlapBadge, showAlertBadge }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileOpen(false)}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all group cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white font-semibold shadow-md shadow-blue-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
                } ${collapsed ? 'justify-center px-2' : ''}`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4 shrink-0 transition-colors" aria-hidden="true" />
                {!collapsed && <span>{label}</span>}
              </div>
              {!collapsed && (
                <>
                  {showCaseCount && totalCasesCount > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-400/30">
                      {totalCasesCount}
                    </span>
                  )}
                  {showOverlapBadge && overlapsCount > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold bg-purple-500/30 text-purple-200 border border-purple-400/40 animate-pulse">
                      {overlapsCount} ALERTS
                    </span>
                  )}
                  {showAlertBadge && unreadCount > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold bg-rose-500/30 text-rose-200 border border-rose-400/40">
                      {unreadCount}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
      </nav>

      {/* System Status and Rule Engine */}
      {!collapsed && (
        <div className="p-3 border-t border-slate-800/80 bg-slate-900/60 text-xs">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1.5">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              AICTE Central Hub
            </span>
            <span className="font-mono text-emerald-400 font-medium text-[10px]">Sync Active</span>
          </div>
          <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60 text-[10px] text-slate-300 leading-relaxed">
            <div className="flex items-center gap-1 font-semibold text-amber-400 mb-0.5">
              <ShieldCheck className="w-3 h-3" />
              Rule Engine v4.2 Active
            </div>
            Deduplication active across 5 bureaus and 8 regional offices.
          </div>
        </div>
      )}

      {/* User profile & collapse control */}
      <div className="border-t border-slate-800/80 p-3">
        {!collapsed && (
          <div className="mb-2 rounded-lg bg-slate-800/40 px-3 py-2">
            <p className="truncate text-xs font-semibold text-white">{user?.name}</p>
            <p className="truncate text-[11px] text-slate-400">{roleNames[user?.role ?? '']}</p>
          </div>
        )}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="hidden w-full items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800/70 hover:text-white lg:flex"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <><ChevronLeft className="h-4 w-4" />Collapse</>}
        </button>
      </div>
    </aside>
  )

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Subtle National Tricolor Ribbon */}
      <div className="h-1 w-full bg-gradient-to-r from-orange-500 via-white to-emerald-600 shrink-0" />

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Desktop Sidebar */}
        <div className="hidden lg:block shrink-0">{sidebar}</div>

        {/* Mobile Sidebar */}
        {mobileOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <button
              className="absolute inset-0 bg-slate-950/60 backdrop-blur-xs"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            />
            <div className="relative h-full w-[270px]">{sidebar}</div>
          </div>
        )}

        {/* Right Content Area */}
        <div className="flex flex-1 flex-col min-w-0 overflow-y-auto">
          {/* Header */}
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 backdrop-blur-md px-4 sm:px-6">
            {/* Left: Mobile button + Brand title */}
            <div className="flex items-center gap-3 min-w-max">
              <button
                className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
                aria-label="Open menu"
                onClick={() => setMobileOpen(true)}
              >
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700">
                    All India Council for Technical Education
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200">
                    SIH-26264
                  </span>
                </div>
                <h1 className="text-sm sm:text-base font-bold text-slate-900 leading-tight">
                  Integrated Complaint & Overlap Monitoring System
                </h1>
              </div>
            </div>

            {/* Center: Global Search Bar */}
            <form onSubmit={handleGlobalSearch} className="relative flex-1 max-w-md mx-4 hidden md:block">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by Docket ID, AICTE Permanent ID, or College..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
                aria-label="Global search docket or institution"
                className={`w-full pl-9 pr-8 py-1.5 text-xs rounded-xl border text-slate-900 placeholder-slate-400 focus:outline-none transition-all ${
                  isSearchFocused ? 'bg-white border-blue-500 ring-2 ring-blue-500/30' : 'bg-slate-100 border-slate-200'
                }`}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 hover:text-slate-600 px-1 py-0.5 rounded bg-slate-200"
                >
                  Clear
                </button>
              )}
            </form>

            {/* Right: Actions & User Info */}
            <div className="flex items-center gap-2 sm:gap-3">
              <button
                onClick={() => setCopilotOpen(true)}
                className="flex items-center gap-1.5 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-3 py-1.5 text-xs font-bold text-blue-900 shadow-xs transition hover:from-blue-100 hover:to-indigo-100 hover:border-blue-300"
                title="Open AICTE Intelligence Copilot"
              >
                <Sparkles className="h-4 w-4 text-blue-600" />
                <span className="hidden sm:inline">AI Copilot</span>
              </button>

              <NavLink
                to="/alerts"
                className="relative rounded-xl p-2 text-slate-600 hover:bg-slate-100"
                aria-label={`Alerts${unreadCount ? `, ${unreadCount} unread` : ''}`}
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-600 px-1 text-[9px] font-bold text-white animate-pulse">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </NavLink>

              <div className="hidden text-right sm:block border-l border-slate-200 pl-3">
                <p className="max-w-40 truncate text-xs font-semibold text-slate-800">{user?.name}</p>
                <p className="text-[10px] text-slate-500">{roleNames[user?.role ?? '']}</p>
              </div>

              <button
                onClick={() => {
                  logout()
                  navigate('/login', { replace: true })
                }}
                className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden md:inline">Sign out</span>
              </button>
            </div>
          </header>

          {/* Main Scrollable Content */}
          <main className="flex-1 p-4 sm:p-6 lg:p-8 bg-slate-100/70">
            <div className="max-w-7xl mx-auto">
              <Outlet />
            </div>
          </main>

          <SyntheticFooter />
          <CopilotModal open={copilotOpen} onClose={() => setCopilotOpen(false)} />
        </div>
      </div>
    </div>
  )
}
