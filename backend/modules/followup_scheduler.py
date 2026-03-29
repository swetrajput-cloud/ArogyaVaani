import asyncio
from datetime import datetime, timedelta
from models.database import SessionLocal
from models.patient import Patient
from services.twilio_service import make_call
from config import settings
import os

BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")

# How often the scheduler checks (every 30 minutes)
CHECK_INTERVAL_SECONDS = 30 * 60

# How long after last call before auto follow-up triggers (2 hours)
FOLLOWUP_AFTER_SECONDS = 2 * 60 * 60


async def run_followup_scheduler():
    print("[FollowUp] Scheduler started — checking every 30 minutes")
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        await check_and_call_red_patients()


async def check_and_call_red_patients():
    print("[FollowUp] Checking for RED patients needing follow-up...")
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=FOLLOWUP_AFTER_SECONDS)

        # Find RED patients whose last call was more than 2 hours ago
        # or who have never been called at all
        patients = (
            db.query(Patient)
            .filter(
                Patient.current_risk_tier == "RED",
                Patient.is_active == True,
            )
            .all()
        )

        called = 0
        for patient in patients:
            # Skip if called within last 2 hours
            if patient.last_called_at and patient.last_called_at > cutoff:
                continue

            try:
                make_call(
                    to_number=patient.phone,
                    callback_url=f"{BASE_URL}/twilio/answered",
                    status_callback_url=f"{BASE_URL}/twilio/status",
                )
                # Update last_called_at so we don't call again for 2 hours
                patient.last_called_at = now
                db.commit()
                called += 1
                print(f"[FollowUp] Auto follow-up call triggered for Patient:{patient.id} ({patient.name})")

                # Small delay between calls to avoid Twilio rate limits
                await asyncio.sleep(3)

            except Exception as e:
                print(f"[FollowUp] Failed to call Patient:{patient.id} — {e}")

        print(f"[FollowUp] Done. {called} follow-up calls triggered.")

    except Exception as e:
        print(f"[FollowUp] Scheduler error: {e}")
    finally:
        db.close()