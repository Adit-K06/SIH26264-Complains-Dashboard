import { Link } from 'react-router-dom'
import type { Institution } from '../../api/institutionTypes'
import { fmtNum } from '../../lib/format'
import { casesLink } from '../../lib/institution'
import { REGIONS } from '../../lib/lookups'

const TH =
  'whitespace-nowrap bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500'

const dash = (v?: string | null) => v || '—'

export default function InstitutionTable({ rows }: { rows: Institution[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[880px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th scope="col" className={TH}>Institution</th>
            <th scope="col" className={TH}>AICTE permanent ID</th>
            <th scope="col" className={TH}>Type</th>
            <th scope="col" className={TH}>Region</th>
            <th scope="col" className={TH}>State</th>
            <th scope="col" className={`${TH} text-right`}>Total cases</th>
            <th scope="col" className={`${TH} text-right`}>Open cases</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((i) => (
            <tr key={i.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="px-3 py-2">
                <Link to={`/institutions/${i.id}`} className="font-medium text-teal hover:underline">
                  {i.name}
                </Link>
              </td>
              <td className="whitespace-nowrap px-3 py-2">{dash(i.aicte_permanent_id)}</td>
              <td className="whitespace-nowrap px-3 py-2">{dash(i.type)}</td>
              <td className="whitespace-nowrap px-3 py-2">
                {i.region_name ?? REGIONS.find((r) => r.id === i.region_id)?.label ?? '—'}
              </td>
              <td className="whitespace-nowrap px-3 py-2">{dash(i.state)}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {i.total_cases === undefined ? (
                  '—'
                ) : (
                  <Link to={casesLink(i.id)} className="text-teal hover:underline">
                    {fmtNum(i.total_cases)}
                  </Link>
                )}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {i.open_cases === undefined ? '—' : fmtNum(i.open_cases)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
