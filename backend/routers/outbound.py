from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.database import SessionLocal
from models.patient import Patient
from services.exotel import make_call
from config import settings

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
    """Trigger an outbound call to a patient."""
    patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
    if not patient:
        return {"error": "Patient not found"}

    callback_url = f"https://rosa-unadulterated-victoriously.ngrok-free.dev/inbound/voice"

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
        "exotel_response": result,
    }