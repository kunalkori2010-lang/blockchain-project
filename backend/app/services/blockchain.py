"""Blockchain data provider.
Tries Etherscan (if API key set) else deterministic mock generator so the
demo always works offline. Architecture supports multi-chain later.
"""
import hashlib
import random
import time
from datetime import datetime, timedelta
import httpx
from ..config import settings


def _mock_transactions(address: str, network: str = "ethereum", n: int = 28):
    """Deterministic, seed-based mock chain that exhibits fraud-like patterns:
    rapid hops, fan-out, consolidation, and one exchange touch."""
    addr = address.lower()
    seed = int(hashlib.sha256(addr.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    base = datetime(2026, 9, 5, 10, 31, 0)

    def a(i: int) -> str:
        h = hashlib.sha256(f"{addr}:{i}".encode()).hexdigest()
        return "0x" + h[:40]

    hops = [address, a(101), a(102), a(103)]
    # known exchange touch at the end for the demo story
    exchange = "0x28c6c06298d514db089934071355e5743bf21d60"  # Binance 14 seed
    txs = []
    t = base
    # 1) victim -> suspect (funding)
    txs.append({
        "tx_hash": "0x" + hashlib.sha256(f"{addr}:fund".encode()).hexdigest()[:64],
        "from_address": a(900), "to_address": address,
        "amount": round(rng.uniform(0.8, 2.5), 4), "token": "ETH",
        "timestamp": t.isoformat(), "ts_epoch": t.timestamp(), "network": network,
    })
    # 2) SUSPECT rapid fan-out: suspect splits funds to 3 wallets within ~15 min
    #    (Pattern A rapid movement + Pattern B fan-out, attributable to suspect itself)
    amt = round(rng.uniform(0.75, 2.2), 4)
    layer1 = [a(101), a(102), a(103)]
    for i, w in enumerate(layer1):
        t = t + timedelta(minutes=rng.choice([4, 5, 6]))
        txs.append({
            "tx_hash": "0x" + hashlib.sha256(f"{addr}:hop{i}".encode()).hexdigest()[:64],
            "from_address": address, "to_address": w,
            "amount": round(amt / 3 * rng.uniform(0.97, 1.03), 4), "token": "ETH",
            "timestamp": t.isoformat(), "ts_epoch": t.timestamp(), "network": network,
        })
    # 3) onward hop chain + fan-out from layer1 (network-level laundering story)
    fan = [a(201), a(202), a(203), a(204)]
    t = t + timedelta(minutes=7)
    txs.append({
        "tx_hash": "0x" + hashlib.sha256(f"{addr}:chain".encode()).hexdigest()[:64],
        "from_address": layer1[0], "to_address": layer1[1],
        "amount": round(amt / 3 * 0.99, 4), "token": "ETH",
        "timestamp": t.isoformat(), "ts_epoch": t.timestamp(), "network": network,
    })
    for j, w in enumerate(fan):
        t = t + timedelta(minutes=rng.choice([2, 3, 5]))
        txs.append({
            "tx_hash": "0x" + hashlib.sha256(f"{addr}:fan{j}".encode()).hexdigest()[:64],
            "from_address": layer1[1], "to_address": w,
            "amount": round(amt / 4 * rng.uniform(0.95, 1.05), 4), "token": "ETH",
            "timestamp": t.isoformat(), "ts_epoch": t.timestamp(), "network": network,
        })
    # 4) consolidation into X then exchange
    consol = a(300)
    for w in fan:
        t = t + timedelta(minutes=rng.choice([4, 7, 9]))
        txs.append({
            "tx_hash": "0x" + hashlib.sha256(f"{addr}:con{w[-6:]}".encode()).hexdigest()[:64],
            "from_address": w, "to_address": consol,
            "amount": round(amt / 4 * rng.uniform(0.96, 1.0), 4), "token": "ETH",
            "timestamp": t.isoformat(), "ts_epoch": t.timestamp(), "network": network,
        })
    t = t + timedelta(minutes=6)
    txs.append({
        "tx_hash": "0x" + hashlib.sha256(f"{addr}:ex".encode()).hexdigest()[:64],
        "from_address": consol, "to_address": exchange,
        "amount": round(amt * 0.97, 4), "token": "ETH",
        "timestamp": t.isoformat(), "ts_epoch": t.timestamp(), "network": network,
    })
    # 5) background noise txs
    for k in range(n - len(txs)):
        t = t + timedelta(hours=rng.choice([3, 9, 26, 50]))
        fr, to = (a(500 + k), address) if k % 2 == 0 else (address, a(600 + k))
        txs.append({
            "tx_hash": "0x" + hashlib.sha256(f"{addr}:bg{k}".encode()).hexdigest()[:64],
            "from_address": fr, "to_address": to,
            "amount": round(rng.uniform(0.01, 0.4), 4), "token": "ETH",
            "timestamp": t.isoformat(), "ts_epoch": t.timestamp(), "network": network,
        })
    txs.sort(key=lambda x: x["ts_epoch"])
    return txs


SCAN_APIS = {
    # Etherscan-family scanners share one API shape → true multi-chain support
    "ethereum": ("https://api.etherscan.io/api", "ETHERSCAN_API_KEY", "ETH", 1e18),
    "polygon": ("https://api.polygonscan.com/api", "POLYGONSCAN_API_KEY", "MATIC", 1e18),
    "bsc": ("https://api.bscscan.com/api", "BSCSCAN_API_KEY", "BNB", 1e18),
}


async def fetch_scan(chain: str, address: str) -> list[dict] | None:
    base, key_attr, symbol, decimals = SCAN_APIS[chain]
    key = getattr(settings, key_attr, "")
    if not key:
        return None
    params = {"module": "account", "action": "txlist", "address": address,
              "startblock": 0, "endblock": 99999999, "sort": "asc", "apikey": key}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(base, params=params)
            data = r.json()
            if data.get("status") != "1":
                return None
            out = []
            for t in data.get("result", [])[:200]:
                try:
                    val = int(t.get("value", "0")) / decimals
                except Exception:
                    val = 0
                try:
                    ts = datetime.utcfromtimestamp(int(t.get("timeStamp", "0")))
                except Exception:
                    ts = datetime.utcnow()
                out.append({
                    "tx_hash": t.get("hash", ""),
                    "from_address": t.get("from", ""),
                    "to_address": t.get("to", ""),
                    "amount": round(val, 6),
                    "token": symbol,
                    "timestamp": ts.isoformat(),
                    "ts_epoch": ts.timestamp(),
                    "network": chain,
                })
            return out or None
    except Exception:
        return None


async def get_transactions(address: str, network: str = "ethereum"):
    """Returns (txs, source): live '<chain>scan' when a key is set, else 'mock-prototype'."""
    chain = network.lower()
    if chain in SCAN_APIS:
        live = await fetch_scan(chain, address)
        if live:
            return live, f"{chain}scan-live"
    return _mock_transactions(address, network), "mock-prototype"
