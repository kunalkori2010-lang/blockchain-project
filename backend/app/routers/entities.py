from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..auth import get_current_user, audit

router = APIRouter(prefix="/api/entities", tags=["entities"])


class EntityIn(BaseModel):
    address: str
    label: str
    category: str = "exchange"  # exchange | mixer | flagged | service
    confidence_note: str = ""


@router.get("")
def list_entities(category: str = "", db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    q = db.query(models.Entity).order_by(models.Entity.id)
    if category:
        q = q.filter(models.Entity.category == category)
    return [{"address": e.address, "label": e.label, "category": e.category,
             "confidence_note": e.confidence_note, "source": e.source} for e in q.limit(200).all()]


@router.post("")
def add_entity(body: EntityIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if db.query(models.Entity).filter(models.Entity.address == body.address).first():
        raise HTTPException(400, "Entity address already known")
    e = models.Entity(address=body.address, label=body.label, category=body.category,
                      confidence_note=body.confidence_note, source=f"investigator:{user.username}")
    db.add(e)
    db.commit()
    audit(db, user.username, "entity.add", f"{body.label} {body.address[:20]}")
    return {"address": e.address, "label": e.label, "category": e.category}
