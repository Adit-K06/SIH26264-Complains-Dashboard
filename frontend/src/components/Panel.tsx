import type { ReactNode } from 'react'

interface Props {
  title: string
  subtitle?: string
  action?: ReactNode
  className?: string
  children: ReactNode
}

export default function Panel({ title, subtitle, action, className = '', children }: Props) {
  return (
    <section className={`min-w-0 rounded-md border border-slate-200 bg-white ${className}`}>
      <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-2.5">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
        {action}
      </header>
      <div className="p-4">{children}</div>
    </section>
  )
}
