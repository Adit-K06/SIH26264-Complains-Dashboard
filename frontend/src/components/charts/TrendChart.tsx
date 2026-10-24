import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { MonthlyPoint } from '../../api/types'
import { fmtMonth } from '../../lib/format'

export default function TrendChart({ points }: { points: MonthlyPoint[] }) {
  return (
    <div role="img" aria-label="Monthly cases received versus disposed, line chart">
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={points} margin={{ left: 0, right: 16, top: 4 }}>
          <CartesianGrid vertical={false} stroke="#e2e8f0" />
          <XAxis
            dataKey="month"
            tickFormatter={fmtMonth}
            tick={{ fontSize: 12, fill: '#475569' }}
          />
          <YAxis tick={{ fontSize: 12, fill: '#475569' }} width={40} />
          <Tooltip labelFormatter={(l) => fmtMonth(String(l))} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="received"
            name="Received"
            stroke="#0f2a4a"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="disposed"
            name="Disposed"
            stroke="#16a34a"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
