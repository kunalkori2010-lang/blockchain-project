from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .. import models
from ..auth import get_current_user
from ..services import risk as R

router = APIRouter(prefix="/api/config", tags=["config"])


class WeightsIn(BaseModel):
    weights: dict[str, float]


@router.get("/weights")
def get_weights(user: models.User = Depends(get_current_user)):
    return {"weights": R.get_weights(), "defaults": R.DEFAULT_WEIGHTS,
            "levels": {"CRITICAL": ">=80", "HIGH": ">=60", "MEDIUM": ">=35", "LOW": "<35"},
            "anomaly": {"model": "IsolationForest", "contamination": 0.15, "nudge_range": [-5, 10]},
            "note": "Prototype assumptions — adjustable live via PUT; indicators are not proof."}


@router.put("/weights")
def put_weights(body: WeightsIn, user: models.User = Depends(get_current_user)):
    try:
        updated = R.set_weights(body.weights)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"weights": updated, "updated_by": user.username}
