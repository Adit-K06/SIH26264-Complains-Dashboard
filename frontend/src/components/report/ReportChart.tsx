import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ReportTable } from '../../lib/reportTable'

/** Bar chart of one numeric column against the first column (first 30 rows). */
export default function ReportChart({ table, metric }: { table: ReportTable; metric: number }) {
  const data = table.rows.slice(0, 30).map((r) => ({
    name: String(r[0] ?? ''),
    value: Number(r[metric] ?? 0),
  }))
  const label = table.columns[metric] ?? 'Value'

  return (
    <div className="h-64 w-full" role="img" aria-label={`Bar chart of ${label}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" name={label} fill="#0f766e" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
