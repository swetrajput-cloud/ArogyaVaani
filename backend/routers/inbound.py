from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from models.database import SessionLocal
from models.patient import Patient
from models.call_record import CallRecord
from nlp.intent_extractor import extract_intent
from nlp.risk_scorer import compute_risk
from dashboard.ws_broadcaster import broadcast_update
from datetime import datetime
import asyncio

router = APIRouter(prefix="/inbound", tags=["inbound"])

def get_or_create_patient(phone: str, db) -> Patient:
    """Find existing patient by phone or create new one."""
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        count = db.query(Patient).count()
        patient = Patient(
            name=f"Caller #{count + 1}",
            phone=phone,
            language="hindi",
            condition="General Monitoring",
            module_type="post_discharge",
            current_risk_tier="GREEN",
            caregiver_primary=False,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        print(f"[Inbound] New patient created: {phone} → ID {patient.id}")
    return patient

def twiml_say(text: str, language: str = "hi-IN") -> str:
    """Generate TwiML-compatible XML — works for both Twilio and Exotel."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{language}">{text}</Say>
    <Gather input="speech" language="{language}" timeout="5" action="/inbound/gather" method="POST">
        <Say language="{language}">कृपया बोलें।</Say>
    </Gather>
</Response>"""

@router.post("/voice")
async def inbound_voice(
    request: Request,
    CallSid: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
):
    """Exotel/Twilio calls this when someone calls the number."""
    db = SessionLocal()
    try:
        # Handle Exotel format (they send different field names)
        form = await request.form()
        call_sid = form.get("CallSid") or form.get("call_sid") or CallSid or "unknown"
        caller = form.get("From") or form.get("from") or From or "unknown"

        patient = get_or_create_patient(caller, db)

        asyncio.create_task(broadcast_update({
            "type": "new_call",
            "call_sid": call_sid,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "phone": caller,
            "risk_tier": patient.current_risk_tier,
            "message": f"Inbound call from {caller}",
        }))

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN">
        नमस्ते! आरोग्यवाणी में आपका स्वागत है।
        कृपया अपनी स्वास्थ्य समस्या बताएं।
        आप हिंदी या अंग्रेजी में बोल सकते हैं।
    </Say>
    <Gather input="speech" language="hi-IN" timeout="5" 
            action="/inbound/gather/{patient.id}/{call_sid}" method="POST">
        <Say language="hi-IN">कृपया बोलें।</Say>
    </Gather>
    <Say language="hi-IN">हमें आपकी आवाज़ नहीं सुनाई दी। कृपया दोबारा कॉल करें।</Say>
</Response>"""

        return Response(content=xml, media_type="application/xml")
    finally:
        db.close()

@router.post("/gather/{patient_id}/{call_sid}")
async def inbound_gather(
    request: Request,
    patient_id: int,
    call_sid: str,
    SpeechResult: str = Form(default=""),
):
    """Handles speech input from caller."""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Say language="hi-IN">Patient not found.</Say></Response>"""
            return Response(content=xml, media_type="application/xml")

        # Get transcript from form (Exotel may use different field name)
        form = await request.form()
        transcript = (
            form.get("SpeechResult") or 
            form.get("speech_result") or 
            SpeechResult or ""
        ).strip()

        print(f"[Inbound] Transcript from {patient.name}: {transcript}")

        # Run NLP + Risk scoring
        nlp_output = await extract_intent(transcript, language=patient.language or "hindi")
        risk_tier, escalate, reason, keywords = compute_risk(
            transcript,
            nlp_output,
            patient_risk_score=patient.overall_risk_score or 0.0
        )

        # Update patient risk tier
        patient.current_risk_tier = risk_tier
        db.commit()

        # Save call record
        call_record = CallRecord(
            patient_id=patient.id,
            call_sid=call_sid,
            module_type=patient.module_type or "post_discharge",
            language=patient.language or "hindi",
            transcript=transcript,
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

        # Broadcast to dashboard
        asyncio.create_task(broadcast_update({
            "type": "call_complete",
            "call_sid": call_sid,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "transcript": transcript,
            "nlp": nlp_output,
            "risk_tier": risk_tier,
            "escalate": escalate,
            "escalation_reason": reason,
        }))

        # Voice response based on risk
        if escalate or risk_tier == "RED":
            reply = (
                "आपकी स्थिति गंभीर लग रही है। "
                "हम तुरंत आपके डॉक्टर को सूचित कर रहे हैं। "
                "कृपया शांत रहें और नज़दीकी अस्पताल जाएं।"
            )
        elif risk_tier == "AMBER":
            reply = (
                "आपकी जानकारी दर्ज कर ली गई है। "
                "हमारी टीम जल्द आपसे संपर्क करेगी। "
                "अगर तकलीफ बढ़े तो तुरंत अस्पताल जाएं।"
            )
        else:
            reply = (
                "धन्यवाद! आपकी जानकारी सुरक्षित दर्ज हो गई है। "
                "स्वस्थ रहें और समय पर दवाई लेते रहें।"
            )

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN">{reply}</Say>
    <Gather input="speech" language="hi-IN" timeout="5"
            action="/inbound/followup/{patient.id}/{call_sid}" method="POST">
        <Say language="hi-IN">
            क्या आप कोई और जानकारी देना चाहते हैं?
        </Say>
    </Gather>
    <Say language="hi-IN">आपकी कॉल के लिए धन्यवाद। नमस्ते!</Say>
</Response>"""

        return Response(content=xml, media_type="application/xml")
    finally:
        db.close()

@router.post("/followup/{patient_id}/{call_sid}")
async def inbound_followup(
    request: Request,
    patient_id: int,
    call_sid: str,
    SpeechResult: str = Form(default=""),
):
    """Handle follow-up speech."""
    db = SessionLocal()
    try:
        form = await request.form()
        transcript = (
            form.get("SpeechResult") or
            form.get("speech_result") or
            SpeechResult or ""
        ).strip()

        patient = db.query(Patient).filter(Patient.id == patient_id).first()

        if transcript and patient:
            nlp_output = await extract_intent(transcript, language=patient.language or "hindi")
            risk_tier, escalate, reason, keywords = compute_risk(
                transcript, nlp_output,
                patient_risk_score=patient.overall_risk_score or 0.0
            )

            followup = CallRecord(
                patient_id=patient_id,
                call_sid=f"{call_sid}-followup",
                module_type="followup",
                language=patient.language or "hindi",
                transcript=transcript,
                structured_output=nlp_output,
                risk_tier=risk_tier,
                escalate_flag=escalate,
                escalation_reason=reason,
                call_status="completed",
                answered_by="patient",
                completed_at=datetime.utcnow(),
            )
            db.add(followup)

            if risk_tier == "RED":
                patient.current_risk_tier = "RED"
            db.commit()

            asyncio.create_task(broadcast_update({
                "type": "followup",
                "call_sid": call_sid,
                "patient_id": patient_id,
                "patient_name": patient.name,
                "transcript": transcript,
                "risk_tier": risk_tier,
                "escalate": escalate,
            }))

        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN">
        बहुत धन्यवाद। आपकी सारी जानकारी दर्ज कर ली गई है।
        आरोग्यवाणी टीम जल्द आपसे संपर्क करेगी। नमस्ते!
    </Say>
</Response>"""
        return Response(content=xml, media_type="application/xml")
    finally:
        db.close()

@router.post("/status")
async def inbound_status(request: Request):
    """Call status webhook."""
    form = await request.form()
    print(f"[Inbound Status] {dict(form)}")
    return {"status": "ok"}