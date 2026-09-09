# SIH26183 — Judge Q&A Cheat Sheet (read this 10 min before the demo)

## The one-liner
"Victims report only a wallet address. We turn that single address into an investigation case: fund-flow graph, risk score, possible exchange, and a filing-ready PDF report."

## All parameters (memorize the bold numbers)

**Risk weights** — `GET /api/config/weights` (live-adjustable via `PUT`):
rapid_movement **20** · fanout **15** · consolidation **10** · exchange_touch **25** · flagged_touch **10** · unusual **10** · burst **10** (max 100 + anomaly nudge −5…+10).
Levels: **≥80 CRITICAL · ≥60 HIGH · ≥35 MEDIUM** · else LOW. Demo wallet scores **85 CRITICAL**.

**ML:** IsolationForest (`contamination=0.15`, `random_state=42`), fitted at runtime on the wallet's own amounts — unsupervised, so there is **no accuracy % to quote**. Never invent one.

**11 wallet features:** tx count · in/out counts + ratio · unique counterparties · total in/out · avg/max amount · avg/min gap · 1-hour burst · wallet age.

**Patterns:** A rapid movement (≥3 sends/60 min) · B fan-out (≥3 recipients/48 h) · C consolidation (≥3 funders → forward) · D exchange touch (5-hop BFS vs seed map) · E unusual variance.

**Data:** Etherscan live if `ETHERSCAN_API_KEY` is set, else deterministic mock-prototype (28 txs, same wallet → same story, works offline). Multi-chain-ready via `network` param; only Ethereum has a live path today.

**Entities:** 7 seed mappings (incl. Binance-pattern, Coinbase-pattern, WazirX-pattern, Tornado-flagged). Always say **"possible connection — verify with the VASP."**

**Security:** JWT + bcrypt · per-IP rate limits (120/min API, 20/min login) · audit trail page · pydantic validation · read-only (no keys, no signing).

## Questions → one-line answers

| They ask | You say |
|---|---|
| Weights validated? | "No — prototype assumptions, shown in UI/PDF, adjustable live. With labels we'd fit them." |
| Model accuracy? | "Unsupervised anomaly — no accuracy metric exists. Path: investigator-reviewed precision@k, then XGBoost." |
| How do you know it's Binance? | "We don't claim it. Possible connection from mapping + fund-flow; report says verify via VASP." |
| False positives? | "Scores are indicators, never verdicts — disclaimer on every screen and the PDF." |
| Why not just Etherscan? | "Etherscan shows transactions; we add cases, patterns, graph, scoring, alerts, audit, report — the workflow." |
| Only one chain? | "Prototype scope. `network` param + provider interface are chain-agnostic; intent is clear in code." |
| Real-time monitoring? | "On-demand analysis today; scheduler + indexer are listed future scope." |
| Scale (millions of txs)? | "Prototype caps ~300 txs/analysis; production needs indexer + queue + Postgres (compose file included)." |
| Show audit trail? | Open `/audit` page — logins, analyses, reports, filterable by actor. |
| Change a weight live? | `PUT /api/config/weights` then re-analyse — score recomputes. |
| Admissibility? | "Prototype. Hashes preserved in PDF; corroborate with FIR/victim statement; VASP confirmation via official channel." |
| Can you track the fraudster's WiFi/IP from the wallet? | "No — and no tool honestly can. Chain data is pseudonymous: addresses, amounts, timestamps only. No IP, MAC, or WiFi. Real IPs come from VASP login logs / ISP records via lawful request. Our tool records such off-chain intel (validated IP field) and correlates it with on-chain flow — that separation is stated in the UI and report." |
| 12-digit number? GMT time? | "Case form takes an exact GMT/UTC incident time (naive input treated as GMT, else derived from date) and a 12-digit reference with Verhoeff checksum + masked display (XXXX-XXXX-0017). Both print in the PDF." |
| Can it say 100% fraud? | "Deliberately not — chain data can't prove intent, and false certainty is dangerous. The system gives evidence strength + a per-clue study guide; only a human investigator with corroborating evidence (FIR/VASP/bank ref, mandatory in the app) can mark confirmed-fraud. Human-in-the-loop, court-ready." |
| What does each clue mean? | "Every triggered indicator ships a study card — what it is, why it matters, exact observed detail, and the next step. Also printed in the PDF." |
| Multi-chain? | "Ethereum + Polygon + BSC live via scanner APIs when keys are set (one code path, Etherscan-family), mock fallback offline. `TRACING_MAX_HOPS` configurable." |
| Graph intelligence? | "networkx engine: shortest suspect→exchange path with hop count, max trace depth, top hub wallets — shown under the graph." |
| Tests? | "`backend/tests/` — 9 pytest cases, all passing offline: risk levels, weight validation, Verhoeff vectors, IP/GMT validators, mock-pipeline hits, peel shape, trace metrics." |
| Threat intel updates? | "Seed list plus runtime `POST /api/entities` — investigators can add attributions live, audited." |
| What did each of 5 do? | Blockchain→`blockchain.py`· AI→`features/patterns/risk.py` · Security→entity map/report/wording · Backend→routers/DB · Frontend→pages/graph. |

## If the demo gods fail
No internet? Mock mode still runs — say so proudly. Backend down? `docs` screenshots + PDF sample in repo talk. Forgot wallet? Any address works in mock mode.
