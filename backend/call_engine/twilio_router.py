import httpx
import asyncio
import base64
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from config import settings
from models.database import SessionLocal
from models.patient import Patient
from models.call_record import CallRecord
from nlp.intent_extractor import extract_intent
from nlp.risk_scorer import compute_risk
from dashboard.ws_broadcaster import broadcast_update
from models_ai.call_brain import build_call_script, is_urgent, get_urgent_alert
from datetime import datetime
import os

router = APIRouter(prefix="/twilio", tags=["twilio"])
BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")

_call_states = {}


def _lang_code(language: str) -> str:
    return {
        "hindi":    "hi-IN",
        "marathi":  "mr-IN",
        "bengali":  "bn-IN",
        "tamil":    "ta-IN",
        "telugu":   "te-IN",
        "gujarati": "gu-IN",
        "english":  "en-IN",
    }.get(language.lower(), "hi-IN")


@router.post("/answered")
async def call_answered(
    request: Request,
    CallSid: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
):
    call_sid = CallSid or request.query_params.get("CallSid", "")
    print(f"[Twilio] Call answered: {call_sid} From:{From} To:{To}")

    patient_phone = To

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.phone == patient_phone).first()
        if not patient:
            clean = patient_phone.lstrip("+").lstrip("91")
            patient = db.query(Patient).filter(
                Patient.phone.contains(clean[-10:])
            ).first()

        if not patient:
            response = VoiceResponse()
            response.say("क्षमा करें, आपका रिकॉर्ड नहीं मिला। धन्यवाद।", language="hi-IN")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        _call_states[call_sid] = {
            "patient_id":         patient.id,
            "patient_name":       patient.name,
            "condition":          patient.condition,
            "risk_tier":          patient.current_risk_tier,
            "module_type":        patient.module_type,
            "language":           "hindi",
            "question_index":     0,
            "transcript_parts":   [],
            "script":             None,
            "overall_risk_score": patient.overall_risk_score or 0,
        }
    finally:
        db.close()

    response = VoiceResponse()
    gather = Gather(
        num_digits=1,
        action=f"{BASE_URL}/twilio/language-select?call_sid={call_sid}",
        method="POST",
        timeout=15,
        finishOnKey="",
    )
    gather.say(
        "नमस्ते! आरोग्यवाणी से आपका स्वागत है। "
        "हिंदी के लिए 1 दबाएं। "
        "English के लिए 3 दबाएं। "
        "कृपया अभी कोई बटन दबाएं।",
        language="hi-IN",
        voice="Polly.Aditi",
    )
    response.append(gather)

    response.redirect(
        f"{BASE_URL}/twilio/language-select?call_sid={call_sid}&default=hindi",
        method="POST"
    )
    return Response(content=str(response), media_type="application/xml")


@router.post("/language-select")
async def language_select(
    request: Request,
    CallSid: str = Form(default=""),
    Digits: str = Form(default=""),
):
    call_sid = CallSid or request.query_params.get("call_sid", "")
    default_lang = request.query_params.get("default", "")
    state = _call_states.get(call_sid)

    if not state:
        response = VoiceResponse()
        response.say("सत्र समाप्त हो गया। धन्यवाद।", language="hi-IN")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    if default_lang == "hindi" and not Digits:
        language = "hindi"
    else:
        lang_map = {"1": "hindi", "2": "marathi", "3": "english"}
        language = lang_map.get(Digits, "hindi")

    state["language"] = language
    print(f"[Twilio] Language selected: {language} (digits={Digits})")

    script = build_call_script(
        patient_name=state["patient_name"],
        condition=state["condition"],
        risk_level=state["risk_tier"],
        language=language,
        max_questions=5,
    )
    state["script"] = script
    state["question_index"] = 0

    twiml_lang = "en-IN" if language == "english" else "hi-IN"
    voice = "Polly.Raveena" if language == "hindi" else "Polly.Aditi"
    greeting = script["greeting"]
    first_q = script["questions"][0]["text"] if script["questions"] else script["closing"]

    response = VoiceResponse()
    response.say(greeting, language=twiml_lang, voice=voice)
    response.pause(length=1)
    response.say(first_q, language=twiml_lang, voice=voice)
    response.record(
        action=f"{BASE_URL}/twilio/record-answer?call_sid={call_sid}&q_index=0",
        method="POST",
        max_length=30,
        finish_on_key="#",
        play_beep=True,
        transcribe=False,
        timeout=5,
    )
    return Response(content=str(response), media_type="application/xml")


@router.post("/record-answer")
async def record_answer(
    request: Request,
    CallSid: str = Form(default=""),
    RecordingUrl: str = Form(default=""),
):
    call_sid = CallSid or request.query_params.get("call_sid", "")
    q_index = int(request.query_params.get("q_index", 0))
    state = _call_states.get(call_sid)

    if not state or not state.get("script"):
        response = VoiceResponse()
        response.say("धन्यवाद। फिर मिलेंगे।", language="hi-IN")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    language = state["language"]
    script = state["script"]
    twiml_lang = "en-IN" if language == "english" else "hi-IN"
    voice = "Polly.Raveena" if language == "hindi" else "Polly.Aditi"
    transcript = ""

    if RecordingUrl:
        try:
            from sarvam.stt import transcribe_audio, download_recording_with_retry

            auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            audio_bytes = await download_recording_with_retry(RecordingUrl, auth)

            print(f"[Twilio] Final recording size: {len(audio_bytes)} bytes")

            if len(audio_bytes) > 5000:
                transcript = await transcribe_audio(
                    audio_bytes, language=_lang_code(language)
                )
                print(f"[Twilio] Transcript q{q_index}: {transcript}")
            else:
                print(f"[Twilio] Recording too small, skipping STT")

        except Exception as e:
            print(f"[Twilio] STT Error: {e}")

    if transcript:
        state["transcript_parts"].append(transcript)

    if transcript and is_urgent(transcript, language):
        urgent_msg = get_urgent_alert(language)
        await _save_call_record(call_sid, state, "RED", True, "Urgent keyword detected")
        response = VoiceResponse()
        response.say(urgent_msg, language=twiml_lang, voice=voice)
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    nlp_output = {}
    risk_tier = "GREEN"
    escalate = False
    reason = ""
    if transcript:
        try:
            nlp_output = await extract_intent(transcript, language)
        except Exception as e:
            print(f"[Twilio] NLP Error: {e}")
        risk_tier, escalate, reason, _ = compute_risk(
            transcript, nlp_output, state["overall_risk_score"]
        )

    next_index = q_index + 1
    state["question_index"] = next_index

    response = VoiceResponse()

    if next_index < len(script["questions"]):
        next_q = script["questions"][next_index]["text"]
        response.say(next_q, language=twiml_lang, voice=voice)
        response.record(
            action=f"{BASE_URL}/twilio/record-answer?call_sid={call_sid}&q_index={next_index}",
            method="POST",
            max_length=30,
            finish_on_key="#",
            play_beep=True,
            transcribe=False,
            timeout=5,
        )
    else:
        await _save_call_record(call_sid, state, risk_tier, escalate, reason, nlp_output)
        response.say(script["closing"], language=twiml_lang, voice=voice)
        response.hangup()

    return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def call_status(
    request: Request,
    CallSid: str = Form(default=""),
    CallStatus: str = Form(default=""),
    CallDuration: str = Form(default="0"),
):
    call_sid = CallSid or request.query_params.get("CallSid", "")
    print(f"[Twilio] Status: {call_sid} → {CallStatus} ({CallDuration}s)")
    state = _call_states.get(call_sid)
    if state:
        await _save_call_record(
            call_sid, state, "GREEN", False, "",
            call_status=CallStatus,
            duration=int(CallDuration) if CallDuration.isdigit() else 0,
        )
        _call_states.pop(call_sid, None)
    return {"status": "ok"}


async def _save_call_record(
    call_sid, state, risk_tier, escalate, reason,
    nlp_output=None, call_status="completed", duration=0
):
    full_transcript = " | ".join(state.get("transcript_parts", []))
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == state["patient_id"]).first()
        if patient:
            patient.current_risk_tier = risk_tier
            patient.updated_at = datetime.utcnow()

        record = CallRecord(
            patient_id        = state["patient_id"],
            call_sid          = call_sid,
            module_type       = state.get("module_type", "post_discharge"),
            language          = state.get("language", "hindi"),
            transcript        = full_transcript,
            structured_output = nlp_output,
            risk_tier         = risk_tier,
            escalate_flag     = escalate,
            escalation_reason = reason,
            answered_by       = "patient",
            call_status       = call_status,
            call_duration     = duration,
            completed_at      = datetime.utcnow(),
        )
        db.add(record)
        db.commit()

        await broadcast_update({
            "call_sid":          call_sid,
            "patient_id":        state["patient_id"],
            "patient_name":      state.get("patient_name"),
            "risk_tier":         risk_tier,
            "escalate":          escalate,
            "escalation_reason": reason,
            "transcript":        full_transcript,
            "nlp":               nlp_output,
        })
        print(f"[Twilio] Saved. Patient:{state['patient_id']} Risk:{risk_tier}")
    except Exception as e:
        db.rollback()
        print(f"[Twilio] DB error: {e}")
    finally:
        db.close()