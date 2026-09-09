from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    cases = db.query(models.Case).all()
    risks = db.query(models.RiskScore).order_by(models.RiskScore.id.desc()).all()
    latest: dict[str, models.RiskScore] = {}
    for r in risks:
        latest.setdefault(r.case_ref, r)
    by_level: dict[str, int] = {}
    scores = []
    for c in cases:
        r = latest.get(c.case_id)
        if r:
            by_level[r.risk_level] = by_level.get(r.risk_level, 0) + 1
            scores.append(r.score)
    by_network: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for c in cases:
        by_network[c.network] = by_network.get(c.network, 0) + 1
        by_status[c.status] = by_status.get(c.status, 0) + 1
    return {"total_cases": len(cases),
            "by_level": by_level,
            "by_network": by_network,
            "by_status": by_status,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "critical_high": by_level.get("CRITICAL", 0) + by_level.get("HIGH", 0)}
