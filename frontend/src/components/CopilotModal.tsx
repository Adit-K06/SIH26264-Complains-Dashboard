import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  ArrowRight, CornerDownLeft, Loader2, Search, Sparkles, X,
} from 'lucide-react'
import { copilotApi } from '../api'
import type { CopilotResponse } from '../types'

interface CopilotModalProps {
  open: boolean
  onClose: () => void
}

const suggestedQueries = [
  'Show cases beyond SLA',
  'Active RB vs PGRC overlaps',
  'Regulation Bureau workload',
  'Complaints for Synthetic Aster Institute',
  'Find scholarship delay grievances',
  'List cases under process',
]

export function CopilotModal({ open, onClose }: CopilotModalProps) {
  const navigate = useNavigate()
  const [queryText, setQueryText] = useState('')
  const [history, setHistory] = useState<CopilotResponse[]>([])

  const mutation = useMutation({
    mutationFn: (q: string) => copilotApi.query(q),
    onSuccess: (data) => {
      setHistory((prev) => [data, ...prev])
    },
  })

  if (!open) return null

  function handleSubmit(event?: React.FormEvent) {
    if (event) event.preventDefault()
    const trimmed = queryText.trim()
    if (!trimmed || mutation.isPending) return
    mutation.mutate(trimmed)
  }

  function handleQuickQuery(q: string) {
    setQueryText(q)
    mutation.mutate(q)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" onClick={onClose} />

      {/* Modal Dialog */}
      <div className="relative flex max-h-[88vh] w-full max-w-3xl flex-col rounded-2xl bg-white shadow-2xl ring-1 ring-slate-900/10">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-teal-500 to-[#102b46] text-white shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">AICTE Query Copilot</h2>
                <span className="rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-teal-800 ring-1 ring-inset ring-teal-600/20">
                  Offline NLP Assistant
                </span>
              </div>
              <p className="text-xs text-slate-500">Ask natural questions across complaints, bureaus, overlaps, and SLAs.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Query Input Bar */}
        <form onSubmit={handleSubmit} className="border-b border-slate-100 p-4">
          <div className="relative flex items-center">
            <Search className="pointer-events-none absolute left-3.5 h-5 w-5 text-slate-400" />
            <input
              type="text"
              className="w-full rounded-xl border border-slate-300 py-3 pl-11 pr-24 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20"
              placeholder="e.g., 'Show overdue cases', 'Find RB and PGRC overlaps'…"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              autoFocus
            />
            <button
              type="submit"
              disabled={mutation.isPending || !queryText.trim()}
              className="absolute right-2 flex items-center gap-1 rounded-lg bg-[#102b46] px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-teal-800 disabled:opacity-40"
            >
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Ask</span>
                  <CornerDownLeft className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>

          {/* Quick Prompts */}
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-semibold text-slate-400">Try:</span>
            {suggestedQueries.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => handleQuickQuery(item)}
                className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-700 transition hover:bg-teal-50 hover:text-teal-900"
              >
                {item}
              </button>
            ))}
          </div>
        </form>

        {/* Content & History Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {history.length === 0 && !mutation.isPending && (
            <div className="py-12 text-center">
              <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-800">
                <Sparkles className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-800">Ready for National AICTE Queries</h3>
              <p className="mx-auto mt-1 max-w-md text-xs text-slate-500">
                Ask about specific institutions, regulatory overlaps between RB and PGRC, overdue timeline bottlenecks, or bureau workloads.
              </p>
            </div>
          )}

          {mutation.isPending && (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin text-teal-700" />
              <span>Analyzing AICTE database…</span>
            </div>
          )}

          {history.map((resp, idx) => (
            <div key={idx} className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 shadow-sm space-y-3">
              {/* Question & Intent */}
              <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
                <p className="text-xs font-bold text-slate-700">“{resp.query}”</p>
                <span className="rounded bg-teal-100 px-2 py-0.5 text-[10px] font-bold text-teal-900">
                  {resp.intent}
                </span>
              </div>

              {/* Answer Header */}
              {resp.highlight && (
                <div className="inline-block rounded-md bg-[#102b46] px-2.5 py-1 text-xs font-bold text-white shadow-xs">
                  {resp.highlight}
                </div>
              )}
              <p className="text-xs leading-relaxed text-slate-800">{resp.answer}</p>

              {/* Matching Items (Cases / Overlaps / Institutions) */}
              {resp.items && resp.items.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Matching Records</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {resp.items.map((item) => (
                      <Link
                        key={item.id}
                        to={item.link}
                        onClick={onClose}
                        className="group flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-2.5 transition hover:border-teal-400 hover:shadow-xs"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-xs font-bold text-[#153a5b] group-hover:text-teal-800">
                            {item.title}
                          </p>
                          {item.subtitle && (
                            <p className="mt-0.5 truncate text-[11px] text-slate-500">{item.subtitle}</p>
                          )}
                        </div>
                        {item.status && (
                          <div className="mt-2 flex items-center justify-between">
                            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                              {item.status}
                            </span>
                            <ArrowRight className="h-3.5 w-3.5 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-teal-700" />
                          </div>
                        )}
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Button */}
              {resp.action && (
                <div className="pt-2">
                  <button
                    onClick={() => {
                      onClose()
                      navigate(resp.action!.link)
                    }}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-teal-800"
                  >
                    <span>{resp.action.label}</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-200 px-6 py-3 bg-slate-50 rounded-b-2xl flex items-center justify-between text-[11px] text-slate-500">
          <span>AICTE Complaint Coordination Engine • SIH26264</span>
          <span>Fast Local NLP • Deterministic Intent</span>
        </div>
      </div>
    </div>
  )
}
