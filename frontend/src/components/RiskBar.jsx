export default function RiskBar({ label, pct }) {
  const color = pct >= 80 ? 'bg-red-500' : pct >= 60 ? 'bg-orange-400' : pct >= 35 ? 'bg-yellow-400' : 'bg-emerald-400'
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs text-slate-300 mb-1"><span>{label}</span><span>{pct}%</span></div>
      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  )
}
