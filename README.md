# SIH26183 — Blockchain Cybercrime Investigation & Intelligence Platform

**Problem:** identify fraud-linked exchanges / VASPs from victim-reported suspect wallet addresses through automated blockchain analytics.
**Sponsor:** Ministry of Home Affairs · **Theme:** Blockchain & Cybersecurity.
**Positioning:** not a "crypto tracker" — a working **investigation prototype**: wallet in → blockchain analytics → graph → risk → case report.

## 60-second demo flow (judges)
1. Login `investigator / cyber123`
2. **+ New Investigation** → Case `CYB-2026-001`, network `ethereum`, any wallet (e.g. `0xAbC1234567890abcdef1234567890ABCDEF1234`), amount ₹75,000 → **🔍 ANALYSE WALLET**
3. Show: **Risk 82/100 HIGH** → interactive fund-flow graph (suspect → hops → possible exchange) → suspicious indicators → possible connected service → timeline
4. Click **📄 Generate Investigation Report** → PDF case file with hashes, scores, disclaimer

## Quick start (Windows)
```bat
run-backend.bat      :: FastAPI on http://localhost:8000  (docs at /docs)
run-frontend.bat     :: Vite on http://localhost:5173
```
Backend auto-seeds `investigator / cyber123` and `admin / admin123`. SQLite by default (`cyberchain.db`); set `DATABASE_URL` to Postgres for production / docker.

```bash
# docker (postgres + backend + frontend)
docker compose up --build
# live chain data (optional): set ETHERSCAN_API_KEY in backend/.env, else deterministic mock-prototype data is used
```

## Architecture
```
Investigator UI (React+Tailwind+ReactFlow) ──► FastAPI ──┬──► Blockchain API (Etherscan live / mock-prototype)
                                                          ├──► SQLite→Postgres (cases, wallets, txs, entities, risks, audit)
                                                          └──► Intelligence (seed entity map: exchanges/VASPs)
                     Transaction Engine (features + Pattern A/B/C) → Risk Engine (weights + IsolationForest)
                     → Graph builder → Dashboard + PDF report
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login` | JWT login |
| POST | `/api/cases` | register case |
| GET | `/api/cases` | list cases + risk |
| GET | `/api/cases/{case_id}` | case + txs + risks |
| POST | `/api/analyze` | full pipeline: fetch → features → patterns → risk → graph (creates/updates case) |
| GET | `/api/wallet/{addr}` | wallet summary card |
| GET | `/api/transactions/{addr}` | tx list |
| GET | `/api/risk/{addr}` | risk only |
| GET | `/api/graph/{addr}` | graph only |
| GET | `/api/report/{case_id}` | PDF case report |
| GET | `/api/alerts?min_level=HIGH` | alert feed (latest HIGH/CRITICAL risks per case) |
| GET | `/api/audit?limit=100&actor=` | audit trail (logins, analyses, reports) |
| GET/PUT | `/api/config/weights` | view / live-adjust risk indicator weights |
| GET | `/api/stats/summary` | portfolio stats (totals, by level/network/status) |
| GET | `/api/cases/search?q=` | search cases by ID / wallet / notes |
| GET/POST | `/api/entities` | threat-intel entity list + runtime additions |

## Risk engine (prototype assumptions — shown in UI + PDF)
`score = Σ weights + IsolationForest nudge`, weights: rapid 20 · fan-out 15 · consolidation 10 · exchange-touch 25 · flagged 10 · unusual 10 · burst 10.
Levels: ≥80 CRITICAL · ≥60 HIGH · ≥35 MEDIUM · else LOW. All outputs worded as **risk indicators / possible connections**, never definitive attribution.

## Team of 5 (maps to repo)
1. **Blockchain/Data** → `backend/app/services/blockchain.py`, `models.py` (wallets/transactions/entities)
2. **AI/ML & Risk** → `features.py`, `patterns.py`, `risk.py` (IsolationForest + rules)
3. **Cybersecurity & Intel** → `known_entities.json`, `report.py`, wording/audit (`auth.audit`, `audit_logs`)
4. **Backend** → `app/main.py`, `routers/*`, `config.py`, `database.py`
5. **Frontend** → `frontend/src/pages/*`, `components/GraphView.jsx`

## Security (prototype-level, real)
JWT auth + bcrypt hashing · role field · per-IP rate limiting (120/min API, 20/min login via `RATE_LIMIT_*`) · investigator-visible audit trail (`/audit`) · input validation (pydantic) · no private keys · no signing/sending · read-only analytics · CORS allowlist · evidence hashes in PDF.

## Prototype scope
Must-have ✅ all implemented. Good-to-have ⭐ partially (multi-chain-ready param, ML anomaly nudge, timeline, seed intel). Future 🚀: full indexer, more chains, entity resolution, monitoring, official-system integration.
