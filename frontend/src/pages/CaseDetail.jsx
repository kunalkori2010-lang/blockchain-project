import { useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import api from '../api/client.js'
import StatCard from '../components/StatCard.jsx'
import RiskBar from '../components/RiskBar.jsx'
import GraphView from '../components/GraphView.jsx'
import SuspectCard from '../components/SuspectCard.jsx'

const badge = (l) => l === 'CRITICAL' ? 'bg-red-600' : l === 'HIGH' ? 'bg-orange-500' : l === 'MEDIUM' ? 'bg-yellow-500 text-black' : 'bg-emerald-600'

export default function CaseDetail() {
  const { caseId } = useParams()
  const loc = useLocation()
  const [data, setData] = useState(loc.state || null)
  const [meta, setMeta] = useState(null)
  const [err, setErr] = useState('')
  const nav = useNavigate()

  useEffect(() => {
    setErr('')
    api.get(`/api/cases/${caseId}`).then((r) => {
      setMeta(r.data)
      if (!loc.state) {
        // re-analyse quickly for full graph view
        api.post('/api/analyze', {
          case_id: caseId, wallet_address: r.data.wallet_address, network: r.data.network,
        }).then((a) => setData(a.data))
          .catch((e) => setErr('Analysis failed: ' + (e?.response?.data?.detail || e.message)))
      }
    }).catch((e) => {
      if (e?.response?.status === 401) { localStorage.clear(); nav('/login') }
      else setErr('Could not load case: ' + (e?.response?.data?.detail || e.message))
    })
    // eslint-disable-next-line
  }, [caseId])

  if (err && !data) return (
    <div className="rounded-2xl bg-red-950/50 border border-red-800 p-6 text-sm">
      <div className="font-bold text-red-200">⚠️ {err}</div>
      <div className="mt-3 flex gap-2">
        <button className="px-4 py-2 rounded-xl bg-slate-800" onClick={() => window.location.reload()}>Retry</button>
        <button className="px-4 py-2 rounded-xl bg-slate-800" onClick={() => nav('/')}>Back to Dashboard</button>
      </div>
    </div>
  )
  if (!data) return <div className="text-sm text-slate-400">Loading investigation…</div>
  const riskPct = (k) => Math.min(100, Math.round(((data.risk.indicators?.[k] || 0) / 25) * 100))
  const chart = Object.entries(data.risk.indicators || {}).map(([k, v]) => ({ name: k.replace(/_/g, ' '), pts: v }))

  // Fund-flow tracing: every counterparty the suspect touched, ranked by volume
  const suspectAddr = (meta?.wallet_address || '').toLowerCase()
  const entityByAddr = Object.fromEntries((data.graph.nodes || []).map((n) => [n.id.toLowerCase(), n]))
  const cpMap = {}
  ;(data.transactions || []).forEach((t) => {
    const f = (t.from_address || '').toLowerCase(), to = (t.to_address || '').toLowerCase()
    let other = null, dir = ''
    if (f === suspectAddr) { other = t.to_address; dir = 'out' }
    else if (to === suspectAddr) { other = t.from_address; dir = 'in' }
    else return
    const k = other.toLowerCase()
    cpMap[k] = cpMap[k] || { address: other, txs: 0, volume: 0, in_n: 0, out_n: 0 }
    cpMap[k].txs += 1; cpMap[k].volume += Number(t.amount) || 0
    if (dir === 'in') cpMap[k].in_n += 1; else cpMap[k].out_n += 1
  })
  const counterparties = Object.values(cpMap).sort((a, b) => b.volume - a.volume).slice(0, 10)

  const changeStatus = async (s) => {
    let note = ''
    if (s === 'confirmed-fraud') {
      note = window.prompt('Corroborating evidence REQUIRED (FIR no / VASP reply ref / bank lien ref):', '') || ''
      if (!note.trim()) return
    }
    try {
      const r = await api.put(`/api/cases/${data.case_id}/status`, { status: s, note })
      setMeta({ ...meta, status: r.data.status })
    } catch (e) { setErr('Status update failed: ' + (e?.response?.data?.detail || e.message)) }
  }

  const downloadReport = async () => {    try {
      const r = await api.get(`/api/report/${data.case_id}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url; a.download = `${data.case_id}_report.pdf`
      document.body.appendChild(a); a.click(); a.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) { setErr('Report download failed: ' + (e?.response?.data?.detail || e.message)) }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-extrabold">{data.case_id}</h1>
        <span className={`text-xs px-3 py-1 rounded-full font-black ${badge(data.risk.level)}`}>
          {data.risk.level} · {data.risk.score}/100
        </span>
        <span className="text-[11px] text-slate-400">source: {data.source} · {data.network || meta?.network} · read-only, no signing</span>
        <button className="ml-auto px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold text-sm"
          onClick={downloadReport}>📄 Generate Investigation Report</button>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-400">Human verdict — case status:</span>
        <span className="px-2 py-1 rounded-full bg-slate-800 font-bold">{meta?.status || 'open'}</span>
        {['under-investigation', 'confirmed-fraud', 'closed'].filter((s) => s !== meta?.status).map((s) => (
          <button key={s} className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700" onClick={() => changeStatus(s)}>{s}</button>
        ))}
      </div>

      <SuspectCard data={data} meta={meta} />

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <div className="text-4xl font-black">{data.risk.score}<span className="text-base text-slate-400">/100</span></div>
        <div className="h-3 rounded-full bg-slate-800 overflow-hidden mt-2">
          <div className="h-full bg-gradient-to-r from-emerald-400 via-yellow-400 to-red-500" style={{ width: `${data.risk.score}%` }} />
        </div>
        <div className="text-[11px] text-slate-400 mt-2">Prototype weights are assumptions (shown below) · indicators ≠ proof of wrongdoing.</div>
      </div>

      {(data.risk.level === 'CRITICAL' || data.risk.level === 'HIGH') && (
        <div className={`rounded-2xl border p-4 text-sm font-semibold ${data.risk.level === 'CRITICAL' ? 'bg-red-950/60 border-red-700 text-red-200' : 'bg-orange-950/60 border-orange-700 text-orange-200'}`}>
          🚨 {data.risk.level}-RISK ACTIVITY — {data.case_id}: {data.risk.reasons[0] || 'multiple suspicious indicators'} (risk {data.risk.score}/100).
          <span className="font-normal"> Recommended action: preserve evidence → verify entity via VASP → generate report.</span>
        </div>
      )}

      {err && (
        <div className="rounded-2xl border border-red-800 bg-red-950/50 p-3 text-xs text-red-200">⚠️ {err}</div>
      )}

      {(meta?.incident_time_gmt || meta?.suspect_ip || meta?.ref_12digit || meta?.suspect_name || meta?.suspect_phone || meta?.suspect_email || meta?.suspect_account) && (
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 text-sm">
          <div className="font-bold mb-2">Subject profile &amp; off-chain intel <span className="font-normal text-[11px] text-slate-400">(investigator-provided — cannot be derived from blockchain data)</span></div>
          <div className="grid md:grid-cols-3 gap-3 text-xs">
            <div><div className="text-slate-400 uppercase tracking-widest text-[10px]">Name / alias</div><div>{meta?.suspect_name || '— not recorded'}{meta?.suspect_alias ? ` (${meta.suspect_alias})` : ''}</div></div>
            <div><div className="text-slate-400 uppercase tracking-widest text-[10px]">Phone (masked)</div><div className="font-mono">{meta?.suspect_phone || '— not recorded'}</div></div>
            <div><div className="text-slate-400 uppercase tracking-widest text-[10px]">Email (masked)</div><div className="font-mono break-all">{meta?.suspect_email || '— not recorded'}</div></div>
            <div><div className="text-slate-400 uppercase tracking-widest text-[10px]">Account note</div><div className="font-mono">{meta?.suspect_account || '—'}</div></div>
            <div><div className="text-slate-400 uppercase tracking-widest text-[10px]">Incident (GMT/UTC)</div><div className="font-mono">{meta?.incident_time_gmt || '—'}</div></div>
            <div><div className="text-slate-400 uppercase tracking-widest text-[10px]">12-digit ref (masked)</div><div className="font-mono">{meta?.ref_12digit || '— not recorded'}</div></div>
          </div>
          {meta?.suspect_ip && (
            <div className="mt-3 rounded-xl bg-slate-800 p-3 text-xs">
              <span className="font-bold">🌐 Suspect IP {meta.suspect_ip}</span>
              <span className="text-slate-400"> · v{meta.suspect_ip_intel?.version} · scope: {meta.suspect_ip_intel?.scope || '—'}</span>
              {meta.suspect_ip_intel?.reverse_dns && <span className="text-slate-400"> · rDNS: <span className="font-mono">{meta.suspect_ip_intel.reverse_dns}</span></span>}
              <div className="text-slate-500 mt-1">Registry data only — describes the address, not the person. Identity needs VASP/ISP records via lawful process.</div>
            </div>
          )}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        <StatCard label="Risk score" value={data.risk.score} sub={data.risk.level} />
        <StatCard label="Transactions" value={data.tx_count} sub={`${data.features.unique_counterparties} counterparties`} />
        <StatCard label="Connections" value={data.graph.nodes.length} sub={`${data.graph.edges.length} fund-flow edges`} />
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <div className="font-bold mb-1">Transaction graph — suspect → hops → possible exchange</div>
        {data.trace_metrics?.nearest_endpoint && (
          <div className="text-xs text-emerald-300 mb-2">
            Shortest fund-flow path to {data.trace_metrics.nearest_endpoint.label}: <b>{data.trace_metrics.nearest_endpoint.hops} hops</b>
            <span className="text-slate-400"> · max depth traced: {data.trace_metrics.max_depth} (limit {data.max_hops})</span>
          </div>
        )}
        <GraphView graph={data.graph} suspect={meta?.wallet_address || data.transactions?.[0]?.to_address} />
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <div className="font-bold mb-1">Trace targets — key counterparties by volume</div>
        <div className="text-[11px] text-slate-400 mb-2">Everyone the suspect transacted with directly. Follow these addresses to trace the fund flow; request VASP KYC for exchange-labelled ones.</div>
        <div className="overflow-auto max-h-64">
          <table className="w-full text-[11px] font-mono">
            <thead className="text-slate-400 sticky top-0 bg-slate-900"><tr><th className="text-left p-2">Counterparty</th><th className="text-left p-2">Entity</th><th className="text-left p-2">Txs</th><th className="text-left p-2">In/Out</th><th className="text-left p-2">Volume</th></tr></thead>
            <tbody>
              {counterparties.map((c) => (
                <tr key={c.address} className="border-t border-slate-800">
                  <td className="p-2 break-all">{c.address.slice(0, 16)}…</td>
                  <td className="p-2">{entityByAddr[c.address.toLowerCase()]?.entity || entityByAddr[c.address.toLowerCase()]?.type || '—'}</td>
                  <td className="p-2">{c.txs}</td>
                  <td className="p-2">{c.in_n}/{c.out_n}</td>
                  <td className="p-2">{c.volume.toFixed(4)} ETH</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
          <div className="font-bold mb-3">Risk analysis</div>
          <RiskBar label="Rapid transfers" pct={Math.max(riskPct('rapid_movement'), riskPct('burst'))} />
          <RiskBar label="Multiple wallets (fan-out)" pct={riskPct('fanout')} />
          <RiskBar label="Exchange interaction" pct={riskPct('exchange_touch')} />
          <RiskBar label="Fund splitting / consolidation" pct={riskPct('consolidation')} />
          <RiskBar label="Unusual behaviour + anomaly" pct={Math.min(100, riskPct('unusual') + Math.round((data.risk.anomaly_nudge || 0) * 40))} />
          <div className="mt-3 text-xs">
            {data.risk.reasons.map((r, i) => <div key={i} className="text-slate-300">⚠️ {r}</div>)}
          </div>
          <div className="font-bold mt-4 mb-1 text-sm">Clue study guide — what each clue means</div>
          {(data.risk.guidance || []).map((g, i) => (
            <div key={i} className="rounded-xl bg-slate-800 p-3 mt-2 text-xs">
              <div className="font-bold">🔎 {g.title} <span className="text-slate-400">(+{g.points})</span></div>
              {g.detail && <div className="font-mono text-[11px] text-slate-400 mt-1">Observed: {g.detail}</div>}
              <div className="text-slate-300 mt-1">{g.what}</div>
              <div className="text-slate-400 mt-1">Why it matters: {g.why}</div>
              <div className="text-indigo-300 mt-1">Next step: {g.next}</div>
            </div>
          ))}
          <div className="text-[11px] text-slate-500 mt-2">No algorithm can declare 100% fraud from chain data alone — only a human investigator with corroborating evidence can, via the case-status verdict below.</div>
          <div className="mt-3 text-xs">
            <div className="font-bold mb-1 text-slate-300">Indicator weights (prototype assumptions — adjustable via PUT /api/config/weights)</div>
            <div className="grid grid-cols-2 gap-x-4">
              {Object.entries(data.risk.weights || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-slate-800 py-1 text-slate-300">
                  <span>{k.replace(/_/g, ' ')}</span><b>{v}</b>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-3 h-44">
            <ResponsiveContainer><BarChart data={chart}><XAxis dataKey="name" tick={{ fontSize: 9, fill: '#94a3b8' }} interval={0} angle={-15} height={50} /><YAxis /><Tooltip /><Bar dataKey="pts" fill="#6366f1" /></BarChart></ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
          <div className="font-bold mb-2">Possible connected service</div>
          {data.entities_hit.length === 0 && <div className="text-xs text-slate-400">No known-entity match in analysed hops.</div>}
          {data.entities_hit.map((e, i) => (
            <div key={i} className="rounded-xl bg-slate-800 p-3 mb-2 text-sm">
              <div className="font-bold">🏦 {e.label} <span className="text-[11px] font-normal text-slate-400">({e.category})</span></div>
              <div className="font-mono text-[11px] text-slate-300 break-all">{e.address}</div>
              <div className="text-xs text-slate-400 mt-1">Confidence: pattern + seed mapping (verify with VASP). {e.confidence_note}</div>
              <div className="text-xs mt-1">Reason: repeated interaction · fund-flow relationship · address/entity mapping</div>
            </div>
          ))}
          <div className="font-bold mt-4 mb-2">Fund-flow timeline</div>
          <div className="max-h-64 overflow-auto text-xs space-y-2">
            {data.timeline.map((t, i) => (
              <div key={i} className="border-l-2 border-indigo-500 pl-3">
                <div className="text-slate-400">{t.timestamp?.replace('T', ' ').slice(0, 16)}</div>
                <div>{t.text}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <div className="font-bold mb-2">Transaction explorer (evidence hashes)</div>
        <div className="overflow-auto max-h-80">
          <table className="w-full text-[11px] font-mono">
            <thead className="text-slate-400 sticky top-0 bg-slate-900"><tr><th className="text-left p-2">Time</th><th className="text-left p-2">From → To</th><th className="text-left p-2">Amount</th><th className="text-left p-2">Hash</th></tr></thead>
            <tbody>
              {data.transactions.slice(0, 100).map((t) => (
                <tr key={t.tx_hash} className="border-t border-slate-800">
                  <td className="p-2 whitespace-nowrap">{t.timestamp?.slice(5, 16).replace('T', ' ')}</td>
                  <td className="p-2 break-all">{t.from_address.slice(0, 10)}… → {t.to_address.slice(0, 10)}…</td>
                  <td className="p-2">{t.amount} {t.token}</td>
                  <td className="p-2 break-all text-slate-400">{t.tx_hash.slice(0, 18)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
