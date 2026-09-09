from .database import SessionLocal
from . import models
from .auth import hash_password
from .services.entities import load_entities


def seed():
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.username == "investigator").first():
            db.add(models.User(username="investigator", password_hash=hash_password("cyber123"), role="investigator"))
        if not db.query(models.User).filter(models.User.username == "admin").first():
            db.add(models.User(username="admin", password_hash=hash_password("admin123"), role="admin"))
        for e in load_entities():
            if not db.query(models.Entity).filter(models.Entity.address == e["address"]).first():
                db.add(models.Entity(address=e["address"], label=e["label"], category=e.get("category", "exchange"),
                                     confidence_note=e.get("confidence_note", ""), source=e.get("source", "seed")))
        db.commit()
    finally:
        db.close()
