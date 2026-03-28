from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import SessionLocal
from models.appointment import Appointment
from models.patient import Patient
from alerts.doctor_sms import _send_whatsapp
from config import settings
from datetime import datetime

router = APIRouter(prefix="/appointments", tags=["appointments"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def list_appointments(status: str = None, db: Session = Depends(get_db)):
    q = db.query(Appointment).join(Patient)
    if status:
        q = q.filter(Appointment.status == status)
    appts = q.order_by(Appointment.requested_at.desc()).limit(50).all()
    return {"appointments": [_serialize(a) for a in appts]}

@router.post("/{appt_id}/confirm")
def confirm_appointment(appt_id: int, db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "confirmed"
    appt.confirmed_at = datetime.utcnow()
    db.commit()

    # Send WhatsApp confirmation to patient
    patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
    if patient and patient.phone:
        _send_whatsapp(
            to_phone=patient.phone,
            message=(
                f"✅ नमस्ते {patient.name} जी!\n"
                f"आपकी अपॉइंटमेंट कन्फर्म हो गई है।\n"
                f"कारण: {appt.reason or 'स्वास्थ्य जांच'}\n"
                f"आरोग्यवाणी स्वास्थ्य सेवा"
            )
        )
    return {"status": "confirmed", "id": appt_id}

@router.post("/{appt_id}/reject")
def reject_appointment(appt_id: int, db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "rejected"
    db.commit()
    return {"status": "rejected", "id": appt_id}

def _serialize(a: Appointment):
    return {
        "id":            a.id,
        "patient_id":    a.patient_id,
        "patient_name":  a.patient.name if a.patient else "Unknown",
        "patient_phone": a.patient.phone if a.patient else "",
        "call_sid":      a.call_sid,
        "reason":        a.reason,
        "status":        a.status,
        "requested_at":  a.requested_at.isoformat() if a.requested_at else None,
        "confirmed_at":  a.confirmed_at.isoformat() if a.confirmed_at else None,
    }