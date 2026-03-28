import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.database import SessionLocal
from models.patient import Patient
from services.twilio_service import make_call
from config import settings

router = APIRouter(prefix="/outbound", tags=["outbound"])
BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")

class CallRequest(BaseModel):
    patient_id: int

@router.post("/call")
async def trigger_call(req: CallRequest):
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        result = make_call(
            to_number           = patient.phone,
            callback_url        = f"{BASE_URL}/twilio/answered",
            status_callback_url = f"{BASE_URL}/twilio/status",
        )
        return {
            "status":          "call initiated",
            "patient":         patient.name,
            "phone":           patient.phone,
            "risk_tier":       patient.current_risk_tier,
            "twilio_response": result,
        }
    finally:
        db.close()

@router.get("/preview/{patient_id}")
async def preview_script(patient_id: int):
    from models_ai.call_brain import build_call_script
    from services.patient_selector import get_patient_call_profile

    profile = get_patient_call_profile(patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")

    script = build_call_script(
        patient_name  = profile["name"],
        condition     = profile["condition"],
        risk_level    = profile["risk_tier"],
        language      = profile["language"],
        max_questions = 5,
    )
    return {"patient": profile, "script": script}
