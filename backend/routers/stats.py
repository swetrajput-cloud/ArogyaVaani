from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import SessionLocal
from models.patient import Patient

router = APIRouter(tags=["stats"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Patient).count()
    red   = db.query(Patient).filter(Patient.current_risk_tier == "RED").count()
    amber = db.query(Patient).filter(Patient.current_risk_tier == "AMBER").count()
    green = db.query(Patient).filter(Patient.current_risk_tier == "GREEN").count()
    return {
        "total_patients": total,
        "red": red,
        "amber": amber,
        "green": green,
    }