const DAY_MS = 86_400_000

// "YYYY-MM-DD" -> local midnight (avoids timezone shifts of date-only strings)
function parseDate(iso: string): Date {
  return new Date(`${iso}T00:00:00`)
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return '—'
  return parseDate(iso).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

/** Whole days past the due date; 0 or negative means not yet overdue. */
export function daysOverdue(due?: string | null): number | null {
  if (!due) return null
  return Math.floor((Date.now() - parseDate(due).getTime()) / DAY_MS)
}

/** "2026-03" -> "Mar '26" */
export function fmtMonth(ym: string): string {
  const [y, m] = ym.split('-')
  const d = new Date(Number(y), Number(m) - 1, 1)
  return `${d.toLocaleString('en-IN', { month: 'short' })} '${y.slice(2)}`
}

export const fmtNum = (n: number) => n.toLocaleString('en-IN')
