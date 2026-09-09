# SIH26183 — 6-minute judge demo script

## 0:00 Hook (20s)
“Victims report only a wallet address. Our tool turns that single address into an investigation case: fund-flow graph, risk score, possible exchange, and a PDF report.”

## 0:20 Register case (40s)
- Login `investigator / cyber123`
- New Investigation: `CYB-2026-001`, Ethereum, suspect wallet, ₹75,000, 2026-09-05 → **ANALYSE WALLET**
- Narrate: “Fetching blockchain data… extracting features… detecting patterns…”

## 1:00 Risk + graph (2 min) ⭐
- Point to **82/100 HIGH** bar. “Weighted indicators, not a verdict — weights shown, fully configurable.”
- Graph: “Suspect → rapid hops (Pattern A) → fan-out to 4 wallets (Pattern B) → consolidation (Pattern C) → possible exchange.”
- Click an exchange node: “Possible Connected Service — Binance-pattern hot wallet, confidence from repeated interaction + mapping. Possible, not proven — report says verify with VASP.”

## 3:00 Indicators + timeline (1 min)
- Rapid transfers 90%, fan-out, exchange 88% bars + IsolationForest anomaly nudge.
- Timeline: received 10:31 → transferred 10:42 → split 10:47 → consolidated 11:02 → exchange 11:08.

## 4:00 Report (1 min) ⭐
- **Generate Investigation Report** → PDF: case, executive summary, risk breakdown, entities, timeline, tx hashes, disclaimer.
- “This is what an officer files — evidence-grade, not a dashboard screenshot.”

## 5:00 Close (1 min)
- “Stack: React + FastAPI + Postgres, Etherscan-live with offline mock fallback, Docker-ready. Architecture is multi-chain-ready. No keys, no signing — read-only forensics.”
- Q&A buffer. If asked about AI: “Rules + IsolationForest anomaly; supervised XGBoost when labelled data arrives.” If asked about attribution: “We say *possible connection*, investigator verifies.”
