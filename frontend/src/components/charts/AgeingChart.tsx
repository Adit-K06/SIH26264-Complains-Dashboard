import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { AgeingBucket } from '../../api/types'

// Older buckets get warmer colours: teal, teal, teal, amber, red.
const COLORS = ['#0e7c86', '#0e7c86', '#0e7c86', '#d97706', '#dc2626']

export default function AgeingChart({ buckets }: { buckets: AgeingBucket[] }) {
  return (
    <div role="img" aria-label="Open cases by age in days, bar chart">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={buckets} margin={{ left: 0, right: 8, top: 16 }}>
          <CartesianGrid vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="bucket" tick={{ fontSize: 12, fill: '#475569' }} />
          <YAxis tick={{ fontSize: 12, fill: '#475569' }} width={40} />
          <Tooltip formatter={(v) => [String(v), 'Cases']} labelFormatter={(l) => `${l} days`} />
          <Bar dataKey="count" name="Cases" isAnimationActive={false}>
            {buckets.map((b, i) => (
              <Cell key={b.bucket} fill={COLORS[Math.min(i, COLORS.length - 1)]} />
            ))}
            <LabelList dataKey="count" position="top" fontSize={12} fill="#334155" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
