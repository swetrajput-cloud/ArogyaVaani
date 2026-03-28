from models.database import SessionLocal
from models.patient import Patient
from typing import Optional

def get_patients_for_calling(
    risk_tiers: list = ["RED", "AMBER"],
    limit: int = 50
) -> list:
    """
    Get patients who need follow-up calls today.
    Prioritizes RED first, then AMBER, then GREEN.
    """
    db = SessionLocal()
    try:
        patients = (
            db.query(Patient)
            .filter(
                Patient.is_active == True,
                Patient.current_risk_tier.in_(risk_tiers)
            )
            .order_by(
                # RED first, then AMBER
                Patient.current_risk_tier.asc(),
                Patient.overall_risk_score.desc().nullslast()
            )
            .limit(limit)
            .all()
        )
        return [_patient_to_dict(p) for p in patients]
    finally:
        db.close()


def get_patient_call_profile(patient_id: int) -> Optional[dict]:
    """
    Get everything needed to make a call for a specific patient.
    """
    db = SessionLocal()
    try:
        p = db.query(Patient).filter(Patient.id == patient_id).first()
        if not p:
            return None
        return _patient_to_dict(p)
    finally:
        db.close()


def _patient_to_dict(p: Patient) -> dict:
    """Convert patient model to call-ready dict."""
    # Determine condition string
    conditions = []
    if p.heart_risk_level == "High":
        conditions.append("Coronary Artery Disease")
    if p.diabetic_risk_level == "High":
        conditions.append("Type 2 Diabetes")
    if p.hypertension_risk_level == "High":
        conditions.append("Hypertension")
    if not conditions:
        conditions.append("General Monitoring")

    return {
        "id": p.id,
        "name": p.name,
        "phone": p.phone,
        "language": p.language or "hindi",
        "condition": p.condition or "General Monitoring",
        "conditions_list": conditions,
        "risk_tier": p.current_risk_tier or "GREEN",
        "risk_score": p.overall_risk_score or 0.0,
        "module_type": p.module_type or "post_discharge",
        "caregiver_primary": p.caregiver_primary or False,
        "caregiver_phone": p.caregiver_phone,
        "health_camp_name": p.health_camp_name,
        "vitals": {
            "systolic_bp": p.systolic_bp,
            "diastolic_bp": p.diastolic_bp,
            "blood_glucose": p.blood_glucose,
            "heart_rate": p.heart_rate,
            "oxygen_saturation": p.oxygen_saturation,
            "bmi": p.bmi,
        }
    }