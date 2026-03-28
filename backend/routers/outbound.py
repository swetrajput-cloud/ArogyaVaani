from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.database import SessionLocal
from models.patient import Patient
from services.call_conductor import conduct_call, conduct_bulk_calls
from config import settings
import os

router = APIRouter(prefix="/outbound", tags=["outbound"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CallRequest(BaseModel):
    patient_id: int

class BulkCallRequest(BaseModel):
    risk_tiers: list = ["RED", "AMBER"]
    limit: int = 10
    delay_seconds: int = 5

@router.post("/call")
async def outbound_call(req: CallRequest, db: Session = Depends(get_db)):
    """Trigger an outbound call to a single patient via Exotel."""
    patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await conduct_call(req.patient_id)
    return result

@router.post("/bulk-call")
async def bulk_call(req: BulkCallRequest, background_tasks: BackgroundTasks):
    """Trigger outbound calls for multiple patients in background."""
    background_tasks.add_task(
        conduct_bulk_calls,
        risk_tiers=req.risk_tiers,
        limit=req.limit,
        delay_seconds=req.delay_seconds,
    )
    return {
        "status": "bulk calls started in background",
        "risk_tiers": req.risk_tiers,
        "limit": req.limit,
    }

@router.get("/preview/{patient_id}")
async def preview_call_script(patient_id: int):
    """Preview the call script for a patient without making the call."""
    from services.patient_selector import get_patient_call_profile
    from models_ai.call_brain import build_call_script

    profile = get_patient_call_profile(patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")

    script = build_call_script(
        patient_name=profile["name"],
        condition=profile["condition"],
        risk_level=profile["risk_tier"],
        language=profile["language"],
        max_questions=5
    )

    return {
        "patient": profile,
        "script": script,
    }
