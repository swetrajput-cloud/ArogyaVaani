from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from models.database import SessionLocal
from models.call_record import CallRecord
from models.patient import Patient
from datetime import datetime

router = APIRouter(prefix="/calls", tags=["calls"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def get_call_history(
    risk_tier: Optional[str] = Query(None),
    escalated_only: bool = Query(False),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    query = db.query(CallRecord, Patient).join(
        Patient, CallRecord.patient_id == Patient.id
    )
    if risk_tier:
        query = query.filter(CallRecord.risk_tier == risk_tier.upper())
    if escalated_only:
        query = query.filter(CallRecord.escalate_flag == True)

    total = query.count()
    results = query.order_by(CallRecord.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "calls": [
            {
                "id": call.id,
                "patient_id": call.patient_id,
                "patient_name": patient.name,
                "patient_phone": patient.phone,
                "call_sid": call.call_sid,
                "module_type": call.module_type,
                "language": call.language,
                "transcript": call.transcript,
                "structured_output": call.structured_output,
                "risk_tier": call.risk_tier,
                "escalate_flag": call.escalate_flag,
                "escalation_reason": call.escalation_reason,
                "adherence_score": call.adherence_score,
                "answered_by": call.answered_by,
                "call_status": call.call_status,
                "call_duration": call.call_duration,
                "created_at": call.created_at.isoformat() if call.created_at else None,
                "completed_at": call.completed_at.isoformat() if call.completed_at else None,
            }
            for call, patient in results
        ]
    }

@router.get("/stats")
def get_call_stats(db: Session = Depends(get_db)):
    total     = db.query(CallRecord).count()
    red       = db.query(CallRecord).filter(CallRecord.risk_tier == "RED").count()
    amber     = db.query(CallRecord).filter(CallRecord.risk_tier == "AMBER").count()
    green     = db.query(CallRecord).filter(CallRecord.risk_tier == "GREEN").count()
    escalated = db.query(CallRecord).filter(CallRecord.escalate_flag == True).count()
    return {
        "total_calls": total,
        "red": red,
        "amber": amber,
        "green": green,
        "escalated": escalated,
    }

@router.get("/{call_id}")
def get_call_detail(call_id: int, db: Session = Depends(get_db)):
    result = db.query(CallRecord, Patient).join(
        Patient, CallRecord.patient_id == Patient.id
    ).filter(CallRecord.id == call_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Call not found")

    call, patient = result
    return {
        "id": call.id,
        "patient_id": call.patient_id,
        "patient_name": patient.name,
        "patient_phone": patient.phone,
        "call_sid": call.call_sid,
        "module_type": call.module_type,
        "language": call.language,
        "transcript": call.transcript,
        "structured_output": call.structured_output,
        "risk_tier": call.risk_tier,
        "escalate_flag": call.escalate_flag,
        "escalation_reason": call.escalation_reason,
        "adherence_score": call.adherence_score,
        "answered_by": call.answered_by,
        "call_status": call.call_status,
        "call_duration": call.call_duration,
        "created_at": call.created_at.isoformat() if call.created_at else None,
        "completed_at": call.completed_at.isoformat() if call.completed_at else None,
    }
@router.get("/patient/{patient_id}")
def get_calls_by_patient(patient_id: int, db: Session = Depends(get_db)):
    results = db.query(CallRecord, Patient).join(
        Patient, CallRecord.patient_id == Patient.id
    ).filter(CallRecord.patient_id == patient_id)\
     .order_by(CallRecord.created_at.desc()).limit(50).all()

    return {
        "calls": [
            {
                "id": call.id,
                "patient_id": call.patient_id,
                "patient_name": patient.name,
                "patient_phone": patient.phone,
                "call_sid": call.call_sid,
                "module_type": call.module_type,
                "language": call.language,
                "transcript": call.transcript,
                "structured_output": call.structured_output,
                "risk_tier": call.risk_tier,
                "escalate_flag": call.escalate_flag,
                "escalation_reason": call.escalation_reason,
                "call_status": call.call_status,
                "answered_by": call.answered_by,
                "created_at": call.created_at.isoformat() if call.created_at else None,
                "completed_at": call.completed_at.isoformat() if call.completed_at else None,
            }
            for call, patient in results
        ]
    }