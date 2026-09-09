import { useEffect, useState } from 'react'
import api from '../api/client.js'

export default function Audit() {
  const [rows, setRows] = useState([])
  const [actor, setActor] = useState('')
  const load = () => {
    api.get('/api/audit', { params: { limit: 200, ...(actor ? { actor } : {}) } })
      .then((r) => setRows(r.data)).catch(() => {})
  }
  useEffect(() => { load() }, []) // eslint-disable-line
  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <h1 className="text-xl font-extrabold">Audit Trail</h1>
        <span className="text-xs text-slate-400">{rows.length} events · logins, analyses, reports</span>
        <div className="ml-auto flex gap-2">
          <input className="rounded-xl bg-slate-800 px-4 py-2 text-sm outline-none" placeholder="Filter by actor…"
            value={actor} onChange={(e) => setActor(e.target.value)} />
          <button className="px-4 py-2 rounded-xl bg-slate-800 text-sm" onClick={load}>Filter</button>
        </div>
      </div>
      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden">
        <table className="w-full text-xs">
          <thead className="text-slate-400 text-left"><tr>
            <th className="p-3">Time (UTC)</th><th className="p-3">Actor</th><th className="p-3">Action</th><th className="p-3">Detail</th>
          </tr></thead>
          <tbody className="font-mono">
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-slate-800">
                <td className="p-3 whitespace-nowrap">{r.created_at?.replace('T', ' ').slice(0, 19)}</td>
                <td className="p-3">{r.actor}</td>
                <td className="p-3 text-indigo-300">{r.action}</td>
                <td className="p-3 text-slate-400 break-all">{r.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <div className="p-6 text-sm text-slate-500">No events yet — logins and analyses are recorded here automatically.</div>}
      </div>
    </div>
  )
}
