import { useState } from 'react'

function avatar(address) {
  let seed = 7
  const s = (address || '').toLowerCase()
  for (let i = 0; i < s.length; i++) seed = (seed * 31 + s.charCodeAt(i)) >>> 0
  const rand = () => { seed = (seed * 1103515245 + 12345) >>> 0; return seed / 4294967296 }
  const cells = []
  for (let y = 0; y < 5; y++) {
    const row = [rand() > 0.45, rand() > 0.45, rand() > 0.45]
    cells.push([...row, ...row.slice(0, 2).reverse()])
  }
  return { cells, hue: seed % 360 }
}

export default function SuspectCard({ data, meta }) {
  const [copied, setCopied] = useState(false)
  const suspect = meta?.wallet_address || ''
  const { cells, hue } = avatar(suspect)
  const f = data.features || {}
  const net = (f.total_in || 0) - (f.total_out || 0)
  const token = data.transactions?.[0]?.token || 'ETH'
  const times = (data.timeline || []).map((t) => t.timestamp).filter(Boolean).sort()
  const path = data.trace_metrics?.nearest_endpoint
  const copy = async () => {
    try { await navigator.clipboard.writeText(suspect); setCopied(true); setTimeout(() => setCopied(false), 1500) }
    catch { setCopied(false) }
  }
  return (
    <div className="rounded-2xl bg-gradient-to-r from-indigo-950 to-slate-900 border border-indigo-800 p-4">
      <div className="flex flex-wrap items-center gap-4">
        <svg width="64" height="64" className="rounded-xl shrink-0" style={{ background: '#0f172a' }}>
          {cells.flatMap((row, y) => row.map((on, x) => on ? (
            <rect key={`${x}-${y}`} x={x * 12.8} y={y * 12.8} width="12.8" height="12.8" fill={`hsl(${hue} 70% 55%)`} />
          ) : null))}
        </svg>
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-widest text-indigo-300 font-bold">🎯 Suspect wallet under investigation</div>
          <div className="flex items-center gap-2 mt-1">
            <span className="font-mono text-sm break-all">{suspect}</span>
            <button onClick={copy} className="text-[11px] px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 shrink-0">
              {copied ? 'Copied ✓' : 'Copy'}
            </button>
          </div>
          {meta?.suspect_name && (
            <div className="text-xs text-slate-300 mt-1">
              Linked subject (off-chain records): <b>{meta.suspect_name}</b>
              <span className="text-slate-500"> — identity comes from lawful records, never from the blockchain</span>
            </div>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4 text-xs">
        {[['Risk', `${data.risk.score}/100 ${data.risk.level}`],
          ['Activity', `${f.tx_count || 0} txs · ${f.unique_counterparties || 0} counterparties`],
          ['Net flow', `${net >= 0 ? '+' : ''}${net.toFixed(4)} ${token}`],
          ['First seen', times[0]?.replace('T', ' ').slice(0, 16) || '—'],
          ['Last seen', times[times.length - 1]?.replace('T', ' ').slice(0, 16) || '—'],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl bg-black/30 px-3 py-2">
            <div className="text-[10px] uppercase tracking-widest text-slate-400">{k}</div>
            <div className="font-bold mt-0.5 break-all">{v}</div>
          </div>
        ))}
      </div>
      {path && (
        <div className="mt-3 text-xs flex flex-wrap items-center gap-1">
          <span className="text-slate-400 mr-1">Trace path to {path.label}:</span>
          {path.path.map((a, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <span className="text-indigo-400">→</span>}
              <span className={`font-mono px-2 py-0.5 rounded-lg ${i === 0 ? 'bg-indigo-600 font-bold' : i === path.path.length - 1 ? 'bg-emerald-700 font-bold' : 'bg-slate-800'}`}>
                {i === 0 ? 'SUSPECT' : i === path.path.length - 1 ? path.label : `${a.slice(0, 8)}…`}
              </span>
            </span>
          ))}
          <span className="text-slate-500 ml-1">({path.hops} hops — follow these wallets to trace the fraudster's funds)</span>
        </div>
      )}
    </div>
  )
}
