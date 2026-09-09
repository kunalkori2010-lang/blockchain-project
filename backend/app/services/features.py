"""Feature engineering for one suspect wallet."""
from collections import Counter


def wallet_features(address: str, txs: list[dict]) -> dict:
    addr = address.lower()
    involved = [t for t in txs if t["from_address"].lower() == addr or t["to_address"].lower() == addr]
    incoming = [t for t in involved if t["to_address"].lower() == addr]
    outgoing = [t for t in involved if t["from_address"].lower() == addr]
    amounts = [t["amount"] for t in involved]
    cps = set()
    for t in involved:
        cps.add(t["from_address"].lower())
        cps.add(t["to_address"].lower())
    cps.discard(addr)
    times = sorted(t["ts_epoch"] for t in involved)
    gaps = [b - a for a, b in zip(times, times[1:])] if len(times) > 1 else [0]
    avg_gap_min = (sum(gaps) / len(gaps) / 60) if gaps else 0
    # short-window burst: max txs in any 60-min window
    burst = 1
    if times:
        j = 0
        for i, ti in enumerate(times):
            while times[j] < ti - 3600:
                j += 1
            burst = max(burst, i - j + 1)
    return {
        "tx_count": len(involved),
        "in_count": len(incoming),
        "out_count": len(outgoing),
        "in_out_ratio": round(len(incoming) / max(1, len(outgoing)), 3),
        "unique_counterparties": len(cps),
        "total_in": round(sum(t["amount"] for t in incoming), 6),
        "total_out": round(sum(t["amount"] for t in outgoing), 6),
        "avg_amount": round(sum(amounts) / max(1, len(amounts)), 6),
        "max_amount": round(max(amounts) if amounts else 0, 6),
        "avg_gap_min": round(avg_gap_min, 2),
        "min_gap_min": round(min(gaps) / 60 if gaps else 0, 2),
        "burst_1h": burst,
        "wallet_age_h": round((max(times) - min(times)) / 3600, 2) if len(times) > 1 else 0,
    }
