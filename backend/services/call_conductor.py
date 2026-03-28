import asyncio
from models_ai.call_brain import build_call_script, is_urgent
from services.patient_selector import get_patient_call_profile
from services.exotel import make_call
from models.database import SessionLocal
from models.patient import Patient
from models.call_record import CallRecord
from dashboard.ws_broadcaster import broadcast_update
from config import settings
from datetime import datetime
import os

async def conduct_call(patient_id: int) -> dict:
    """
    Full pipeline: get patient → build script → make call → return result.
    """
    # Get patient profile
    profile = get_patient_call_profile(patient_id)
    if not profile:
        return {"error": f"Patient {patient_id} not found"}

    # Build call script
    script = build_call_script(
        patient_name=profile["name"],
        condition=profile["condition"],
        risk_level=profile["risk_tier"],
        language=profile["language"],
        max_questions=5
    )

    print(f"[CallConductor] Script for {profile['name']}: {script['total_questions']} questions")

    # Get callback URL
    base_url = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    callback_url = f"{base_url}/inbound/voice"

    # Initiate Exotel call
    result = await make_call(
        to_number=profile["phone"],
        from_number=settings.EXOTEL_PHONE_NUMBER,
        api_key=settings.EXOTEL_API_KEY,
        api_token=settings.EXOTEL_API_TOKEN,
        account_sid=settings.EXOTEL_ACCOUNT_SID,
        callback_url=callback_url,
    )

    # Save initial call record
    db = SessionLocal()
    try:
        call_record = CallRecord(
            patient_id=patient_id,
            call_sid=result.get("Call", {}).get("Sid", f"PENDING-{patient_id}"),
            module_type=profile["module_type"],
            language=profile["language"],
            transcript="",
            risk_tier=profile["risk_tier"],
            escalate_flag=False,
            call_status="initiated",
            answered_by="",
        )
        db.add(call_record)
        db.commit()
        print(f"[CallConductor] Call record saved for patient {patient_id}")
    except Exception as e:
        print(f"[CallConductor] DB error: {e}")
    finally:
        db.close()

    # Broadcast to dashboard
    await broadcast_update({
        "type": "call_initiated",
        "patient_id": patient_id,
        "patient_name": profile["name"],
        "risk_tier": profile["risk_tier"],
        "phone": profile["phone"],
        "script": script,
        "exotel_response": result,
    })

    return {
        "patient_id": patient_id,
        "patient_name": profile["name"],
        "phone": profile["phone"],
        "script": script,
        "exotel_response": result,
    }


async def conduct_bulk_calls(
    risk_tiers: list = ["RED", "AMBER"],
    limit: int = 10,
    delay_seconds: int = 5
) -> dict:
    """
    Conduct calls for multiple patients with a delay between each.
    """
    from services.patient_selector import get_patients_for_calling
    patients = get_patients_for_calling(risk_tiers=risk_tiers, limit=limit)

    print(f"[CallConductor] Starting bulk calls for {len(patients)} patients")

    results = []
    for i, patient in enumerate(patients):
        print(f"[CallConductor] Calling patient {i+1}/{len(patients)}: {patient['name']}")
        result = await conduct_call(patient["id"])
        results.append(result)
        if i < len(patients) - 1:
            await asyncio.sleep(delay_seconds)

    return {
        "total_called": len(results),
        "results": results,
    }