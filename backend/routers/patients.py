from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models.database import SessionLocal
from models.patient import Patient

router = APIRouter(prefix="/patients", tags=["patients"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def list_patients(
    risk_tier: str = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Patient)
    if risk_tier:
        query = query.filter(Patient.current_risk_tier == risk_tier.upper())
    patients = query.order_by(Patient.overall_risk_score.desc().nullslast()).all()
    return {"patients": [p.__dict__ for p in patients]}

@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {"error": "Patient not found"}
    return patient.__dict__