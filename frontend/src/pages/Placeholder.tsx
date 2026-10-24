import { useLocation } from 'react-router-dom'

// Stand-in for pages built by other teammates. Shows the URL so you can
// verify that dashboard links carry the right filters.
export default function Placeholder({ title }: { title: string }) {
  const { pathname, search } = useLocation()
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center">
      <h1 className="text-lg font-semibold text-slate-800">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">This page is not part of the dashboard module.</p>
      <code className="mt-3 inline-block rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">
        {pathname}
        {search}
      </code>
    </div>
  )
}
