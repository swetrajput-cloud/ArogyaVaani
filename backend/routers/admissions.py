from fastapi import APIRouter, HTTPException
from models.database import SessionLocal
from models.admission import Admission
from models.patient import Patient
from alerts.doctor_sms import _send_whatsapp
from config import settings
from datetime import datetime

router = APIRouter(prefix="/admissions", tags=["admissions"])


@router.get("")
def get_admissions():
    db = SessionLocal()
    try:
        admissions = (
            db.query(Admission, Patient)
            .join(Patient, Admission.patient_id == Patient.id)
            .order_by(Admission.requested_at.desc())
            .limit(50)
            .all()
        )
        return {
            "admissions": [
                {
                    "id":            a.id,
                    "patient_id":    a.patient_id,
                    "patient_name":  p.name,
                    "patient_phone": p.phone,
                    "condition":     p.condition,
                    "risk_tier":     a.risk_tier,
                    "reason":        a.reason,
                    "status":        a.status,
                    "requested_at":  a.requested_at,
                    "admitted_at":   a.admitted_at,
                    "notes":         a.notes,
                }
                for a, p in admissions
            ]
        }
    finally:
        db.close()


@router.post("/{admission_id}/admit")
def admit_patient(admission_id: int):
    db = SessionLocal()
    try:
        admission = db.query(Admission).filter(Admission.id == admission_id).first()
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")

        patient = db.query(Patient).filter(Patient.id == admission.patient_id).first()

        admission.status      = "admitted"
        admission.admitted_at = datetime.utcnow()
        db.commit()

        if patient and patient.phone:
            _send_whatsapp(
                to_phone=patient.phone,
                message=(
                    f"🏥 *आरोग्यवाणी - भर्ती सूचना*\n"
                    f"नमस्ते {patient.name}!\n"
                    f"आपको अस्पताल में भर्ती करने की सलाह दी गई है।\n"
                    f"*कारण:* {admission.reason or 'उच्च जोखिम - तत्काल देखभाल आवश्यक'}\n"
                    f"कृपया तुरंत नजदीकी अस्पताल जाएं।\n"
                    f"*हेल्पलाइन:* आरोग्यवाणी सेवा"
                )
            )

        if settings.DOCTOR_PHONE:
            _send_whatsapp(
                to_phone=settings.DOCTOR_PHONE,
                message=(
                    f"✅ *OPD → IPD ADMITTED*\n"
                    f"*Patient:* {patient.name if patient else 'Unknown'}\n"
                    f"*Phone:* {patient.phone if patient else 'Unknown'}\n"
                    f"*Condition:* {patient.condition if patient else ''}\n"
                    f"*Risk:* {admission.risk_tier}\n"
                    f"*Reason:* {admission.reason or 'High risk detected'}\n"
                    f"Patient has been notified via WhatsApp."
                )
            )

        return {"status": "admitted", "admission_id": admission_id}
    finally:
        db.close()


@router.post("/{admission_id}/discharge")
def discharge_patient(admission_id: int):
    db = SessionLocal()
    try:
        admission = db.query(Admission).filter(Admission.id == admission_id).first()
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")

        patient = db.query(Patient).filter(Patient.id == admission.patient_id).first()

        admission.status        = "discharged"
        admission.discharged_at = datetime.utcnow()
        db.commit()

        if patient and patient.phone:
            _send_whatsapp(
                to_phone=patient.phone,
                message=(
                    f"✅ *आरोग्यवाणी*\n"
                    f"नमस्ते {patient.name}!\n"
                    f"आपकी अस्पताल भर्ती की आवश्यकता नहीं है।\n"
                    f"कृपया अपना ध्यान रखें और दवाइयां लेते रहें।\n"
                    f"कोई तकलीफ हो तो तुरंत डॉक्टर से मिलें।"
                )
            )

        return {"status": "discharged", "admission_id": admission_id}
    finally:
        db.close()