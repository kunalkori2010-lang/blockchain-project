from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user, audit
from ..services.ipintel import ip_intel

router = APIRouter(prefix="/api/cases", tags=["cases"])

ALLOWED_STATUS = {"open", "under-investigation", "confirmed-fraud", "closed", "dismissed"}


class StatusIn(BaseModel):
    status: str
    note: str = ""  # corroborating-evidence reference, REQUIRED for confirmed-fraud


def _out(c: models.Case) -> dict:
    return {"case_id": c.case_id, "wallet_address": c.wallet_address, "network": c.network,
            "victim_ref": c.victim_ref, "fraud_amount_inr": c.fraud_amount_inr,
            "incident_date": c.incident_date, "incident_time_gmt": getattr(c, "incident_time_gmt", "") or "",
            "suspect_ip": getattr(c, "suspect_ip", "") or "",
            "ref_12digit": schemas.mask12(getattr(c, "ref_12digit", "") or ""),
            "suspect_name": getattr(c, "suspect_name", "") or "",
            "suspect_alias": getattr(c, "suspect_alias", "") or "",
            "suspect_phone": schemas.mask_phone(getattr(c, "suspect_phone", "") or ""),
            "suspect_email": schemas.mask_email(getattr(c, "suspect_email", "") or ""),
            "suspect_account": getattr(c, "suspect_account", "") or "",
            "suspect_ip_intel": ip_intel(getattr(c, "suspect_ip", "") or ""),
            "tx_hash": c.tx_hash, "notes": c.notes,
            "status": c.status, "created_by": c.created_by,
            "created_at": c.created_at.isoformat() if isinstance(c.created_at, datetime) else str(c.created_at)}


@router.post("", response_model=schemas.CaseOut)
def create_case(body: schemas.CaseCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if db.query(models.Case).filter(models.Case.case_id == body.case_id).first():
        raise HTTPException(400, "Case ID already exists")
    d = body.model_dump()
    d["incident_time_gmt"] = schemas.derive_gmt(body.incident_date, body.incident_time_gmt)
    c = models.Case(**d, status="open", created_by=user.username)
    db.add(c)
    db.commit()
    audit(db, user.username, "case.create", body.case_id)
    return _out(c)


@router.get("")
def list_cases(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.query(models.Case).order_by(models.Case.id.desc()).limit(100).all()
    out = []
    for c in rows:
        d = _out(c)
        r = db.query(models.RiskScore).filter(models.RiskScore.case_ref == c.case_id).order_by(models.RiskScore.id.desc()).first()
        d["risk_score"] = r.score if r else None
        d["risk_level"] = r.risk_level if r else None
        out.append(d)
    return out


@router.get("/search")
def search_cases(q: str = "", db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Search cases by ID, wallet, notes or victim ref (min 2 chars)."""
    q = (q or "").strip()
    if len(q) < 2:
        return []
    like = f"%{q}%"
    rows = db.query(models.Case).filter(
        (models.Case.case_id.ilike(like)) | (models.Case.wallet_address.ilike(like)) |
        (models.Case.notes.ilike(like)) | (models.Case.victim_ref.ilike(like))
    ).order_by(models.Case.id.desc()).limit(50).all()
    return [_out(c) for c in rows]


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    c = db.query(models.Case).filter(models.Case.case_id == case_id).first()
    if not c:
        raise HTTPException(404, "Case not found")
    d = _out(c)
    risks = db.query(models.RiskScore).filter(models.RiskScore.case_ref == case_id).order_by(models.RiskScore.id.desc()).all()
    d["risks"] = [{"wallet": r.wallet, "score": r.score, "risk_level": r.risk_level, "reasons": r.reasons,
                   "indicators": r.indicators, "created_at": r.created_at.isoformat()} for r in risks]
    d["transactions"] = [{"tx_hash": t.tx_hash, "from_address": t.from_address, "to_address": t.to_address,
                          "amount": t.amount, "token": t.token, "timestamp": t.timestamp, "network": t.network}
                         for t in db.query(models.Transaction).filter(models.Transaction.case_ref == case_id).order_by(models.Transaction.ts_epoch).limit(300).all()]
    return d


@router.put("/{case_id}/status")
def set_status(case_id: str, body: StatusIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Human verdict workflow. The algorithm NEVER declares certainty: only an
    investigator with corroborating evidence may mark 'confirmed-fraud',
    and a evidence reference (FIR no / VASP reply / bank lien) is mandatory."""
    st = body.status.strip().lower()
    if st not in ALLOWED_STATUS:
        raise HTTPException(400, f"Invalid status. Allowed: {sorted(ALLOWED_STATUS)}")
    c = db.query(models.Case).filter(models.Case.case_id == case_id).first()
    if not c:
        raise HTTPException(404, "Case not found")
    if st == "confirmed-fraud" and not body.note.strip():
        raise HTTPException(400, "Marking confirmed-fraud requires a corroborating-evidence note (FIR no / VASP reply ref / bank lien ref)")
    c.status = st
    if body.note.strip():
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        c.notes = ((c.notes or "") + f"\n[{stamp} {user.username} → {st}] {body.note.strip()}").strip()
    db.commit()
    audit(db, user.username, "case.status", f"{case_id} → {st} :: {body.note.strip()[:120]}")
    return {"case_id": case_id, "status": st}
