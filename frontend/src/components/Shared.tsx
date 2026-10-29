import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Clock3, LoaderCircle } from 'lucide-react'
import type { CaseStatus } from '../types'

export const FOOTER_TEXT = 'Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.'

export function SyntheticFooter() {
  return <footer className="border-t border-slate-200 bg-white px-5 py-3 text-center text-xs text-slate-500">{FOOTER_TEXT}</footer>
}

export function PageHeader({ title, helper, action }: { title: string; helper: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{helper}</p>
      </div>
      {action}
    </div>
  )
}

export function LoadingState({ label = 'Loading information…' }: { label?: string }) {
  return <div className="flex min-h-36 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600"><LoaderCircle className="h-5 w-5 animate-spin text-teal-700" aria-hidden="true" />{label}</div>
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" /><div className="flex-1"><p className="font-semibold">We could not load this information</p><p className="mt-1">{message}</p>{retry && <button className="mt-3 font-semibold underline" onClick={retry}>Try again</button>}</div></div>
}

export function EmptyState({ title = 'Nothing to show yet', message = 'Try changing your filters or check back later.' }: { title?: string; message?: string }) {
  return <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center"><p className="font-semibold text-slate-800">{title}</p><p className="mt-1 text-sm text-slate-500">{message}</p></div>
}

export function StatusBadge({ status }: { status: CaseStatus | string }) {
  const key = status.toLowerCase().replace(/_/g, '-')
  const label = status === 'UNDER_PROCESS' ? 'Under process' : status.charAt(0) + status.slice(1).toLowerCase()
  return <span className={`status-badge status-${key}`}>{label}</span>
}

export function SlaBadge({ dueOn, status }: { dueOn?: string | null; status: CaseStatus | string }) {
  if (status === 'DISPOSED') return <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2.5 py-1 text-xs font-semibold text-green-700"><CheckCircle2 className="h-3.5 w-3.5" />Closed</span>
  if (!dueOn) return <span className="text-xs text-slate-500">No due date</span>
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(`${dueOn}T00:00:00`)
  const days = Math.ceil((due.getTime() - today.getTime()) / 86400000)
  if (days < 0) return <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700"><Clock3 className="h-3.5 w-3.5" />Overdue</span>
  if (days <= 7) return <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800"><Clock3 className="h-3.5 w-3.5" />Due in {days}d</span>
  return <span className="text-xs text-slate-600">{days} days left</span>
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</section>
}

export function SectionTitle({ title, note }: { title: string; note?: string }) {
  return <div className="mb-3"><h2 className="text-base font-semibold text-slate-900">{title}</h2>{note && <p className="text-xs text-slate-500">{note}</p>}</div>
}

export function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(date)
}

export function formatDateTime(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
