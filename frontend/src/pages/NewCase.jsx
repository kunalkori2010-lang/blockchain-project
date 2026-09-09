import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client.js'

export default function NewCase() {
  const nav = useNavigate()
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')
  const [form, setForm] = useState({
    case_id: 'CYB-2026-001', wallet_address: '0xAbC1234567890abcdef1234567890ABCDEF1234',
    network: 'ethereum', victim_ref: 'VICTIM-ANON-07', fraud_amount_inr: 75000,
    incident_date: '2026-09-05', incident_time_gmt: '2026-09-05T10:31', suspect_ip: '', ref_12digit: '',
    suspect_name: '', suspect_alias: '', suspect_phone: '', suspect_email: '', suspect_account: '',
    tx_hash: '', notes: 'Victim-reported suspect wallet from cyber portal complaint.',
  })
  const set = (k, v) => setForm({ ...form, [k]: v })

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true); setMsg('Fetching blockchain data → analysing patterns → scoring risk…')
    try {
      const { data } = await api.post('/api/analyze', form)
      nav(`/case/${data.case_id}`, { state: data })
    } catch (err) {
      setMsg('Analysis failed: ' + (err?.response?.data?.detail || err.message))
    } finally { setLoading(false) }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-extrabold mb-1">New Investigation — Case Registration</h1>
      <p className="text-xs text-slate-400 mb-5">Enter victim-reported suspect wallet → click Analyse Wallet.</p>
      <form onSubmit={submit} className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-3 text-sm">
        {[
          ['case_id', 'Case ID'], ['wallet_address', 'Suspect wallet address'],
          ['victim_ref', 'Victim ref / anonymous ID'], ['incident_date', 'Incident date (YYYY-MM-DD)'],
          ['tx_hash', 'Optional transaction hash'],
        ].map(([k, label]) => (
          <label key={k} className="block">
            <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">{label}</div>
            <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none font-mono text-xs"
              value={form[k]} onChange={(e) => set(k, e.target.value)} required={k === 'case_id' || k === 'wallet_address'} />
          </label>
        ))}
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">Incident date &amp; time (GMT/UTC)</div>
            <input type="datetime-local" className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none"
              value={form.incident_time_gmt} onChange={(e) => set('incident_time_gmt', e.target.value)} />
          </label>
          <label className="block">
            <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">Suspect IP (off-chain intel)</div>
            <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none font-mono text-xs" placeholder="e.g. 103.21.244.10"
              value={form.suspect_ip} onChange={(e) => set('suspect_ip', e.target.value)} />
          </label>
        </div>
        <label className="block">
          <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">12-digit reference (checksum-validated)</div>
          <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none font-mono text-xs" placeholder="e.g. 999999990017"
            value={form.ref_12digit} onChange={(e) => set('ref_12digit', e.target.value)} />
        </label>
        <div className="text-[11px] text-slate-500">IP and 12-digit ref cannot be derived from blockchain data (pseudonymous) — record them only from complaint records / VASP responses / lawful sources.</div>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">Network</div>
            <select className="w-full rounded-xl bg-slate-800 px-4 py-2.5" value={form.network} onChange={(e) => set('network', e.target.value)}>
              <option value="ethereum">ethereum</option>
              <option value="polygon">polygon (prototype-ready)</option>
              <option value="bsc">bsc (prototype-ready)</option>
            </select>
          </label>
          <label className="block">
            <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">Fraud amount (₹)</div>
            <input type="number" className="w-full rounded-xl bg-slate-800 px-4 py-2.5" value={form.fraud_amount_inr} onChange={(e) => set('fraud_amount_inr', Number(e.target.value))} />
          </label>
        </div>
        <div className="rounded-xl bg-slate-800/60 p-4 space-y-3">
          <div className="text-[11px] uppercase tracking-widest text-slate-400">Subject profile — off-chain, lawful sources only (FIR / VASP reply / bank). Never from the blockchain.</div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block"><div className="text-[11px] text-slate-500 mb-1">Suspect name (as per records)</div>
              <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none text-xs" value={form.suspect_name} onChange={(e) => set('suspect_name', e.target.value)} /></label>
            <label className="block"><div className="text-[11px] text-slate-500 mb-1">Alias / username</div>
              <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none text-xs" value={form.suspect_alias} onChange={(e) => set('suspect_alias', e.target.value)} /></label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block"><div className="text-[11px] text-slate-500 mb-1">Phone (10–15 digits)</div>
              <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none font-mono text-xs" value={form.suspect_phone} onChange={(e) => set('suspect_phone', e.target.value)} /></label>
            <label className="block"><div className="text-[11px] text-slate-500 mb-1">Email</div>
              <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none font-mono text-xs" value={form.suspect_email} onChange={(e) => set('suspect_email', e.target.value)} /></label>
          </div>
          <label className="block"><div className="text-[11px] text-slate-500 mb-1">Bank / UPI / account note</div>
            <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none font-mono text-xs" value={form.suspect_account} onChange={(e) => set('suspect_account', e.target.value)} /></label>
        </div>
        <label className="block">
          <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">Notes / evidence</div>
          <textarea className="w-full rounded-xl bg-slate-800 px-4 py-2.5" rows={3} value={form.notes} onChange={(e) => set('notes', e.target.value)} />
        </label>
        <button disabled={loading} className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 font-extrabold py-3 text-base">
          {loading ? '⏳ ANALYSING…' : '🔍 ANALYSE WALLET'}
        </button>
        {msg && <div className="text-xs text-slate-300">{msg}</div>}
      </form>
    </div>
  )
}
