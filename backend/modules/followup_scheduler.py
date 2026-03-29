import asyncio
from datetime import datetime, timedelta
from models.database import SessionLocal
from models.patient import Patient
from services.twilio_service import make_call
import os

BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")

# Check every 30 minutes
CHECK_INTERVAL_SECONDS = 30 * 60

# RED patients: follow-up after 2 hours
RED_FOLLOWUP_SECONDS = 2 * 60 * 60

# AMBER patients: follow-up after 2 weeks
AMBER_FOLLOWUP_SECONDS = 14 * 24 * 60 * 60


async def run_followup_scheduler():
    print("[FollowUp] Scheduler started — checking every 30 minutes")
    print("[FollowUp] RED patients: auto-call every 2 hours")
    print("[FollowUp] AMBER patients: auto-call every 2 weeks")
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        await check_and_call_patients()


async def check_and_call_patients():
    print("[FollowUp] Checking RED and AMBER patients...")
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        red_cutoff   = now - timedelta(seconds=RED_FOLLOWUP_SECONDS)
        amber_cutoff = now - timedelta(seconds=AMBER_FOLLOWUP_SECONDS)

        patients = (
            db.query(Patient)
            .filter(
                Patient.current_risk_tier.in_(["RED", "AMBER"]),
                Patient.is_active == True,
            )
            .all()
        )

        called = 0
        for patient in patients:
            is_red   = patient.current_risk_tier == "RED"
            is_amber = patient.current_risk_tier == "AMBER"
            cutoff   = red_cutoff if is_red else amber_cutoff

            # Skip if called recently enough
            if patient.last_called_at and patient.last_called_at > cutoff:
                continue

            try:
                make_call(
                    to_number           = patient.phone,
                    callback_url        = f"{BASE_URL}/twilio/answered",
                    status_callback_url = f"{BASE_URL}/twilio/status",
                )
                patient.last_called_at = now
                db.commit()
                called += 1
                tier_label = "RED (2hr)" if is_red else "AMBER (2wk)"
                print(f"[FollowUp] {tier_label} call → Patient:{patient.id} ({patient.name})")

                # Avoid Twilio rate limits
                await asyncio.sleep(3)

            except Exception as e:
                print(f"[FollowUp] Failed Patient:{patient.id} — {e}")

        print(f"[FollowUp] Done. {called} calls triggered.")

    except Exception as e:
        print(f"[FollowUp] Scheduler error: {e}")
    finally:
        db.close()