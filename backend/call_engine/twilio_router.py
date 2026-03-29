import httpx
import asyncio
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from config import settings
from models.database import SessionLocal
from models.patient import Patient
from models.call_record import CallRecord
from models.appointment import Appointment
from models.vaccination_reminder import VaccinationReminder
from models.admission import Admission
from nlp.intent_extractor import extract_intent
from nlp.risk_scorer import compute_risk
from dashboard.ws_broadcaster import broadcast_update
from models_ai.call_brain import build_call_script, is_urgent, get_urgent_alert
from modules.vaccination_reminder_engine import mark_reminder_called
from alerts.doctor_sms import send_doctor_alert, _send_whatsapp
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


def _twiml_lang(language: str) -> str:
    return "en-IN" if language == "english" else "hi-IN"


def _voice(language: str) -> str:
    voices = {
        "hindi":   "Polly.Aditi",
        "english": "Polly.Raveena",
        "marathi": "Polly.Aditi",
        "tamil":   "Polly.Aditi",
    }
    return voices.get(language, "Polly.Aditi")


def _finish_instruction(language: str) -> str:
    instructions = {
        "hindi":   " बोलने के बाद # दबाएं।",
        "english": " Press # when done speaking.",
        "marathi": " बोलून झाल्यावर # दाबा।",
        "tamil":   " பேசி முடிந்தால் # அழுத்துங்கள்।",
    }
    return instructions.get(language, " बोलने के बाद # दबाएं।")


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
            "health_camp_name":   patient.health_camp_name or "",
            "module_type":        patient.module_type,
            "language":           "hindi",
            "question_index":     0,
            "transcript_parts":   [],
            "script":             None,
            "overall_risk_score": patient.overall_risk_score or 0,
            "record_saved":       False,
            "patient_phone":      patient.phone or "",
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
        lang_map = {"1": "hindi", "2": "marathi", "3": "english", "4": "tamil"}
        language = lang_map.get(Digits, "hindi")

    state["language"] = language
    print(f"[Twilio] Language selected: {language} (digits={Digits})")

    script = build_call_script(
        patient_name=state["patient_name"],
        condition=state["condition"],
        risk_level=state["risk_tier"],
        language=language,
        camp=state.get("health_camp_name", ""),
        max_questions=None,
    )
    state["script"] = script
    state["question_index"] = 0

    greeting = script["greeting"]
    first_q = script["questions"][0]["text"] if script["questions"] else script["closing"]
    finish_instr = _finish_instruction(language)

    response = VoiceResponse()
    response.say(greeting, language=_twiml_lang(language), voice=_voice(language))
    response.pause(length=1)
    response.say(first_q + finish_instr, language=_twiml_lang(language), voice=_voice(language))
    response.record(
        action=f"{BASE_URL}/twilio/record-answer?call_sid={call_sid}&q_index=0",
        method="POST",
        max_length=25,
        finish_on_key="#",
        play_beep=True,
        transcribe=False,
        timeout=8,
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

    webhook_key = f"webhook_{call_sid}_{q_index}"
    if state.get(webhook_key):
        print(f"[Twilio] Duplicate webhook ignored for {call_sid} q{q_index}")
        return Response(content="<Response/>", media_type="application/xml")
    state[webhook_key] = True

    language = state["language"]
    script = state["script"]
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
        await broadcast_update({
            "call_sid":          call_sid,
            "patient_id":        state["patient_id"],
            "patient_name":      state.get("patient_name"),
            "risk_tier":         state.get("risk_tier", "GREEN"),
            "escalate":          False,
            "escalation_reason": "",
            "transcript":        transcript,
            "nlp":               {},
        })
        print(f"[Dashboard] Live broadcast sent for patient {state['patient_id']}")

    if transcript and is_urgent(transcript, language):
        urgent_msg = get_urgent_alert(language)
        urgent_nlp = {}
        try:
            urgent_nlp = await extract_intent(transcript, language)
        except Exception as e:
            print(f"[Twilio] NLP Error (urgent): {e}")
        await _save_call_record(call_sid, state, "RED", True, "Urgent keyword detected", urgent_nlp)
        response = VoiceResponse()
        response.say(urgent_msg, language=_twiml_lang(language), voice=_voice(language))
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
        finish_instr = _finish_instruction(language)
        response.say(next_q + finish_instr, language=_twiml_lang(language), voice=_voice(language))
        response.record(
            action=f"{BASE_URL}/twilio/record-answer?call_sid={call_sid}&q_index={next_index}",
            method="POST",
            max_length=25,
            finish_on_key="#",
            play_beep=True,
            transcribe=False,
            timeout=8,
        )
    else:
        await _save_call_record(call_sid, state, risk_tier, escalate, reason, nlp_output)
        response.say(script["closing"], language=_twiml_lang(language), voice=_voice(language))
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
    _call_states.pop(call_sid, None)
    return {"status": "ok"}


@router.post("/vaccination-reminder-twiml")
async def vaccination_reminder_twiml(request: Request):
    vaccine = request.query_params.get("vaccine", "टीका")
    due     = request.query_params.get("due", "अगले सप्ताह")

    response = VoiceResponse()
    response.say(
        f"नमस्ते! आरोग्यवाणी से एक महत्वपूर्ण सूचना। "
        f"आपके बच्चे का {vaccine} का टीका {due} को लगवाना है। "
        f"कृपया अपने नजदीकी स्वास्थ्य केंद्र में जाएं। "
        f"यह कॉल आरोग्यवाणी स्वास्थ्य सेवा द्वारा है। धन्यवाद।",
        language="hi-IN",
        voice="Polly.Aditi",
    )
    response.pause(length=1)
    response.say(
        f"Reminder: {vaccine} vaccination is due on {due}. "
        f"Please visit your nearest health center. Thank you.",
        language="en-IN",
        voice="Polly.Raveena",
    )
    response.hangup()
    return Response(content=str(response), media_type="application/xml")


@router.post("/vaccination-status")
async def vaccination_call_status(request: Request):
    reminder_id = request.query_params.get("reminder_id")
    form        = await request.form()
    status      = form.get("CallStatus", "")
    call_sid    = form.get("CallSid", "")
    print(f"[VaxReminder] Status: reminder={reminder_id} sid={call_sid} status={status}")
    if reminder_id:
        mark_reminder_called(int(reminder_id), call_sid, status)
    return {"ok": True}


async def _save_call_record(
    call_sid, state, risk_tier, escalate, reason,
    nlp_output=None, call_status="completed", duration=0
):
    if state.get("record_saved"):
        print(f"[Twilio] Record already saved for {call_sid}, skipping duplicate save")
        return
    state["record_saved"] = True

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

        # Doctor WhatsApp alert on RED/escalated
        if escalate or risk_tier.upper() == "RED":
            send_doctor_alert(
                patient_name=state.get("patient_name", "Unknown"),
                patient_phone=state.get("patient_phone", "Unknown"),
                condition=state.get("condition", ""),
                risk_tier=risk_tier,
                transcript=full_transcript,
                escalation_reason=reason,
            )

        # Auto-create admission request if RED
        if risk_tier.upper() == "RED":
            admission = Admission(
                patient_id = state["patient_id"],
                call_sid   = call_sid,
                reason     = reason or "High risk detected during call",
                risk_tier  = risk_tier,
                status     = "pending",
            )
            db.add(admission)
            db.commit()
            print(f"[Admission] Created for patient {state['patient_id']}")

            await broadcast_update({
                "type":         "admission",
                "patient_id":   state["patient_id"],
                "patient_name": state.get("patient_name"),
                "risk_tier":    risk_tier,
                "reason":       reason,
            })

        # Auto-create appointment if patient requested one
        if nlp_output and nlp_output.get("wants_appointment"):
            appt = Appointment(
                patient_id = state["patient_id"],
                call_sid   = call_sid,
                reason     = nlp_output.get("structured_answer", {}).get(
                    "patient_concern", "Patient requested appointment"
                ),
                status     = "pending",
            )
            db.add(appt)
            db.commit()
            print(f"[Appointment] Created for patient {state['patient_id']}")

            if settings.DOCTOR_PHONE:
                _send_whatsapp(
                    to_phone=settings.DOCTOR_PHONE,
                    message=(
                        f"📅 *नई अपॉइंटमेंट रिक्वेस्ट*\n"
                        f"*Patient:* {state.get('patient_name', 'Unknown')}\n"
                        f"*Phone:* {state.get('patient_phone', 'Unknown')}\n"
                        f"*Condition:* {state.get('condition', '')}\n"
                        f"*Reason:* {appt.reason}\n"
                        f"Please confirm on the AarogyaVaani dashboard."
                    )
                )
                print(f"[Appointment] Doctor WhatsApp sent for patient {state['patient_id']}")

            await broadcast_update({
                "type":         "appointment",
                "patient_id":   state["patient_id"],
                "patient_name": state.get("patient_name"),
                "reason":       appt.reason,
            })

    except Exception as e:
        db.rollback()
        print(f"[Twilio] DB error: {e}")
    finally:
        db.close()