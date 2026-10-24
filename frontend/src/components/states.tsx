import { AlertTriangle, Inbox } from 'lucide-react'

export function Skeleton({ height = 160 }: { height?: number }) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="animate-pulse rounded bg-slate-100"
      style={{ height }}
    />
  )
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 text-sm text-slate-500">
      <Inbox className="h-5 w-5" aria-hidden />
      <span>{text}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-2 py-8 text-sm text-red-700"
    >
      <AlertTriangle className="h-5 w-5" aria-hidden />
      <span>{message}</span>
      <button
        type="button"
        onClick={onRetry}
        className="rounded border border-slate-300 bg-white px-3 py-1 text-slate-700 hover:bg-slate-50"
      >
        Retry
      </button>
    </div>
  )
}
