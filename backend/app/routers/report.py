from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user, audit
from ..config import settings
from ..services import blockchain, features as F, patterns as P, risk as R, entities as E, report as RP

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{case_id}")
async def case_report(case_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = db.query(models.Case).filter(models.Case.case_id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    txs = [{"tx_hash": t.tx_hash, "from_address": t.from_address, "to_address": t.to_address,
            "amount": t.amount, "token": t.token, "timestamp": t.timestamp, "ts_epoch": t.ts_epoch}
           for t in db.query(models.Transaction).filter(models.Transaction.case_ref == case_id).order_by(models.Transaction.ts_epoch).all()]
    if not txs:
        live, _ = await blockchain.get_transactions(case.wallet_address, case.network)
        txs = live
    emap = E.entity_map()
    feats = F.wallet_features(case.wallet_address, txs)
    pats = P.detect_patterns(case.wallet_address, txs, set(emap.keys()), max_hops=settings.TRACING_MAX_HOPS)
    anom = R.anomaly_nudge(feats, [t["amount"] for t in txs])
    score, level, reasons, indicators = R.compute_risk(feats, pats, emap, anomaly_score=anom)
    touched = pats["exchange_touch"].get("addresses", [])
    entities_hit = [emap[a] for a in touched if a in emap]
    timeline = [{"timestamp": t["timestamp"],
                 "text": f"{t['from_address'][:10]}… → {t['to_address'][:10]}… : {t['amount']} {t.get('token','ETH')}"} for t in sorted(txs, key=lambda x: x["ts_epoch"])[:30]]
    pdf = RP.build_case_report(
        {"case_id": case.case_id, "wallet_address": case.wallet_address, "network": case.network,
         "victim_ref": case.victim_ref, "fraud_amount_inr": case.fraud_amount_inr,
         "incident_date": case.incident_date, "incident_time_gmt": getattr(case, "incident_time_gmt", "") or "",
         "suspect_ip": getattr(case, "suspect_ip", "") or "",
         "ref_12digit": schemas.mask12(getattr(case, "ref_12digit", "") or ""),
         "suspect_name": getattr(case, "suspect_name", "") or "",
         "suspect_alias": getattr(case, "suspect_alias", "") or "",
         "suspect_phone": schemas.mask_phone(getattr(case, "suspect_phone", "") or ""),
         "suspect_email": schemas.mask_email(getattr(case, "suspect_email", "") or ""),
         "suspect_account": getattr(case, "suspect_account", "") or "",
         "tx_hash": case.tx_hash, "notes": case.notes},
        feats, {"score": score, "level": level, "reasons": reasons, "indicators": indicators},
        pats, entities_hit, txs, timeline, guidance=R.guidance_for(indicators, pats))
    audit(db, user.username, "report.generate", case_id)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={case_id}_report.pdf"})
