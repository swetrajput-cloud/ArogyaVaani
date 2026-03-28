from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.database import SessionLocal
from models.patient import Patient
from services.exotel import make_call
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

@router.post("/call")
async def outbound_call(req: CallRequest, db: Session = Depends(get_db)):
    """Trigger an outbound call to a patient via Exotel."""
    patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Use BASE_URL from env so it works both locally (ngrok) and on Railway
    base_url = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    callback_url = f"{base_url}/inbound/voice"

    result = await make_call(
        to_number=patient.phone,
        from_number=settings.EXOTEL_PHONE_NUMBER,
        api_key=settings.EXOTEL_API_KEY,
        api_token=settings.EXOTEL_API_TOKEN,
        account_sid=settings.EXOTEL_ACCOUNT_SID,
        callback_url=callback_url,
    )

    return {
        "status": "call initiated",
        "patient": patient.name,
        "phone": patient.phone,
        "callback_url": callback_url,
        "exotel_response": result,
    }
