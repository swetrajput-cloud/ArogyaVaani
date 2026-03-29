import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.database import SessionLocal
from models.patient import Patient
from models.scheduled_call import ScheduledCall

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ─────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────

class ScheduleSingleRequest(BaseModel):
    patient_id:   int
    scheduled_at: datetime        # ISO format: "2026-03-30T14:30:00"
    custom_note:  Optional[str] = None

class ScheduleBulkRequest(BaseModel):
    scheduled_at: datetime
    custom_note:  Optional[str] = None
    # Filters — all optional, combined with AND
    condition:    Optional[str] = None   # e.g. "Diabetes", "Heart Disease"
    risk_tier:    Optional[str] = None   # "RED", "AMBER", "GREEN"
    camp_name:    Optional[str] = None   # partial match on health_camp_name


# ─────────────────────────────────────────────
# Schedule a single patient
# ─────────────────────────────────────────────

@router.post("/single")
def schedule_single(req: ScheduleSingleRequest):
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        entry = ScheduledCall(
            patient_id   = req.patient_id,
            scheduled_at = req.scheduled_at,
            custom_note  = req.custom_note,
            status       = "pending",
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return {
            "status":       "scheduled",
            "id":           entry.id,
            "patient":      patient.name,
            "scheduled_at": entry.scheduled_at.isoformat(),
            "custom_note":  entry.custom_note,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
# Bulk schedule by filters
# ─────────────────────────────────────────────

@router.post("/bulk")
def schedule_bulk(req: ScheduleBulkRequest):
    db = SessionLocal()
    try:
        query = db.query(Patient)

        if req.condition:
            query = query.filter(Patient.condition.ilike(f"%{req.condition}%"))
        if req.risk_tier:
            query = query.filter(Patient.current_risk_tier == req.risk_tier.upper())
        if req.camp_name:
            query = query.filter(Patient.health_camp_name.ilike(f"%{req.camp_name}%"))

        patients = query.all()
        if not patients:
            raise HTTPException(status_code=404, detail="No patients match the given filters")

        entries = []
        for patient in patients:
            entry = ScheduledCall(
                patient_id   = patient.id,
                scheduled_at = req.scheduled_at,
                custom_note  = req.custom_note,
                status       = "pending",
            )
            db.add(entry)
            entries.append(patient.name)

        db.commit()
        return {
            "status":         "scheduled",
            "total_patients": len(entries),
            "scheduled_at":   req.scheduled_at.isoformat(),
            "custom_note":    req.custom_note,
            "patients":       entries,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
# List all scheduled calls
# ─────────────────────────────────────────────

@router.get("/list")
def list_scheduled(status: Optional[str] = None):
    db = SessionLocal()
    try:
        query = db.query(ScheduledCall)
        if status:
            query = query.filter(ScheduledCall.status == status)
        calls = query.order_by(ScheduledCall.scheduled_at).all()

        result = []
        for c in calls:
            patient = db.query(Patient).filter(Patient.id == c.patient_id).first()
            result.append({
                "id":           c.id,
                "patient_id":   c.patient_id,
                "patient_name": patient.name if patient else "Unknown",
                "patient_phone":patient.phone if patient else "",
                "scheduled_at": c.scheduled_at.isoformat(),
                "custom_note":  c.custom_note,
                "status":       c.status,
                "call_sid":     c.call_sid,
                "fired_at":     c.fired_at.isoformat() if c.fired_at else None,
                "created_at":   c.created_at.isoformat(),
            })
        return result
    finally:
        db.close()


# ─────────────────────────────────────────────
# Cancel a scheduled call
# ─────────────────────────────────────────────

@router.delete("/{schedule_id}")
def cancel_schedule(schedule_id: int):
    db = SessionLocal()
    try:
        entry = db.query(ScheduledCall).filter(ScheduledCall.id == schedule_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Scheduled call not found")
        if entry.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot cancel — status is '{entry.status}'")
        entry.status = "cancelled"
        db.commit()
        return {"status": "cancelled", "id": schedule_id}
    finally:
        db.close()


# ─────────────────────────────────────────────
# Preview patients matching bulk filters
# ─────────────────────────────────────────────

@router.get("/preview")
def preview_bulk(
    condition: Optional[str] = None,
    risk_tier: Optional[str] = None,
    camp_name: Optional[str] = None,
):
    db = SessionLocal()
    try:
        query = db.query(Patient)
        if condition:
            query = query.filter(Patient.condition.ilike(f"%{condition}%"))
        if risk_tier:
            query = query.filter(Patient.current_risk_tier == risk_tier.upper())
        if camp_name:
            query = query.filter(Patient.health_camp_name.ilike(f"%{camp_name}%"))

        patients = query.all()
        return {
            "total": len(patients),
            "patients": [
                {
                    "id":        p.id,
                    "name":      p.name,
                    "phone":     p.phone,
                    "condition": p.condition,
                    "risk_tier": p.current_risk_tier,
                    "camp":      p.health_camp_name,
                    "language":  p.language,
                }
                for p in patients
            ]
        }
    finally:
        db.close()