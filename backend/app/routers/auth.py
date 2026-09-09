from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from ..auth import verify_password, create_token, get_current_user, audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.username == body.username).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    audit(db, u.username, "login", " investigator login")
    return {"access_token": create_token(u.username, u.role), "token_type": "bearer", "username": u.username, "role": u.role}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role}
