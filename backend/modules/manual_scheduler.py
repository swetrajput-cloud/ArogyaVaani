"""
Runs every 60 seconds.
Finds pending scheduled calls whose scheduled_at <= now, fires them via Twilio,
and injects the custom_note into the call state so Groq mentions it naturally.
"""

import asyncio
import os
from datetime import datetime
from models.database import SessionLocal
from models.scheduled_call import ScheduledCall
from models.patient import Patient
from services.twilio_service import make_call

BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")


async def run_manual_scheduler():
    print("[ManualScheduler] Started — checking every 60 seconds")
    while True:
        try:
            _fire_due_calls()
        except Exception as e:
            print(f"[ManualScheduler] Error: {e}")
        await asyncio.sleep(60)


def _fire_due_calls():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due = db.query(ScheduledCall).filter(
            ScheduledCall.status       == "pending",
            ScheduledCall.scheduled_at <= now,
        ).all()

        if not due:
            return

        print(f"[ManualScheduler] {len(due)} call(s) due — firing now")

        for entry in due:
            patient = db.query(Patient).filter(Patient.id == entry.patient_id).first()
            if not patient:
                entry.status = "failed"
                db.commit()
                continue

            try:
                # Pass custom_note as query param so twilio/answered can pick it up
                note_param = ""
                if entry.custom_note:
                    import urllib.parse
                    note_param = f"&custom_note={urllib.parse.quote(entry.custom_note)}"

                result = make_call(
                    to_number           = patient.phone,
                    callback_url        = f"{BASE_URL}/twilio/answered?schedule_id={entry.id}{note_param}",
                    status_callback_url = f"{BASE_URL}/twilio/status",
                )

                entry.status   = "called"
                entry.call_sid = result.get("sid")
                entry.fired_at = datetime.utcnow()
                db.commit()
                print(f"[ManualScheduler] Fired: Patient {patient.name} ({patient.phone}) SID:{entry.call_sid}")

            except Exception as e:
                print(f"[ManualScheduler] Failed for patient {patient.id}: {e}")
                entry.status = "failed"
                db.commit()

    finally:
        db.close()