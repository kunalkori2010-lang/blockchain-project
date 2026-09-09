from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..auth import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@router.get("")
def alerts(min_level: str = "HIGH", db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Derived alert feed: latest risk per case at/above min_level. Levels: LOW/MEDIUM/HIGH/CRITICAL."""
    floor = _RANK.get(min_level.upper(), 2)
    risks = db.query(models.RiskScore).order_by(models.RiskScore.id.desc()).limit(500).all()
    seen: set[str] = set()
    out = []
    for r in risks:
        if r.case_ref in seen:
            continue
        seen.add(r.case_ref)
        if _RANK.get(r.risk_level, 0) >= floor:
            c = db.query(models.Case).filter(models.Case.case_id == r.case_ref).first()
            out.append({
                "severity": r.risk_level,
                "case_id": r.case_ref,
                "wallet": r.wallet,
                "score": r.score,
                "headline": (r.reasons[0] if r.reasons else "High-risk indicators detected"),
                "reasons": r.reasons,
                "network": c.network if c else "",
                "created_at": r.created_at.isoformat() if r.created_at else "",
            })
    return out
