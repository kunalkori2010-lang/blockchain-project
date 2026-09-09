from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user, audit
from ..config import settings
from ..services import blockchain, features as F, patterns as P, risk as R, graph as G, entities as E

router = APIRouter(prefix="/api", tags=["analyze"])

_ARTICLE_CACHE: dict[str, dict] = {}


async def _analyse_wallet(address: str, network: str):
    txs, source = await blockchain.get_transactions(address, network)
    emap = E.entity_map()
    feats = F.wallet_features(address, txs)
    pats = P.detect_patterns(address, txs, set(emap.keys()), max_hops=settings.TRACING_MAX_HOPS)
    amounts = [t["amount"] for t in txs]
    anom = R.anomaly_nudge(feats, amounts)
    score, level, reasons, indicators = R.compute_risk(feats, pats, emap, anomaly_score=anom)
    graph = G.build_graph(address, txs, emap, score)
    metrics = G.trace_metrics(address, txs, emap)
    # entities hit
    touched = pats["exchange_touch"].get("addresses", [])
    entities_hit = []
    for a in touched:
        e = emap.get(a)
        if e:
            entities_hit.append({**e, "match_type": "direct seed mapping — verify with VASP"})
    if pats["exchange_touch"]["hit"] and not entities_hit:
        entities_hit.append({"label": "Unlabelled service interaction (pattern-based)",
                             "category": "service", "address": (touched[0] if touched else ""),
                             "confidence_note": "Pattern suggests service/exchange hop; needs attribution",
                             "match_type": "heuristic"})
    # timeline narrative
    timeline = []
    for t in sorted(txs, key=lambda x: x["ts_epoch"])[:30]:
        if t["to_address"].lower() == address.lower():
            timeline.append({"timestamp": t["timestamp"], "text": f"Funds received: {t['amount']} {t.get('token','ETH')} from {t['from_address'][:12]}…", "tx_hash": t["tx_hash"]})
        elif t["from_address"].lower() == address.lower():
            timeline.append({"timestamp": t["timestamp"], "text": f"Funds sent: {t['amount']} {t.get('token','ETH')} to {t['to_address'][:12]}…", "tx_hash": t["tx_hash"]})
        else:
            timeline.append({"timestamp": t["timestamp"], "text": f"Hop: {t['from_address'][:10]}… → {t['to_address'][:10]}… ({t['amount']} {t.get('token','ETH')})", "tx_hash": t["tx_hash"]})
    return {"transactions": txs, "source": source, "features": feats, "patterns": pats,
            "risk": {"score": score, "level": level, "reasons": reasons, "indicators": indicators,
                     "weights": R.get_weights(), "anomaly_nudge": anom,
                     "guidance": R.guidance_for(indicators, pats),
                     "note": "Prototype weights are assumptions; indicators ≠ proof."},
            "graph": graph, "entities_hit": entities_hit, "timeline": timeline,
            "trace_metrics": metrics, "max_hops": settings.TRACING_MAX_HOPS}


@router.post("/analyze")
async def analyze(body: schemas.AnalyzeIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    res = await _analyse_wallet(body.wallet_address, body.network)
    case_id = body.case_id
    if not case_id:
        case_id = f"CYB-2026-{datetime.utcnow().strftime('%H%M%S')}"
    case = db.query(models.Case).filter(models.Case.case_id == case_id).first()
    gmt = schemas.derive_gmt(body.incident_date, body.incident_time_gmt)
    if not case:
        case = models.Case(case_id=case_id, wallet_address=body.wallet_address, network=body.network,
                           victim_ref=body.victim_ref, fraud_amount_inr=body.fraud_amount_inr,
                           incident_date=body.incident_date, incident_time_gmt=gmt,
                           suspect_ip=body.suspect_ip, ref_12digit=body.ref_12digit,
                           suspect_name=body.suspect_name, suspect_alias=body.suspect_alias,
                           suspect_phone=body.suspect_phone, suspect_email=body.suspect_email,
                           suspect_account=body.suspect_account,
                           tx_hash=body.tx_hash, notes=body.notes,
                           status="open", created_by=user.username)
        db.add(case)
    else:
        case.wallet_address = body.wallet_address
        case.network = body.network
        if body.incident_date:
            case.incident_date = body.incident_date
        if gmt:
            case.incident_time_gmt = gmt
        if body.suspect_ip:
            case.suspect_ip = body.suspect_ip
        if body.ref_12digit:
            case.ref_12digit = body.ref_12digit
        for f in ("suspect_name", "suspect_alias", "suspect_phone", "suspect_email", "suspect_account"):
            v = getattr(body, f, "")
            if v:
                setattr(case, f, v)
        if body.notes:
            case.notes = body.notes
    db.query(models.Transaction).filter(models.Transaction.case_ref == case_id).delete()
    for t in res["transactions"][:300]:
        db.add(models.Transaction(case_ref=case_id, tx_hash=t["tx_hash"], from_address=t["from_address"],
                                  to_address=t["to_address"], amount=t["amount"], token=t.get("token", "ETH"),
                                  timestamp=t["timestamp"], network=t.get("network", body.network), ts_epoch=t["ts_epoch"]))
    if not db.query(models.Wallet).filter(models.Wallet.address == body.wallet_address).first():
        db.add(models.Wallet(address=body.wallet_address, network=body.network))
    db.add(models.RiskScore(case_ref=case_id, wallet=body.wallet_address, score=res["risk"]["score"],
                            risk_level=res["risk"]["level"], reasons=res["risk"]["reasons"], indicators=res["risk"]["indicators"]))
    db.commit()
    audit(db, user.username, "wallet.analyze", f"{case_id} {body.wallet_address} score={res['risk']['score']}")
    return {"case_id": case_id, **res, "tx_count": len(res["transactions"])}


@router.get("/wallet/{address}")
async def wallet_summary(address: str, network: str = "ethereum", user: models.User = Depends(get_current_user)):
    res = await _analyse_wallet(address, network)
    txs = res["transactions"]
    involved = [t for t in txs if t["from_address"].lower() == address.lower() or t["to_address"].lower() == address.lower()]
    ts = sorted([t["ts_epoch"] for t in involved]) if involved else [0, 0]
    from datetime import datetime as dt
    return {"address": address, "network": network,
            "balance_hint": f"net {res['features']['total_in'] - res['features']['total_out']:.4f} ETH (from analysed window)",
            "first_seen": dt.utcfromtimestamp(ts[0]).isoformat() if ts[0] else "",
            "last_seen": dt.utcfromtimestamp(ts[-1]).isoformat() if ts[-1] else "",
            "in_count": res["features"]["in_count"], "out_count": res["features"]["out_count"],
            "risk_score": res["risk"]["score"], "risk_level": res["risk"]["level"],
            "connected": res["features"]["unique_counterparties"], "source": res["source"]}


@router.get("/risk/{address}")
async def risk_only(address: str, network: str = "ethereum", user: models.User = Depends(get_current_user)):
    res = await _analyse_wallet(address, network)
    return res["risk"]


@router.get("/graph/{address}")
async def graph_only(address: str, network: str = "ethereum", user: models.User = Depends(get_current_user)):
    res = await _analyse_wallet(address, network)
    return res["graph"]


@router.get("/transactions/{address}")
async def tx_only(address: str, network: str = "ethereum", user: models.User = Depends(get_current_user)):
    res = await _analyse_wallet(address, network)
    return {"source": res["source"], "count": len(res["transactions"]), "transactions": res["transactions"][:200]}
