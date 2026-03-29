"""
Human-like conversational call engine powered by Groq (Llama 3).
- NO press 1/3 language menu
- NO press # to finish
- Unlimited turns until patient says bye
- AI always replies to last thing patient said before closing
- After health questions done — chats naturally like a friend
"""

import httpx
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
import asyncio

router = APIRouter(prefix="/twilio", tags=["twilio"])
BASE_URL = os.getenv("BASE_URL", "https://arogyavaani-production.up.railway.app")

_call_states: dict[str, dict] = {}

TURNS_BY_RISK = {"RED": 5, "AMBER": 4, "GREEN": 3}


# ─────────────────────────────────────────────
# BYE DETECTION
# ─────────────────────────────────────────────

BYE_KEYWORDS = [
    "अलविदा", "बाय", "ठीक है धन्यवाद", "धन्यवाद", "शुक्रिया", "बस इतना ही",
    "फिर मिलेंगे", "अब रखता हूं", "अब रखती हूं", "रखता हूं", "रखती हूं",
    "काम है", "जाना है", "ठीक है बस", "बस",
    "bye", "goodbye", "thank you", "thanks", "that's all", "ok thanks",
    "i have to go", "talk later", "see you",
    "निघतो", "निघते", "बरं",
]

def _patient_wants_to_end(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    return any(kw in t for kw in BYE_KEYWORDS)


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
# Groq AI
# ─────────────────────────────────────────────

async def _groq_respond(
    patient_name: str,
    condition: str,
    risk_tier: str,
    language: str,
    history: list[dict],
    patient_said: str,
    health_questions_done: bool,
    closing: bool,
) -> str:

    lang_instruction = {
        "hindi":    "Respond ONLY in Hindi (Devanagari script). Warm conversational Hindi like a caring friend who is also a nurse.",
        "english":  "Respond in simple conversational Indian English. Warm and friendly.",
        "marathi":  "Respond ONLY in Marathi (Devanagari). Warm and conversational.",
        "tamil":    "Respond ONLY in Tamil script. Simple and warm.",
        "telugu":   "Respond ONLY in Telugu script. Simple and warm.",
        "gujarati": "Respond ONLY in Gujarati script. Simple and warm.",
        "bengali":  "Respond ONLY in Bengali script. Simple and warm.",
    }.get(language, "Respond ONLY in Hindi.")

    if closing:
        mode_instruction = """
The patient wants to end the call OR all health questions are done and you just acknowledged their last reply.
Rules:
- FIRST reply warmly to exactly what the patient just said — never ignore it
- Then give a natural warm goodbye
- Tell them their health info is safely recorded
- Reassure them Aarogya is always here if they need anything
- End like a caring friend saying goodbye, not a robot
- Do NOT ask any more questions
"""
    elif health_questions_done:
        mode_instruction = """
You have finished all the health check questions. Now just chat naturally like a warm caring friend.
Rules:
- ALWAYS first respond to exactly what the patient said — react, show interest, show warmth
- Ask casual friendly questions about their day, family, mood, or anything they brought up
- Keep it light, human, and warm
- Do NOT ask health questions anymore
- Do NOT hang up — keep the conversation going until they say bye
"""
    else:
        mode_instruction = """
You are doing a health check call.
Rules:
- ALWAYS first acknowledge and react to what the patient just said — empathy before anything
- Then naturally ask your next health question
- Ask only ONE question per turn
- Sound warm and human, not clinical or scripted
- Do NOT end the call yet
"""

    system = f"""You are Aarogya — a warm caring health assistant calling patients for AarogyaVaani, a rural India health service.

Patient:
- Name: {patient_name}
- Condition: {condition}
- Risk level: {risk_tier}

YOUR STYLE:
- Sound like a kind friend who is also a nurse — NOT a robot or IVR
- Use the patient's name once in a while — makes it personal
- React to what the patient says FIRST, always
- If they mention pain, worry, or distress — show real concern before moving on
- Keep responses to 2-3 short sentences MAX — this is a phone call
- Never use bullet points, lists, or medical jargon
- Never say you are an AI — you are Aarogya, their health friend
- Be warm, curious, and human

{lang_instruction}

{mode_instruction}

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
                    "max_tokens": 200,
                    "temperature": 0.75,
                    "messages": [{"role": "system", "content": system}] + messages,
                },
            )
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            mode = "CLOSING" if closing else ("CHAT" if health_questions_done else "HEALTH")
            print(f"[Groq] [{mode}] Turn {len(history)//2 + 1}: {text[:80]}...")
            return text

    except Exception as e:
        print(f"[Groq] Error: {e}")
        fallbacks = {
            "hindi":   f"{patient_name} जी, क्षमा करें। आप कैसा महसूस कर रहे हैं?",
            "english": f"Sorry {patient_name}, could you repeat that?",
        }
        return fallbacks.get(language, fallbacks["hindi"])


# ─────────────────────────────────────────────
# Greeting
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
# TwiML helpers
# ─────────────────────────────────────────────

def _make_gather(text: str, action_url: str, language: str) -> str:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        language=_gather_lang(language),
        speech_timeout="auto",
        timeout=8,
        enhanced=True,
    )
    gather.say(text, language=_say_lang(language), voice=_voice(language))
    response.append(gather)

    nudge = {
        "hindi":   "क्या आप वहाँ हैं? कृपया बोलें।",
        "english": "Are you there? Please go ahead.",
        "marathi": "तुम्ही तिथे आहात का? कृपया बोला.",
        "tamil":   "நீங்கள் இங்கே இருக்கிறீர்களா?",
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
        health_turns = TURNS_BY_RISK.get(patient.current_risk_tier or "GREEN", 3)

        _call_states[call_sid] = {
            "patient_id":           patient.id,
            "patient_name":         patient.name,
            "condition":            patient.condition or "",
            "risk_tier":            patient.current_risk_tier or "GREEN",
            "language":             language,
            "health_turns":         health_turns,   # how many turns for health questions
            "turn_number":          0,              # total turns so far
            "history":              [],             # full Groq conversation history
            "transcript_parts":     [],
            "overall_risk_score":   patient.overall_risk_score or 0,
            "patient_phone":        patient.phone or "",
            "module_type":          patient.module_type or "post_discharge",
            "record_saved":         False,
            "health_done":          False,          # health questions completed flag
            "closing_sent":         False,          # goodbye already sent flag
        }
    finally:
        db.close()

    state = _call_states[call_sid]
    greeting = _build_greeting(state["patient_name"], language)
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

    language      = state["language"]
    patient_said  = SpeechResult.strip()
    turn_number   = state["turn_number"]
    health_turns  = state["health_turns"]
    health_done   = state["health_done"]

    print(f"[Twilio] Turn {turn_number + 1} | Health done: {health_done} | Patient said: '{patient_said}'")

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

    # Mark health questions as done after health_turns
    if not health_done and turn_number >= health_turns:
        state["health_done"] = True
        health_done = True

    # Patient wants to end — reply to last thing then close
    patient_ending = _patient_wants_to_end(patient_said)

    # Closing condition:
    # 1. Patient said bye, OR
    # 2. Health done AND we already had at least 1 chat turn after health
    chat_turns_after_health = turn_number - health_turns
    closing = patient_ending or (health_done and chat_turns_after_health >= 1)

    # Generate Groq response
    ai_response = await _groq_respond(
        patient_name         = state["patient_name"],
        condition            = state["condition"],
        risk_tier            = state["risk_tier"],
        language             = language,
        history              = state["history"],
        patient_said         = patient_said,
        health_questions_done= health_done,
        closing              = closing,
    )

    # Update history
    if patient_said:
        state["history"].append({"role": "user",      "content": patient_said})
    state["history"].append(    {"role": "assistant", "content": ai_response})
    state["turn_number"] += 1

    # If closing — save record and hang up after speaking
    if closing:
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

    # Continue conversation — speak and listen again
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

    state = _call_states.get(call_sid)
    if state and not state.get("record_saved") and CallStatus in ("no-answer", "busy", "failed", "completed"):
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
# Save call record
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
        print(f"[Twilio] Saved. Patient:{state['patient_id']} Risk:{risk_tier} Turns:{state['turn_number']}")

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