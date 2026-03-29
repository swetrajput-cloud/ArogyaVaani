"""
Human-like conversational call engine powered by Groq (Llama 3).
- NO press 1/3 language menu
- NO press # to finish
- NO beep-record-download cycle
- Patient speaks naturally → Twilio STT → Groq → warm nurse voice
"""

import httpx
import asyncio
import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from config import settings
from models.database import SessionLocal
from models.patient import Patient
from models.call_record import CallRecord
from models.appointment import Appointment
from models.admission import Admission
from nlp.intent_extractor import extract_intent
from nlp.risk_scorer import compute_risk
from dashboard.ws_broadcaster import broadcast_update
from models_ai.call_brain import is_urgent, get_urgent_alert
from alerts.doctor_sms import send_doctor_alert, _send_whatsapp
from datetime import datetime

router = APIRouter(prefix="/twilio", tags=["twilio"])
BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")

_call_states: dict[str, dict] = {}

TURNS_BY_RISK = {"RED": 4, "AMBER": 3, "GREEN": 2}


# ─────────────────────────────────────────────
# Language helpers
# ─────────────────────────────────────────────

def _gather_lang(language: str) -> str:
    return {
        "hindi":    "hi-IN",
        "marathi":  "mr-IN",
        "bengali":  "bn-IN",
        "tamil":    "ta-IN",
        "telugu":   "te-IN",
        "gujarati": "gu-IN",
        "english":  "en-IN",
    }.get(language.lower(), "hi-IN")

def _say_lang(language: str) -> str:
    return "en-IN" if language == "english" else "hi-IN"

def _voice(language: str) -> str:
    return "Polly.Raveena" if language == "english" else "Polly.Aditi"


# ─────────────────────────────────────────────
# Groq AI — warm nurse response
# ─────────────────────────────────────────────

async def _groq_respond(
    patient_name: str,
    condition: str,
    risk_tier: str,
    language: str,
    history: list[dict],
    patient_said: str,
    turn_number: int,
    total_turns: int,
) -> str:
    lang_instruction = {
        "hindi":    "Respond ONLY in Hindi (Devanagari script). Simple warm conversational Hindi like a nurse from a government health centre.",
        "english":  "Respond in simple conversational Indian English.",
        "marathi":  "Respond ONLY in Marathi (Devanagari). Warm and conversational.",
        "tamil":    "Respond ONLY in Tamil script. Simple and warm.",
        "telugu":   "Respond ONLY in Telugu script. Simple and warm.",
        "gujarati": "Respond ONLY in Gujarati script. Simple and warm.",
        "bengali":  "Respond ONLY in Bengali script. Simple and warm.",
    }.get(language, "Respond ONLY in Hindi.")

    is_last = (turn_number >= total_turns - 1)
    closing_note = (
        "\n\nThis is the LAST turn. After responding to what the patient said, "
        "give a warm goodbye: tell them their information is safely recorded, "
        "reassure them, and end warmly. Do NOT ask any more questions."
    ) if is_last else ""

    system = f"""You are Aarogya — a warm caring health assistant nurse calling patients on behalf of AarogyaVaani, an AI health service for rural India.

Patient you are calling:
- Name: {patient_name}
- Condition: {condition}
- Risk level: {risk_tier}

YOUR STYLE:
- Sound like a kind nurse, NOT a robot or IVR system
- Use the patient's name once or twice to feel personal
- Always acknowledge what the patient said FIRST (show empathy), then ask your question
- If they mention pain or distress — show genuine concern before anything else
- Keep responses to 2-3 short sentences MAX — this is a phone call
- Ask only ONE question per turn
- Never use bullet points, lists, or clinical jargon
- Never say you are an AI — you are Aarogya, their health friend

{lang_instruction}

YOUR GOAL across {total_turns} turns:
Gently learn about: current symptoms, any pain or discomfort, medication adherence, and overall wellbeing.
You are on turn {turn_number + 1} of {total_turns}.
{closing_note}

Output ONLY the spoken words. No stage directions. No labels. No formatting."""

    messages = list(history)
    messages.append({
        "role": "user",
        "content": patient_said if patient_said.strip() else "[Patient was silent or unclear]"
    })

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "max_tokens": 180,
                    "temperature": 0.7,
                    "messages": [{"role": "system", "content": system}] + messages,
                },
            )
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            print(f"[Groq] Turn {turn_number + 1}: {text[:80]}...")
            return text

    except Exception as e:
        print(f"[Groq] Error: {e}")
        fallbacks = {
            "hindi":   f"{patient_name} जी, क्षमा करें। आज आप कैसा महसूस कर रहे हैं?",
            "english": f"{patient_name}, sorry for the delay. How are you feeling today?",
        }
        return fallbacks.get(language, fallbacks["hindi"])


# ─────────────────────────────────────────────
# Greeting (first thing patient hears)
# ─────────────────────────────────────────────

def _build_greeting(patient_name: str, language: str) -> str:
    greetings = {
        "hindi":   (f"नमस्ते {patient_name} जी! मैं आरोग्यवाणी से आरोग्या बोल रही हूँ। "
                    f"आपकी सेहत का हाल जानने के लिए कॉल की है। "
                    f"बताइए — आज आप कैसा महसूस कर रहे हैं?"),
        "english": (f"Hello {patient_name}! This is Aarogya calling from AarogyaVaani. "
                    f"I'm calling to check on your health today. How are you feeling?"),
        "marathi": (f"नमस्कार {patient_name} जी! मी आरोग्यवाणीमधून आरोग्या बोलतेय। "
                    f"आज तुम्ही कसे आहात?"),
        "tamil":   (f"வணக்கம் {patient_name}! நான் ஆரோக்யவாணியிலிருந்து ஆரோக்யா பேசுகிறேன். "
                    f"இன்று நீங்கள் எப்படி இருக்கிறீர்கள்?"),
    }
    return greetings.get(language, greetings["hindi"])


# ─────────────────────────────────────────────
# TwiML builder — speak + listen (no # needed)
# ─────────────────────────────────────────────

def _make_gather(text: str, action_url: str, language: str) -> str:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        language=_gather_lang(language),
        speech_timeout="auto",   # silence detection — no # needed
        timeout=6,
        enhanced=True,           # Twilio enhanced speech model
    )
    gather.say(text, language=_say_lang(language), voice=_voice(language))
    response.append(gather)

    # Patient didn't speak — nudge once then hang up
    nudge = {
        "hindi":   "क्या आप वहाँ हैं? कृपया बोलें।",
        "english": "Are you there? Please speak.",
        "marathi": "तुम्ही तिथे आहात का? कृपया बोला.",
        "tamil":   "நீங்கள் இங்கே இருக்கிறீர்களா? தயவுசெய்து பேசுங்கள்.",
    }.get(language, "क्या आप वहाँ हैं?")
    response.say(nudge, language=_say_lang(language), voice=_voice(language))
    response.hangup()
    return str(response)


def _make_say_and_hangup(text: str, language: str) -> str:
    response = VoiceResponse()
    response.say(text, language=_say_lang(language), voice=_voice(language))
    response.hangup()
    return str(response)


# ─────────────────────────────────────────────
# WEBHOOK 1: Call answered
# ─────────────────────────────────────────────

@router.post("/answered")
async def call_answered(
    request: Request,
    CallSid: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
):
    call_sid = CallSid or request.query_params.get("CallSid", "")
    patient_phone = To
    print(f"[Twilio] Call answered: {call_sid} To:{patient_phone}")

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.phone == patient_phone).first()
        if not patient:
            clean = patient_phone.lstrip("+").lstrip("91")
            patient = db.query(Patient).filter(
                Patient.phone.contains(clean[-10:])
            ).first()

        if not patient:
            resp = VoiceResponse()
            resp.say("क्षमा करें, आपका रिकॉर्ड नहीं मिला। धन्यवाद।", language="hi-IN", voice="Polly.Aditi")
            resp.hangup()
            return Response(content=str(resp), media_type="application/xml")

        language = (patient.language or "hindi").lower()
        total_turns = TURNS_BY_RISK.get(patient.current_risk_tier or "GREEN", 2)

        _call_states[call_sid] = {
            "patient_id":         patient.id,
            "patient_name":       patient.name,
            "condition":          patient.condition or "",
            "risk_tier":          patient.current_risk_tier or "GREEN",
            "language":           language,
            "total_turns":        total_turns,
            "turn_number":        0,
            "history":            [],        # Groq conversation history
            "transcript_parts":   [],
            "overall_risk_score": patient.overall_risk_score or 0,
            "patient_phone":      patient.phone or "",
            "module_type":        patient.module_type or "post_discharge",
            "record_saved":       False,
        }
    finally:
        db.close()

    state = _call_states[call_sid]
    greeting = _build_greeting(state["patient_name"], language)

    # Add greeting to history so Groq has context
    state["history"].append({"role": "assistant", "content": greeting})

    action_url = f"{BASE_URL}/twilio/conversation?call_sid={call_sid}"
    twiml = _make_gather(greeting, action_url, language)
    return Response(content=twiml, media_type="application/xml")


# ─────────────────────────────────────────────
# WEBHOOK 2: Patient spoke — generate response
# ─────────────────────────────────────────────

@router.post("/conversation")
async def conversation_turn(
    request: Request,
    CallSid: str = Form(default=""),
    SpeechResult: str = Form(default=""),
    Confidence: str = Form(default="0"),
):
    call_sid = CallSid or request.query_params.get("call_sid", "")
    state = _call_states.get(call_sid)

    if not state:
        resp = VoiceResponse()
        resp.say("सत्र समाप्त हो गया। धन्यवाद।", language="hi-IN", voice="Polly.Aditi")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    language     = state["language"]
    turn_number  = state["turn_number"]
    total_turns  = state["total_turns"]
    patient_said = SpeechResult.strip()

    print(f"[Twilio] Turn {turn_number + 1}/{total_turns} | Patient said: '{patient_said}'")

    # Save transcript
    if patient_said:
        state["transcript_parts"].append(patient_said)

    # Urgent keyword check
    if patient_said and is_urgent(patient_said, language):
        urgent_msg = get_urgent_alert(language)
        await _save_call_record(call_sid, state, "RED", True, "Urgent keyword detected", {})
        twiml = _make_say_and_hangup(urgent_msg, language)
        return Response(content=twiml, media_type="application/xml")

    # Broadcast live transcript to dashboard
    if patient_said:
        await broadcast_update({
            "call_sid":     call_sid,
            "patient_id":   state["patient_id"],
            "patient_name": state["patient_name"],
            "risk_tier":    state["risk_tier"],
            "escalate":     False,
            "transcript":   patient_said,
            "nlp":          {},
        })

    # Groq generates warm nurse response
    ai_response = await _groq_respond(
        patient_name  = state["patient_name"],
        condition     = state["condition"],
        risk_tier     = state["risk_tier"],
        language      = language,
        history       = state["history"],
        patient_said  = patient_said,
        turn_number   = turn_number,
        total_turns   = total_turns,
    )

    # Update conversation history
    if patient_said:
        state["history"].append({"role": "user",      "content": patient_said})
    state["history"].append(    {"role": "assistant", "content": ai_response})
    state["turn_number"] += 1

    # Last turn — save record and hang up
    if state["turn_number"] >= total_turns:
        full_transcript = " | ".join(state["transcript_parts"])
        nlp_output = {}
        risk_tier  = state["risk_tier"]
        escalate   = False
        reason     = ""

        if full_transcript:
            try:
                nlp_output = await extract_intent(full_transcript, language)
            except Exception as e:
                print(f"[NLP] Error: {e}")
            risk_tier, escalate, reason, _ = compute_risk(
                full_transcript, nlp_output, state["overall_risk_score"]
            )

        await _save_call_record(call_sid, state, risk_tier, escalate, reason, nlp_output)
        twiml = _make_say_and_hangup(ai_response, language)
        return Response(content=twiml, media_type="application/xml")

    # More turns — speak response and listen again
    action_url = f"{BASE_URL}/twilio/conversation?call_sid={call_sid}"
    twiml = _make_gather(ai_response, action_url, language)
    return Response(content=twiml, media_type="application/xml")


# ─────────────────────────────────────────────
# WEBHOOK 3: Call status (cleanup)
# ─────────────────────────────────────────────

@router.post("/status")
async def call_status(
    request: Request,
    CallSid: str = Form(default=""),
    CallStatus: str = Form(default=""),
    CallDuration: str = Form(default="0"),
):
    call_sid = CallSid or request.query_params.get("CallSid", "")
    print(f"[Twilio] Status: {call_sid} → {CallStatus} ({CallDuration}s)")

    # If call ended early (no-answer, busy, failed) — save partial record
    state = _call_states.get(call_sid)
    if state and not state.get("record_saved") and CallStatus in ("no-answer", "busy", "failed"):
        await _save_call_record(call_sid, state, state["risk_tier"], False, "", {}, CallStatus)

    _call_states.pop(call_sid, None)
    return {"status": "ok"}


# ─────────────────────────────────────────────
# Vaccination reminder TwiML (unchanged)
# ─────────────────────────────────────────────

@router.post("/vaccination-reminder-twiml")
async def vaccination_reminder_twiml(request: Request):
    vaccine = request.query_params.get("vaccine", "टीका")
    due     = request.query_params.get("due", "अगले सप्ताह")

    response = VoiceResponse()
    response.say(
        f"नमस्ते! आरोग्यवाणी से एक महत्वपूर्ण सूचना। "
        f"आपके बच्चे का {vaccine} का टीका {due} को लगवाना है। "
        f"कृपया अपने नजदीकी स्वास्थ्य केंद्र में जाएं। धन्यवाद।",
        language="hi-IN", voice="Polly.Aditi",
    )
    response.hangup()
    return Response(content=str(response), media_type="application/xml")


@router.post("/vaccination-status")
async def vaccination_call_status(request: Request):
    from modules.vaccination_reminder_engine import mark_reminder_called
    reminder_id = request.query_params.get("reminder_id")
    form        = await request.form()
    status      = form.get("CallStatus", "")
    call_sid    = form.get("CallSid", "")
    if reminder_id:
        mark_reminder_called(int(reminder_id), call_sid, status)
    return {"ok": True}


# ─────────────────────────────────────────────
# Save call record (unchanged logic)
# ─────────────────────────────────────────────

async def _save_call_record(
    call_sid, state, risk_tier, escalate, reason,
    nlp_output=None, call_status="completed", duration=0
):
    if state.get("record_saved"):
        return
    state["record_saved"] = True

    full_transcript = " | ".join(state.get("transcript_parts", []))
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == state["patient_id"]).first()
        if patient:
            patient.current_risk_tier = risk_tier
            patient.last_called_at    = datetime.utcnow()
            patient.updated_at        = datetime.utcnow()

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

        if escalate or risk_tier.upper() == "RED":
            send_doctor_alert(
                patient_name      = state.get("patient_name", "Unknown"),
                patient_phone     = state.get("patient_phone", "Unknown"),
                condition         = state.get("condition", ""),
                risk_tier         = risk_tier,
                transcript        = full_transcript,
                escalation_reason = reason,
            )

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
            await broadcast_update({
                "type":         "admission",
                "patient_id":   state["patient_id"],
                "patient_name": state.get("patient_name"),
                "risk_tier":    risk_tier,
                "reason":       reason,
            })

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

            if settings.DOCTOR_PHONE:
                _send_whatsapp(
                    to_phone = settings.DOCTOR_PHONE,
                    message  = (
                        f"📅 *नई अपॉइंटमेंट रिक्वेस्ट*\n"
                        f"*Patient:* {state.get('patient_name')}\n"
                        f"*Phone:* {state.get('patient_phone')}\n"
                        f"*Reason:* {appt.reason}"
                    )
                )

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