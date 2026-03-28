from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from models.database import SessionLocal
from models.patient import Patient
from models.call_record import CallRecord
from nlp.intent_extractor import extract_intent
from nlp.risk_scorer import compute_risk

router = APIRouter(prefix="/simulate", tags=["simulate"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SimulateRequest(BaseModel):
    patient_id: int
    transcript: str
    language: str = "hindi"

@router.post("/call")
async def simulate_call(req: SimulateRequest, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
    if not patient:
        return {"error": "Patient not found"}

    # Run NLP
    nlp_output = await extract_intent(req.transcript, language=req.language)

    # Run risk scorer
    risk_tier, escalate, reason, keywords = compute_risk(
        req.transcript,
        nlp_output,
        patient_risk_score=patient.overall_risk_score or 0.0
    )

    # Update patient risk tier
    patient.current_risk_tier = risk_tier
    db.commit()

    # Save call record to DB
    call_record = CallRecord(
        patient_id=req.patient_id,
        call_sid=f"SIM-{req.patient_id}-{int(datetime.utcnow().timestamp())}",
        module_type=patient.module_type or "post_discharge",
        language=req.language,
        transcript=req.transcript,
        structured_output=nlp_output,
        risk_tier=risk_tier,
        escalate_flag=escalate,
        escalation_reason=reason,
        call_status="completed",
        answered_by="patient",
        completed_at=datetime.utcnow(),
    )
    db.add(call_record)
    db.commit()

    return {
        "patient_id": patient.id,
        "patient_name": patient.name,
        "transcript": req.transcript,
        "language": req.language,
        "nlp": nlp_output,
        "risk_tier": risk_tier,
        "escalate": escalate,
        "escalation_reason": reason,
        "keywords": keywords,
    }