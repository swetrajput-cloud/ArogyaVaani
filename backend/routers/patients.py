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

def serialize_patient(p: Patient) -> dict:
    return {
        "id":                          p.id,
        "name":                        p.name,
        "phone":                       p.phone,
        "age":                         p.age,
        "language":                    p.language,
        "health_camp_name":            p.health_camp_name,
        "condition":                   p.condition,
        "module_type":                 p.module_type,
        "current_risk_tier":           p.current_risk_tier,
        "overall_risk_score":          p.overall_risk_score,
        "last_called_at":              p.last_called_at.isoformat() if p.last_called_at else None,
        "systolic_bp":                 p.systolic_bp,
        "diastolic_bp":                p.diastolic_bp,
        "heart_rate":                  p.heart_rate,
        "oxygen_saturation":           p.oxygen_saturation,
        "blood_glucose":               p.blood_glucose,
        "bmi":                         p.bmi,
        "heart_risk_level":            p.heart_risk_level,
        "diabetic_risk_level":         p.diabetic_risk_level,
        "hypertension_risk_level":     p.hypertension_risk_level,
        "chest_discomfort":            p.chest_discomfort,
        "breathlessness":              p.breathlessness,
        "palpitations":                p.palpitations,
        "fatigue_weakness":            p.fatigue_weakness,
        "dizziness_blackouts":         p.dizziness_blackouts,
        "caregiver_primary":           p.caregiver_primary,
        "caregiver_name":              p.caregiver_name,
        "caregiver_phone":             p.caregiver_phone,
        "is_active":                   p.is_active,
        "created_at":                  p.created_at.isoformat() if p.created_at else None,
        "updated_at":                  p.updated_at.isoformat() if p.updated_at else None,
    }

@router.get("")
def list_patients(
    risk_tier: str = Query(None),
    limit: int = Query(120),
    db: Session = Depends(get_db)
):
    query = db.query(Patient)
    if risk_tier:
        query = query.filter(Patient.current_risk_tier == risk_tier.upper())
    patients = query.order_by(Patient.overall_risk_score.desc().nullslast()).limit(limit).all()
    return {"patients": [serialize_patient(p) for p in patients]}

@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {"error": "Patient not found"}
    return serialize_patient(patient)