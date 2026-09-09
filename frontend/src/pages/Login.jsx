import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client.js'

export default function Login() {
  const nav = useNavigate()
  const [form, setForm] = useState({ username: 'investigator', password: 'cyber123' })
  const [err, setErr] = useState('')
  const go = async (e) => {
    e.preventDefault()
    setErr('')
    try {
      const { data } = await api.post('/api/auth/login', form)
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', data.username)
      nav('/')
    } catch {
      setErr('Invalid credentials. Try investigator / cyber123')
    }
  }
  return (
    <div className="min-h-screen grid place-items-center bg-slate-950 text-slate-100 p-4">
      <div className="w-full max-w-md rounded-3xl bg-slate-900 border border-slate-800 p-8">
        <div className="text-2xl font-black">🛡️ CyberChain Investigator</div>
        <div className="text-xs text-slate-400 mt-1 mb-6">SIH26183 · Blockchain Cybercrime Intelligence · Demo login: <b>investigator / cyber123</b></div>
        <form onSubmit={go} className="space-y-3">
          <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none" placeholder="Username"
            value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <input className="w-full rounded-xl bg-slate-800 px-4 py-2.5 outline-none" type="password" placeholder="Password"
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          {err && <div className="text-xs text-red-400">{err}</div>}
          <button className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 font-bold py-2.5">Login</button>
        </form>
        <div className="text-[11px] text-slate-500 mt-4">Read-only analysis tool. No private keys, no transaction signing.</div>
      </div>
    </div>
  )
}
