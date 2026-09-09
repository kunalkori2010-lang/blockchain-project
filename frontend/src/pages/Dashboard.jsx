import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client.js'

const badge = (l) => l === 'CRITICAL' ? 'bg-red-600' : l === 'HIGH' ? 'bg-orange-500' : l === 'MEDIUM' ? 'bg-yellow-500 text-black' : 'bg-emerald-600'

export default function Dashboard() {
  const [cases, setCases] = useState([])
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState(null)
  const [q, setQ] = useState('')
  const load = (query) => {
    api.get(query ? '/api/cases/search' : '/api/cases', { params: query ? { q: query } : {} })
      .then((r) => setCases(r.data)).catch(() => {})
  }
  useEffect(() => {
    load('')
    api.get('/api/alerts').then((r) => setAlerts(r.data)).catch(() => {})
    api.get('/api/stats/summary').then((r) => setStats(r.data)).catch(() => {})
  }, [])
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-xl font-extrabold">Investigations</h1>
        <span className="text-xs text-slate-400">{cases.length} cases</span>
        <input className="ml-auto rounded-xl bg-slate-800 px-4 py-2 text-sm outline-none w-56" placeholder="Search ID / wallet / notes…"
          value={q} onChange={(e) => { setQ(e.target.value); load(e.target.value) }} />
        <Link to="/new" className="px-4 py-2 rounded-xl bg-indigo-600 font-bold text-sm">🔍 New Investigation</Link>
      </div>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 text-sm">
          {[['Total cases', stats.total_cases], ['Critical + High', stats.critical_high],
            ['Avg risk score', stats.avg_score], ['Networks', Object.keys(stats.by_network || {}).join(', ') || '—'],
          ].map(([k, v]) => (
            <div key={k} className="rounded-xl bg-slate-900 border border-slate-800 px-4 py-2">
              <div className="text-[10px] uppercase tracking-widest text-slate-400">{k}</div>
              <div className="font-black text-lg">{v}</div>
            </div>
          ))}
        </div>
      )}
      {alerts.length > 0 && (
        <div className="rounded-2xl border border-red-800 bg-red-950/50 p-4 mb-4 text-sm">
          <span className="font-black text-red-300">🚨 {alerts.length} HIGH-RISK ALERT{alerts.length > 1 ? 'S' : ''}</span>
          <div className="mt-2 space-y-1">
            {alerts.slice(0, 5).map((a) => (
              <div key={a.case_id}>
                <Link className="text-red-200 underline" to={`/case/${a.case_id}`}>{a.case_id}</Link>
                <span className="text-red-300/80"> · {a.severity} {a.score}/100 — {a.headline}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {cases.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-700 p-8 text-center text-slate-400 text-sm">
          No cases yet. Click <b>New Investigation</b> and enter a suspect wallet — e.g. <code>0xABC123…</code> (any address works in prototype mock mode).
        </div>
      )}
      <div className="grid md:grid-cols-2 gap-4">
        {cases.map((c) => (
          <Link key={c.case_id} to={`/case/${c.case_id}`} className="rounded-2xl bg-slate-900 border border-slate-800 p-5 hover:border-indigo-500">
            <div className="flex items-center gap-2">
              <span className="font-bold">{c.case_id}</span>
              {c.risk_level && <span className={`text-[11px] px-2 py-0.5 rounded-full font-bold ${badge(c.risk_level)}`}>{c.risk_level} {c.risk_score}</span>}
              <span className="ml-auto text-[11px] text-slate-400">{c.network}</span>
            </div>
            <div className="font-mono text-xs text-slate-300 mt-2 break-all">{c.wallet_address}</div>
            <div className="text-xs text-slate-500 mt-1">₹{c.fraud_amount_inr} · {c.incident_date} · {c.created_at?.slice(0, 10)}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
