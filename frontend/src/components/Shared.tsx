import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Clock3, LoaderCircle } from 'lucide-react'
import type { CaseStatus } from '../types'

export const FOOTER_TEXT = 'Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.'

export function SyntheticFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white/90 px-5 py-3 text-center text-xs text-slate-500 backdrop-blur-xs">
      <div className="flex flex-wrap items-center justify-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span>{FOOTER_TEXT}</span>
        <span className="text-slate-300">|</span>
        <span className="font-mono text-slate-400">SIH-26264 AICTE Coordination Layer</span>
      </div>
    </footer>
  )
}

export function PageHeader({ title, helper, action }: { title: string; helper: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">{title}</h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-600">{helper}</p>
      </div>
      {action && <div className="flex items-center gap-2 shrink-0">{action}</div>}
    </div>
  )
}

export function LoadingState({ label = 'Loading information…' }: { label?: string }) {
  return (
    <div className="flex min-h-36 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white p-8 text-sm font-medium text-slate-600 shadow-sm">
      <LoaderCircle className="h-5 w-5 animate-spin text-blue-600" aria-hidden="true" />
      {label}
    </div>
  )
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50/80 p-4 text-sm text-red-900 shadow-sm">
      <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" aria-hidden="true" />
      <div className="flex-1">
        <p className="font-bold">We could not load this information</p>
        <p className="mt-1 text-red-700">{message}</p>
        {retry && (
          <button className="mt-3 font-semibold text-red-800 underline hover:text-red-900 cursor-pointer" onClick={retry}>
            Try again
          </button>
        )}
      </div>
    </div>
  )
}

export function EmptyState({
  title = 'Nothing to show yet',
  message = 'Try changing your filters or check back later.',
}: {
  title?: string
  message?: string
}) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-xs">
      <p className="font-bold text-slate-800 text-base">{title}</p>
      <p className="mt-1.5 text-xs text-slate-500 max-w-sm mx-auto">{message}</p>
    </div>
  )
}

export function StatusBadge({ status }: { status: CaseStatus | string }) {
  const norm = String(status).toUpperCase()
  let badgeStyle = 'bg-slate-100 text-slate-700 border-slate-200'
  let dotStyle = 'bg-slate-400'
  let label = norm.replace(/_/g, ' ')

  if (norm === 'PENDING') {
    badgeStyle = 'bg-amber-50 text-amber-800 border-amber-200'
    dotStyle = 'bg-amber-500'
    label = 'Pending'
  } else if (norm === 'UNDER_PROCESS') {
    badgeStyle = 'bg-blue-50 text-blue-800 border-blue-200'
    dotStyle = 'bg-blue-600'
    label = 'Under Process'
  } else if (norm === 'DISPOSED') {
    badgeStyle = 'bg-emerald-50 text-emerald-800 border-emerald-200'
    dotStyle = 'bg-emerald-600'
    label = 'Disposed'
  } else if (norm === 'TRANSFERRED') {
    badgeStyle = 'bg-purple-50 text-purple-800 border-purple-200'
    dotStyle = 'bg-purple-600'
    label = 'Transferred'
  } else if (norm === 'ESCALATED') {
    badgeStyle = 'bg-rose-50 text-rose-800 border-rose-200 animate-pulse'
    dotStyle = 'bg-rose-600'
    label = 'Escalated'
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-bold border ${badgeStyle}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotStyle}`} />
      {label}
    </span>
  )
}

export function SlaBadge({ dueOn, status }: { dueOn?: string | null; status: CaseStatus | string }) {
  if (status === 'DISPOSED') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-bold text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="h-3 w-3" />
        Closed
      </span>
    )
  }
  if (!dueOn) return <span className="text-xs text-slate-400">No deadline</span>
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(`${dueOn}T00:00:00`)
  const days = Math.ceil((due.getTime() - today.getTime()) / 86400000)

  if (days < 0) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[11px] font-bold text-rose-700 border border-rose-200">
        <Clock3 className="h-3 w-3" />
        Overdue ({Math.abs(days)}d)
      </span>
    )
  }
  if (days <= 7) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-bold text-amber-800 border border-amber-200">
        <Clock3 className="h-3 w-3" />
        Due in {days}d
      </span>
    )
  }
  return <span className="text-xs font-medium text-slate-600">{days} days left</span>
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-slate-200/90 bg-white shadow-sm hover:shadow-md transition-shadow ${className}`}>
      {children}
    </section>
  )
}

export function SectionTitle({ title, note }: { title: string; note?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">{title}</h2>
      {note && <p className="text-xs text-slate-500 mt-0.5">{note}</p>}
    </div>
  )
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`)
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}
