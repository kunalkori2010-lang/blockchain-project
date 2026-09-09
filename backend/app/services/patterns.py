"""Heuristic suspicious-pattern detectors (risk indicators, not proof)."""
from collections import defaultdict


def _gaps(times):
    times = sorted(times)
    return [b - a for a, b in zip(times, times[1:])]


def detect_patterns(address: str, txs: list[dict], known_set: set[str], max_hops: int = 5) -> dict:
    addr = address.lower()
    out_tx = sorted([t for t in txs if t["from_address"].lower() == addr], key=lambda x: x["ts_epoch"])
    in_tx = [t for t in txs if t["to_address"].lower() == addr]

    # A) rapid fund movement: >=3 outgoing within 60 min with decreasing-ish amounts
    rapid = False
    rapid_detail = ""
    if len(out_tx) >= 2:
        times = [t["ts_epoch"] for t in out_tx]
        window = 1
        for i in range(len(times)):
            c = sum(1 for tj in times if 0 <= tj - times[i] <= 3600)
            window = max(window, c)
        gaps_min = [g / 60 for g in _gaps(times)] if len(times) > 1 else []
        avg_gap = sum(gaps_min) / len(gaps_min) if gaps_min else 999
        if window >= 3 or (len(out_tx) >= 2 and avg_gap <= 15):
            rapid = True
            rapid_detail = f"{window} transfers within 60 min ({len(out_tx)} outgoing total)"

    # B) fan-out: >=3 distinct recipients within any 48h sliding window
    fanout = False
    fanout_n = 0
    by_sender = defaultdict(list)
    for t in txs:
        by_sender[t["from_address"].lower()].append(t)
    for sender, lst in by_sender.items():
        if sender != addr:
            continue
        lst = sorted(lst, key=lambda x: x["ts_epoch"])
        best = 0
        for i in range(len(lst)):
            win = [x for x in lst if 0 <= x["ts_epoch"] - lst[i]["ts_epoch"] <= 172800]
            best = max(best, len(set(x["to_address"].lower() for x in win)))
        if best >= 3:
            fanout = True
            fanout_n = best
            break

    # C) consolidation: >=3 distinct senders into one address that then forwards
    # Prefer downstream (non-suspect) consolidation to avoid noise self-match
    consol = False
    consol_detail = ""
    by_recv = defaultdict(list)
    for t in txs:
        by_recv[t["to_address"].lower()].append(t)
    ordered = sorted(by_recv.items(), key=lambda kv: (kv[0] == addr, -len(set(x["from_address"].lower() for x in kv[1]))))
    for recv, lst in ordered:
        senders = set(x["from_address"].lower() for x in lst)
        if len(senders) >= 3:
            fwd = [t for t in txs if t["from_address"].lower() == recv]
            if fwd:
                consol = True
                who = "suspect wallet" if recv == addr else f"{recv[:10]}…"
                consol_detail = f"{who} funded by {len(senders)} wallets then forwarded ({len(fwd)} txs)"
                break

    # D) exchange / flagged interaction within max_hops (BFS fund-flow trace)
    neighbours: dict[str, set[str]] = {}
    for t in txs:
        f, to = t["from_address"].lower(), t["to_address"].lower()
        neighbours.setdefault(f, set()).add(to)
        neighbours.setdefault(to, set()).add(f)
    seen = {addr}
    frontier = {addr}
    for _ in range(max_hops):
        nxt = set()
        for u in frontier:
            for v in neighbours.get(u, set()):
                if v not in seen:
                    seen.add(v)
                    nxt.add(v)
        frontier = nxt
        if not frontier:
            break
    seen.discard(addr)
    exch_touch = sorted(seen & known_set)

    # E) unusual behaviour: burst or tiny dust + large move mix
    amounts = [t["amount"] for t in txs if t["from_address"].lower() == addr or t["to_address"].lower() == addr]
    unusual = False
    if amounts and (max(amounts) / max(0.0001, min(amounts)) > 50):
        unusual = True

    # F) peel-chain heuristic (account-model adaptation): longest run of
    # 1-in → 1-dominant-out hops where each step shaves ~0.1–5% (fee-like),
    # the classic peel-chain money-trail shape. Informational (no weight).
    peel_len, peel_detail = detect_peel_chain(address, txs)

    return {
        "rapid_movement": {"hit": rapid, "detail": rapid_detail},
        "fanout": {"hit": fanout, "detail": f"{fanout_n} distinct recipients" if fanout else ""},
        "consolidation": {"hit": consol, "detail": consol_detail},
        "exchange_touch": {"hit": bool(exch_touch), "detail": ", ".join(a[:12] + "…" for a in exch_touch[:3]), "addresses": exch_touch},
        "unusual": {"hit": unusual, "detail": "Wide amount variance (dust + large moves)" if unusual else ""},
        "peel_chain": {"hit": peel_len >= 3, "detail": peel_detail, "length": peel_len},
        "in_count": len(in_tx),
        "out_count": len(out_tx),
    }


def detect_peel_chain(address: str, txs: list[dict]) -> tuple[int, str]:
    """Longest peel-like run reachable from the suspect: each step forwards
    95–99.9% of what it received within 24h (single dominant output)."""
    by_in: dict[str, list[dict]] = defaultdict(list)
    by_out: dict[str, list[dict]] = defaultdict(list)
    for t in txs:
        by_in[t["to_address"].lower()].append(t)
        by_out[t["from_address"].lower()].append(t)
    best = 0
    best_path: list[str] = []
    addr = address.lower()
    # try every outgoing tx of the suspect as a peel start
    for start in sorted(by_out.get(addr, []), key=lambda x: x["ts_epoch"]):
        path = [addr]
        cur_tx = start
        cur_amt = start["amount"]
        cur_time = start["ts_epoch"]
        nxt = start["to_address"].lower()
        while True:
            outs = [o for o in by_out.get(nxt, []) if o["ts_epoch"] >= cur_time and o["ts_epoch"] - cur_time <= 86400]
            if not outs:
                break
            o = min(outs, key=lambda x: x["ts_epoch"])
            if cur_amt > 0 and 0.95 * cur_amt <= o["amount"] <= 0.999 * cur_amt:
                path.append(nxt)
                cur_amt, cur_time, nxt = o["amount"], o["ts_epoch"], o["to_address"].lower()
                if len(path) > 12 or nxt in path:
                    break
            else:
                break
        if len(path) - 1 > best:
            best = len(path) - 1
            best_path = path
    detail = f"{best}-hop peel-like run" + (f" via {best_path[1][:10]}…" if best_path[1:] else "") if best else ""
    return best, detail
