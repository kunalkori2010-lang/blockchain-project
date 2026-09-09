from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..auth import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(limit: int = 100, actor: str = "", db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Investigator-visible audit trail (logins, case creates, analyses, reports)."""
    q = db.query(models.AuditLog).order_by(models.AuditLog.id.desc())
    if actor:
        q = q.filter(models.AuditLog.actor == actor)
    rows = q.limit(max(1, min(limit, 500))).all()
    return [{"id": r.id, "actor": r.actor, "action": r.action, "detail": r.detail,
             "created_at": r.created_at.isoformat() if r.created_at else ""} for r in rows]
