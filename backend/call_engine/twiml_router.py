from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from call_engine.state_machine import create_session, get_session, CallState
from call_engine.caregiver_proxy import should_use_caregiver, get_caregiver_number
from models.database import SessionLocal
from models.patient import Patient
from models.call_record import CallRecord
from sarvam.tts import synthesize_speech
from config import settings
from datetime import datetime
import asyncio

router = APIRouter(prefix="/webhook", tags=["twilio"])

def get_twilio_client():
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

@router.post("/answered")
async def call_answered(request: Request, CallSid: str = Form(...)):
    """Twilio hits this when patient picks up. Returns TwiML to open Media Stream."""
    session = get_session(CallSid)
    if not session:
        resp = VoiceResponse()
        resp.say("Sorry, session not found.")
        return Response(content=str(resp), media_type="application/xml")

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
        if not patient:
            resp = VoiceResponse()
            resp.say("Patient not found.")
            return Response(content=str(resp), media_type="application/xml")

        # Check caregiver proxy
        if should_use_caregiver(patient):
            caregiver_num = get_caregiver_number(patient)
            if caregiver_num:
                session.answered_by = "caregiver"
                resp = VoiceResponse()
                resp.say("Transferring to caregiver.")
                resp.dial(caregiver_num)
                return Response(content=str(resp), media_type="application/xml")

        # Open Media Stream for real-time audio
        module = session.module_type
        language = session.language

        # Get first question via TTS
        from modules import pre_arrival, post_discharge, chronic_coach, caregiver as caregiver_mod
        MODULE_MAP = {
            "pre_arrival": pre_arrival,
            "post_discharge": post_discharge,
            "chronic_coach": chronic_coach,
            "caregiver": caregiver_mod,
        }
        mod = MODULE_MAP.get(module, post_discharge)
        first_question = mod.get_question(0, language)

        resp = VoiceResponse()
        resp.say(first_question, language="hi-IN")

        # Connect to Media Stream WebSocket
        connect = Connect()
        stream = Stream(url=f"wss://{request.headers.get('host')}/ws/stream/{CallSid}")
        connect.append(stream)
        resp.append(connect)

        session.transition(CallState.QUESTIONING)
        return Response(content=str(resp), media_type="application/xml")
    finally:
        db.close()

@router.post("/status")
async def call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str = Form(default="0")
):
    """Twilio hits this when call ends. Saves CallRecord to DB."""
    session = get_session(CallSid)
    if not session:
        return {"status": "no session"}

    db = SessionLocal()
    try:
        record = CallRecord(
            patient_id=session.patient_id,
            call_sid=CallSid,
            module_type=session.module_type,
            language=session.language,
            transcript=session.full_transcript(),
            structured_output=session.nlp_outputs[-1] if session.nlp_outputs else None,
            risk_tier=session.risk_tier,
            escalate_flag=session.escalate_flag,
            escalation_reason=session.escalation_reason,
            answered_by=session.answered_by,
            call_status=CallStatus,
            call_duration=int(CallDuration) if CallDuration.isdigit() else None,
            completed_at=datetime.utcnow(),
        )
        db.add(record)

        # Update patient risk tier
        patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
        if patient:
            patient.current_risk_tier = session.risk_tier
            patient.updated_at = datetime.utcnow()

        db.commit()
        print(f"[Status] Call {CallSid} saved. Risk: {session.risk_tier}")
    except Exception as e:
        db.rollback()
        print(f"[Status] DB error: {e}")
    finally:
        db.close()

    return {"status": "saved"}

@router.post("/initiate/{patient_id}")
async def initiate_call(patient_id: int, request: Request):
    """API endpoint to trigger an outbound call to a patient."""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        client = get_twilio_client()
        call = client.calls.create(
            to=patient.phone,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=f"https://{request.headers.get('host')}/webhook/answered",
            status_callback=f"https://{request.headers.get('host')}/webhook/status",
            status_callback_method="POST",
        )

        # Create session
        create_session(
            call_sid=call.sid,
            patient_id=patient.id,
            module_type=patient.module_type,
            language=patient.language,
        )

        return {"call_sid": call.sid, "status": "initiated"}
    finally:
        db.close()