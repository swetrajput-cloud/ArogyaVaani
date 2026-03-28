from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from datetime import date
from modules.vaccination_reminder_engine import (
    get_reminders_due_today,
    create_reminders_for_patient,
    mark_reminder_called,
)
from models.database import SessionLocal
from models.vaccination_reminder import VaccinationReminder
import httpx
from config import settings
import os

router = APIRouter(prefix="/vaccination-reminders", tags=["vaccination-reminders"])

BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")
TWILIO_URL = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Calls.json"


class RegisterBabyRequest(BaseModel):
    patient_id: int
    baby_dob:   str   # format: YYYY-MM-DD


@router.post("/register")
def register_baby(req: RegisterBabyRequest):
    """Register a baby's DOB and generate all vaccination reminders."""
    dob = date.fromisoformat(req.baby_dob)
    result = create_reminders_for_patient(req.patient_id, dob)
    return result


@router.get("/due-today")
def due_today():
    """List all reminders due to be called today."""
    return {"reminders": get_reminders_due_today()}


@router.get("/all")
def all_reminders():
    """List all reminders in DB."""
    db = SessionLocal()
    try:
        reminders = db.query(VaccinationReminder).order_by(
            VaccinationReminder.reminder_date
        ).all()
        return {
            "total": len(reminders),
            "reminders": [
                {
                    "id":            r.id,
                    "patient_name":  r.patient_name,
                    "patient_phone": r.patient_phone,
                    "vaccine_name":  r.vaccine_name,
                    "age_label":     r.age_label,
                    "due_date":      str(r.due_date),
                    "reminder_date": str(r.reminder_date),
                    "call_status":   r.call_status,
                    "called_at":     str(r.called_at) if r.called_at else None,
                }
                for r in reminders
            ]
        }
    finally:
        db.close()


async def _make_twilio_call(phone: str, reminder_id: int, vaccine_name: str, due_date: str):
    """Make a single Twilio call for a vaccination reminder."""
    twiml_url = f"{BASE_URL}/twilio/vaccination-reminder-twiml?vaccine={vaccine_name}&due={due_date}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TWILIO_URL,
                data={
                    "To":    phone,
                    "From":  settings.TWILIO_PHONE_NUMBER,
                    "Url":   twiml_url,
                    "Method": "POST",
                    "StatusCallback": f"{BASE_URL}/twilio/vaccination-status?reminder_id={reminder_id}",
                },
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            )
            result = resp.json()
            call_sid = result.get("sid", "")
            print(f"[VaxReminder] Called {phone} → SID: {call_sid}")
            mark_reminder_called(reminder_id, call_sid, "called")
            return call_sid
    except Exception as e:
        print(f"[VaxReminder] Call failed for {phone}: {e}")
        mark_reminder_called(reminder_id, "", "failed")
        return None


@router.post("/trigger-calls")
async def trigger_reminder_calls(background_tasks: BackgroundTasks):
    """Trigger Twilio calls for all reminders due today."""
    reminders = get_reminders_due_today()
    if not reminders:
        return {"message": "No reminders due today", "called": 0}

    called = 0
    for r in reminders:
        await _make_twilio_call(
            phone=r["patient_phone"],
            reminder_id=r["id"],
            vaccine_name=r["vaccine_name"],
            due_date=r["due_date"],
        )
        called += 1

    return {"message": f"Triggered {called} reminder calls", "called": called}