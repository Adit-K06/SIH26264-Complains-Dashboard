import { useState } from 'react'
import { SAMPLE_CASE } from '../../lib/importCsv'

export default function CurlSample() {
  const [copied, setCopied] = useState(false)

  const cmd = [
    `curl -X POST "${window.location.origin}/api/v1/ingest/cases" \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -H "X-API-Key: <YOUR_BUREAU_API_KEY>" \\`,
    `  -d '${JSON.stringify(SAMPLE_CASE, null, 2)}'`,
  ].join('\n')

  async function copy() {
    try {
      await navigator.clipboard.writeText(cmd)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2">
        <h2 className="text-sm font-semibold text-slate-800">Ingest API (for bureau systems)</h2>
        <button
          type="button"
          onClick={() => void copy()}
          className="rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div className="space-y-2 px-4 py-3">
        <pre className="overflow-x-auto rounded bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
          <code>{cmd}</code>
        </pre>
        <p className="text-xs text-slate-600">
          Each bureau uses its own API key; replace the placeholder. Sending the same case_no for the same bureau twice
          is safe: the first call creates the case (201) and repeats are ignored as duplicates (200). All values above
          are synthetic.
        </p>
      </div>
    </section>
  )
}
