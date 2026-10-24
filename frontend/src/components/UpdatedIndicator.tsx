import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { REFRESH_MS } from '../hooks/useDashboardData'

interface Props {
  updatedAt: number
  isFetching: boolean
  onRefresh: () => void
}

export default function UpdatedIndicator({ updatedAt, isFetching, onRefresh }: Props) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const secs = updatedAt ? Math.max(0, Math.round((now - updatedAt) / 1000)) : null

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span aria-live="polite">
        {secs === null ? 'Loading…' : `Updated ${secs}s ago`} · auto-refresh {REFRESH_MS / 1000}s
      </span>
      <button
        type="button"
        onClick={onRefresh}
        className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:bg-slate-50"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} aria-hidden />
        Refresh
      </button>
    </div>
  )
}
