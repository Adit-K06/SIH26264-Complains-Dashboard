import { Link } from 'react-router-dom'
import { Link2 } from 'lucide-react'
import { flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'
import type { ColumnDef } from '@tanstack/react-table'
import type { CaseRow } from '../api/types'
import { fmtDate } from '../lib/format'
import SlaBadge from './SlaBadge'
import StatusBadge from './StatusBadge'

const dash = (v?: string | null) => v || '—'

const columns: ColumnDef<CaseRow>[] = [
  {
    id: 'case_no',
    header: 'Case no.',
    cell: ({ row }) => (
      <Link to={`/cases/${row.original.id}`} className="font-medium text-teal hover:underline">
        {row.original.case_no}
      </Link>
    ),
  },
  { id: 'institution', header: 'Institution', cell: ({ row }) => dash(row.original.institution_name) },
  { id: 'bureau', header: 'Bureau', cell: ({ row }) => dash(row.original.bureau_code) },
  { id: 'category', header: 'Category', cell: ({ row }) => dash(row.original.category_name) },
  { id: 'status', header: 'Status', cell: ({ row }) => <StatusBadge status={row.original.status} /> },
  { id: 'priority', header: 'Priority', cell: ({ row }) => dash(row.original.priority) },
  { id: 'received', header: 'Received', cell: ({ row }) => fmtDate(row.original.received_on) },
  { id: 'last_action', header: 'Last action', cell: ({ row }) => fmtDate(row.original.last_action_on) },
  { id: 'due', header: 'Due', cell: ({ row }) => fmtDate(row.original.expected_disposal_on) },
  {
    id: 'sla',
    header: 'SLA',
    cell: ({ row }) => (
      <SlaBadge
        status={row.original.status}
        expected_disposal_on={row.original.expected_disposal_on}
        received_on={row.original.received_on}
      />
    ),
  },
  {
    id: 'linked',
    header: 'Linked',
    cell: ({ row }) =>
      row.original.link_group_id ? (
        <span title="Linked with other cases" className="inline-flex text-teal">
          <Link2 className="h-4 w-4" aria-label="Linked with other cases" />
        </span>
      ) : null,
  },
]

const TH =
  'whitespace-nowrap bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500'

export default function CasesTable({ rows }: { rows: CaseRow[] }) {
  // Pagination happens on the server, so the table only renders the rows it is given.
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
  })

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[960px] border-collapse text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-slate-200">
              {hg.headers.map((h) => (
                <th key={h.id} scope="col" className={TH}>
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((r) => (
            <tr key={r.id} className="border-b border-slate-100 hover:bg-slate-50">
              {r.getVisibleCells().map((c) => (
                <td key={c.id} className="whitespace-nowrap px-3 py-2">
                  {flexRender(c.column.columnDef.cell, c.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
