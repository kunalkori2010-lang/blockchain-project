"""Prototype test suite: risk engine, patterns, validators, trace metrics.
Runs offline — no server, no API keys needed (uses mock chain generator).
"""
import pytest
from pydantic import ValidationError

from app.services import risk as R
from app.services import patterns as P
from app.services import features as F
from app.services import graph as G
from app.services import entities as E
from app.services.blockchain import _mock_transactions
from app import schemas


SUSPECT = "0xAbC1234567890abcdef1234567890ABCDEF1234"


def test_levels():
    assert R.level_for(85) == "CRITICAL"
    assert R.level_for(60) == "HIGH"
    assert R.level_for(35) == "MEDIUM"
    assert R.level_for(10) == "LOW"


def test_weights_override_and_validation():
    before = R.get_weights()["rapid_movement"]
    R.set_weights({"rapid_movement": 5})
    assert R.get_weights()["rapid_movement"] == 5
    with pytest.raises(ValueError):
        R.set_weights({"nope": 5})
    with pytest.raises(ValueError):
        R.set_weights({"rapid_movement": 99})
    R.set_weights({"rapid_movement": before})  # restore


def test_verhoeff_vectors():
    assert schemas.verhoeff_ok("2363") is True
    assert schemas.verhoeff_ok("2364") is False
    assert schemas.verhoeff_ok("999999990017") is True


def test_12digit_validator():
    ok = schemas.CaseIntel(ref_12digit="999999990017")
    assert ok.ref_12digit == "999999990017"
    assert schemas.mask12("999999990017") == "XXXX-XXXX-0017"
    with pytest.raises(ValidationError):
        schemas.CaseIntel(ref_12digit="123")
    with pytest.raises(ValidationError):
        schemas.CaseIntel(ref_12digit="123456789011")  # bad checksum


def test_ip_and_gmt_validators():
    ok = schemas.CaseIntel(suspect_ip="103.21.244.10", incident_time_gmt="2026-09-05T10:31")
    assert ok.suspect_ip == "103.21.244.10"
    assert ok.incident_time_gmt == "2026-09-05T10:31:00+00:00"  # naive treated as GMT
    with pytest.raises(ValidationError):
        schemas.CaseIntel(suspect_ip="999.1.1.1")
    assert schemas.derive_gmt("2026-09-06", "") == "2026-09-06T00:00:00+00:00"


def test_mock_pipeline_hits_core_patterns():
    txs = _mock_transactions(SUSPECT, "ethereum")
    assert len(txs) >= 20
    emap = E.entity_map()
    feats = F.wallet_features(SUSPECT, txs)
    pats = P.detect_patterns(SUSPECT, txs, set(emap.keys()))
    assert pats["rapid_movement"]["hit"] is True
    assert pats["fanout"]["hit"] is True
    assert pats["exchange_touch"]["hit"] is True
    anom = R.anomaly_nudge(feats, [t["amount"] for t in txs])
    score, level, reasons, indicators = R.compute_risk(feats, pats, emap, anomaly_score=anom)
    assert score >= 60 and level in ("HIGH", "CRITICAL")
    assert len(reasons) >= 3


def test_peel_detector_shape():
    # hand-built 4-hop peel: each step forwards ~99%
    txs = []
    base = 1_700_000_000
    addrs = [SUSPECT] + [f"0xpeel{i:036d}" for i in range(5)]
    amt = 1.0
    for i in range(4):
        txs.append({"tx_hash": f"0xph{i}", "from_address": addrs[i], "to_address": addrs[i + 1],
                    "amount": round(amt, 6), "token": "ETH", "timestamp": "2026-09-05T10:00:00",
                    "ts_epoch": base + i * 600, "network": "ethereum"})
        amt *= 0.99
    n, detail = P.detect_peel_chain(SUSPECT, txs)
    assert n >= 3, detail


def test_guidance_cards_cover_hits():
    txs = _mock_transactions(SUSPECT, "ethereum")
    emap = E.entity_map()
    feats = F.wallet_features(SUSPECT, txs)
    pats = P.detect_patterns(SUSPECT, txs, set(emap.keys()))
    _, _, _, indicators = R.compute_risk(feats, pats, emap)
    cards = R.guidance_for(indicators, pats)
    titles = {c["title"] for c in cards}
    assert "Rapid fund movement" in titles
    assert all({"what", "why", "next"} <= set(c) for c in cards)


def test_trace_metrics_finds_exchange():
    txs = _mock_transactions(SUSPECT, "ethereum")
    m = G.trace_metrics(SUSPECT, txs, E.entity_map())
    assert m["engine"] == "networkx"
    assert m["nearest_endpoint"] is not None
    assert m["nearest_endpoint"]["hops"] >= 1
    assert len(m["hubs"]) > 0
