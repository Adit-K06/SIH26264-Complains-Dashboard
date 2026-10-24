import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { WorkloadRow } from '../../api/types'
import { STATUSES, STATUS_COLOR, STATUS_LABEL } from '../../lib/constants'
import type { CaseStatus } from '../../lib/constants'

type Row = { bureau: string } & Partial<Record<CaseStatus, number>>

export default function WorkloadChart({ rows }: { rows: WorkloadRow[] }) {
  const data: Row[] = rows.map((r) => ({ bureau: r.bureau, ...r.counts }))
  return (
    <div role="img" aria-label="Bureau-wise workload by status, stacked bars">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 16 }}>
          <CartesianGrid horizontal={false} stroke="#e2e8f0" />
          <XAxis type="number" tick={{ fontSize: 12, fill: '#475569' }} />
          <YAxis
            type="category"
            dataKey="bureau"
            width={80}
            tick={{ fontSize: 12, fill: '#475569' }}
          />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {STATUSES.map((s) => (
            <Bar
              key={s}
              dataKey={s}
              name={STATUS_LABEL[s]}
              stackId="status"
              fill={STATUS_COLOR[s]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
