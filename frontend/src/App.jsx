import { Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import NewCase from './pages/NewCase.jsx'
import CaseDetail from './pages/CaseDetail.jsx'
import Audit from './pages/Audit.jsx'

function Guard({ children }) {
  const t = localStorage.getItem('token')
  if (!t) return <Navigate to="/login" replace />
  return children
}

function Shell({ children }) {
  const nav = useNavigate()
  const user = localStorage.getItem('user') || 'investigator'
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 grid place-items-center font-black">C</div>
          <div>
            <div className="font-extrabold tracking-wide text-sm">CYBERCRIME BLOCKCHAIN INTELLIGENCE</div>
            <div className="text-[11px] text-slate-400">SIH26183 · Ministry of Home Affairs · Prototype</div>
          </div>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <Link className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700" to="/">Dashboard</Link>
            <Link className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700" to="/audit">Audit</Link>
            <Link className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold" to="/new">+ New Investigation</Link>
            <span className="text-slate-400 hidden md:inline">{user}</span>
            <button className="px-3 py-1.5 rounded-lg bg-slate-800" onClick={() => { localStorage.clear(); nav('/login') }}>Logout</button>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      <footer className="max-w-7xl mx-auto px-4 pb-8 text-[11px] text-slate-500">
        Prototype for demo. Risk scores are heuristic indicators, not proof. Entity matches are “possible connections” — verify via VASP / official records.
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Guard><Shell><Dashboard /></Shell></Guard>} />
      <Route path="/new" element={<Guard><Shell><NewCase /></Shell></Guard>} />
      <Route path="/case/:caseId" element={<Guard><Shell><CaseDetail /></Shell></Guard>} />
      <Route path="/audit" element={<Guard><Shell><Audit /></Shell></Guard>} />
    </Routes>
  )
}
