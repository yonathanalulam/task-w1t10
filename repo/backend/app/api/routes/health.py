from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import db_dep

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness(db: Session = Depends(db_dep)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
