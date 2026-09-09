"""Risk engine: configurable rule weights + IsolationForest anomaly nudge.
Prototype weights are assumptions — surfaced in UI + report as such.
"""
import numpy as np

DEFAULT_WEIGHTS = {
    "rapid_movement": 20,
    "fanout": 15,
    "consolidation": 10,
    "exchange_touch": 25,
    "unusual": 10,
    "burst": 10,
    "flagged_touch": 10,  # extra if touched a flagged/mixer entity
    "peel_chain": 0,  # informational only — peel shape noted, never scored
}

LEVELS = [(80, "CRITICAL"), (60, "HIGH"), (35, "MEDIUM")]

# Study guide per clue: what the pattern is, why it matters, what to do next.
INDICATOR_GUIDE = {
    "rapid_movement": {
        "title": "Rapid fund movement",
        "what": "Funds left the wallet in quick succession, faster than normal user behaviour.",
        "why": "Classic layering: speed breaks the trail before victims report.",
        "next": "Trace each hop destination; check for fee-shaved decreasing amounts (peel chain).",
    },
    "fanout": {
        "title": "Fund splitting (fan-out)",
        "what": "One wallet scattered funds to 3+ addresses inside 48 hours.",
        "why": "Splitting evades amount-based detection and complicates tracing.",
        "next": "List every recipient; cluster the ones that later reconverge.",
    },
    "consolidation": {
        "title": "Fund consolidation",
        "what": "Scattered funds were gathered back into one wallet that forwarded them.",
        "why": "Reassembly point before cash-out — the highest-value trace target.",
        "next": "Flag the consolidation wallet as the next hop; VASP-request it if it touches an exchange.",
    },
    "exchange_touch": {
        "title": "Possible exchange interaction",
        "what": "Fund flow reaches a known exchange/VASP-pattern address within 5 hops.",
        "why": "Cash-out point: the exchange holds KYC + login IPs — the bridge to real identity.",
        "next": "File a VASP information request with tx hashes + GMT timestamps; match KYC.",
    },
    "flagged_touch": {
        "title": "Flagged / mixer interaction",
        "what": "Flow touches a sanctioned mixer or flagged address.",
        "why": "Deliberate obfuscation strongly suggests criminal intent — but still needs corroboration.",
        "next": "Escalate priority; cross-check sanctions lists; corroborate with FIR/bank trail.",
    },
    "unusual": {
        "title": "Unusual amount behaviour",
        "what": "Extreme variance between smallest and largest transfers (dust + large moves).",
        "why": "Tiny transfers are often test transactions before the real move.",
        "next": "Compare against the victim's stated amount and GMT time of fraud.",
    },
    "burst": {
        "title": "Transaction burst",
        "what": "Abnormal cluster of transactions inside a 60-minute window.",
        "why": "Bursts align with the active fraud window, unlike organic activity.",
        "next": "Correlate the burst window with the reported incident GMT time.",
    },
    "peel_chain": {
        "title": "Peel-chain trail (informational)",
        "what": "A run of hops each forwarding slightly less than received — the classic peel shape.",
        "why": "Peel chains are a documented layering structure; each hop is a traceable step.",
        "next": "Walk every hop in order; the end of the peel is usually near cash-out.",
    },
}


def guidance_for(indicators: dict, patterns: dict | None = None) -> list[dict]:
    """Study cards for each triggered clue (points + observed detail + next step).
    Zero-point informational hits (e.g. peel shape) are included when observed."""
    out = []
    for key, pts in indicators.items():
        if key not in INDICATOR_GUIDE:
            continue
        detail = ""
        if patterns and isinstance(patterns.get(key), dict):
            detail = patterns[key].get("detail", "")
        if pts or detail:
            g = INDICATOR_GUIDE[key]
            out.append({"indicator": key, "points": pts, "detail": detail,
                        "title": g["title"], "what": g["what"], "why": g["why"], "next": g["next"]})
    return sorted(out, key=lambda x: -x["points"])

# Live-overridable weights (PUT /api/config/weights). Prototype-grade:
# in-memory only — persist to DB / config service in production.
CUSTOM_WEIGHTS: dict = {}


def get_weights() -> dict:
    return {**DEFAULT_WEIGHTS, **CUSTOM_WEIGHTS}


def set_weights(patch: dict) -> dict:
    for k, v in patch.items():
        if k not in DEFAULT_WEIGHTS:
            raise ValueError(f"Unknown indicator: {k}. Valid: {sorted(DEFAULT_WEIGHTS)}")
        if not isinstance(v, (int, float)) or not (0 <= v <= 50):
            raise ValueError(f"Weight for '{k}' must be a number 0..50")
    CUSTOM_WEIGHTS.update({k: v for k, v in patch.items()})
    return get_weights()


def level_for(score: int) -> str:
    for th, lv in LEVELS:
        if score >= th:
            return lv
    return "LOW"


def compute_risk(features: dict, patterns: dict, entity_map: dict, weights: dict | None = None, anomaly_score: float = 0.0):
    w = {**get_weights(), **(weights or {})}
    indicators: dict[str, int] = {}
    reasons: list[str] = []

    def add(key: str, hit: bool, detail: str = ""):
        indicators[key] = w.get(key, 0) if hit else 0
        if hit:
            reasons.append(f"{key.replace('_', ' ').title()}" + (f" — {detail}" if detail else ""))

    add("rapid_movement", patterns["rapid_movement"]["hit"], patterns["rapid_movement"]["detail"])
    add("fanout", patterns["fanout"]["hit"], patterns["fanout"]["detail"])
    add("consolidation", patterns["consolidation"]["hit"], patterns["consolidation"]["detail"])
    touched = patterns["exchange_touch"].get("addresses", [])
    cats = {entity_map.get(a, {}).get("category", "") for a in touched}
    add("exchange_touch", bool(touched and ("exchange" in cats or not cats)), patterns["exchange_touch"]["detail"])
    add("flagged_touch", bool("flagged" in cats or "mixer" in cats), "Possible mixer/flagged interaction")
    add("unusual", patterns["unusual"]["hit"], patterns["unusual"]["detail"])
    add("peel_chain", patterns.get("peel_chain", {}).get("hit", False), patterns.get("peel_chain", {}).get("detail", ""))
    burst_hit = features.get("burst_1h", 0) >= 3
    add("burst", burst_hit, f"{features.get('burst_1h', 0)} txs within 60 min" if burst_hit else "")

    base = sum(indicators.values())
    # anomaly nudge: -5..+10 scaled from IsolationForest score
    nudge = int(round(max(-5, min(10, anomaly_score * 10))))
    score = max(0, min(100, base + nudge))
    return score, level_for(score), reasons, indicators


def anomaly_nudge(features: dict, all_amounts: list[float]) -> float:
    """IsolationForest over [amount stats]; returns ~ -0.5..1.0 contribution factor."""
    try:
        from sklearn.ensemble import IsolationForest
        if len(all_amounts) < 6:
            return 0.0
        X = np.array(all_amounts, dtype=float).reshape(-1, 1)
        clf = IsolationForest(contamination=0.15, random_state=42)
        pred = clf.fit_predict(X)  # -1 anomaly
        frac = float((pred == -1).mean())
        burst = features.get("burst_1h", 1)
        return max(0.0, min(1.0, frac + (0.3 if burst >= 4 else 0.0)))
    except Exception:
        return 0.0
