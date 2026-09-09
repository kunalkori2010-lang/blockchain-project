export default function StatCard({ label, value, sub }) {
  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
      <div className="text-[11px] uppercase tracking-widest text-slate-400">{label}</div>
      <div className="text-3xl font-black mt-1">{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </div>
  )
}
