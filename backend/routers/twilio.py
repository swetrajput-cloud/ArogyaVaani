"""
AarogyaVaani — Human-like hospital follow-up call engine (Groq / Llama 3.3)

Features:
- Greeting uses patient's REAL data (vitals, condition, camp visit) — no risk tier mentioned
- Fully responsive — replies to everything patient says, then diverts to health
- Mid-call language switching (patient says "Hindi mein bolo" -> switches instantly)
- Appointment ask before every closing
- Unlimited turns until patient says bye
- Custom note from manual scheduler injected naturally
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

TURNS_BY_RISK = {"RED": 6, "AMBER": 5, "GREEN": 4}


# ─────────────────────────────────────────────
# LANGUAGE DETECTION (mid-call switch)
# ─────────────────────────────────────────────

LANGUAGE_SWITCH_PATTERNS = {
    "hindi": [
        "hindi mein", "hindi me", "hindi bol", "hindi main", "hindi mein bolo",
        "hindi mai bolo", "hindi mai", "हिंदी में", "हिंदी मे", "हिंदी में बोलो",
    ],
    "english": [
        "english mein", "english me", "speak english", "in english",
        "english mai", "english bol", "speak in english", "english please",
        "english mein bolo",
    ],
    "marathi": [
        "marathi mein", "marathi me", "marathi bol", "marathi madhye",
        "marathi madhe", "marathi mein bolo", "मराठी मध्ये",
    ],
    "tamil": [
        "tamil mein", "tamil la", "tamil il", "tamil bol", "தமிழில்",
    ],
    "telugu": [
        "telugu lo", "telugu mein", "telugu bol", "తెలుగులో",
    ],
    "gujarati": [
        "gujarati mein", "gujarati me", "gujarati bol", "ગુજરાતીમાં",
    ],
    "bengali": [
        "bangla mein", "bengali mein", "bangla te", "বাংলায়",
    ],
}

def _detect_language_switch(text: str):
    if not text:
        return None
    t = text.lower().strip()
    for lang, patterns in LANGUAGE_SWITCH_PATTERNS.items():
        if any(p in t for p in patterns):
            return lang
    return None


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
# Build patient context for Groq
# ─────────────────────────────────────────────

def _build_patient_context(patient: Patient) -> str:
    lines = []

    if patient.condition:
        lines.append(f"- Diagnosed condition: {patient.condition}")
    if patient.health_camp_name:
        lines.append(f"- Visited health camp: {patient.health_camp_name}")
    if patient.age:
        lines.append(f"- Age: {patient.age}")

    vitals = []
    if patient.systolic_bp and patient.diastolic_bp:
        vitals.append(f"BP {int(patient.systolic_bp)}/{int(patient.diastolic_bp)} mmHg")
    if patient.heart_rate:
        vitals.append(f"Heart rate {int(patient.heart_rate)} bpm")
    if patient.blood_glucose:
        vitals.append(f"Blood glucose {int(patient.blood_glucose)} mg/dL")
    if patient.oxygen_saturation:
        vitals.append(f"SpO2 {patient.oxygen_saturation}%")
    if patient.temperature:
        vitals.append(f"Temp {patient.temperature}°C")
    if patient.bmi:
        vitals.append(f"BMI {round(patient.bmi, 1)} ({patient.bmi_category or ''})")
    if vitals:
        lines.append(f"- Last recorded vitals: {', '.join(vitals)}")

    risk_notes = []
    if patient.heart_risk_level:
        risk_notes.append(f"Heart risk: {patient.heart_risk_level}")
    if patient.diabetic_risk_level:
        risk_notes.append(f"Diabetic risk: {patient.diabetic_risk_level}")
    if patient.hypertension_risk_level:
        risk_notes.append(f"Hypertension risk: {patient.hypertension_risk_level}")
    if risk_notes:
        lines.append(f"- Internal risk assessments (guide your questions only, NEVER mention to patient): {', '.join(risk_notes)}")

    symptoms = []
    for field, label in [
        ("chest_discomfort", "chest discomfort"),
        ("breathlessness", "breathlessness"),
        ("palpitations", "palpitations"),
        ("fatigue_weakness", "fatigue/weakness"),
        ("dizziness_blackouts", "dizziness"),
    ]:
        val = getattr(patient, field, None)
        if val and val.lower() not in ("no", "none", "normal", ""):
            symptoms.append(label)
    if symptoms:
        lines.append(f"- Previously reported symptoms: {', '.join(symptoms)}")

    lifestyle = []
    if patient.stress_anxiety and patient.stress_anxiety.lower() not in ("no", "none", "low", ""):
        lifestyle.append(f"stress/anxiety: {patient.stress_anxiety}")
    if patient.physical_inactivity and patient.physical_inactivity.lower() not in ("no", "none", ""):
        lifestyle.append(f"physical inactivity: {patient.physical_inactivity}")
    if patient.diet_quality and patient.diet_quality.lower() not in ("good", ""):
        lifestyle.append(f"diet quality: {patient.diet_quality}")
    if lifestyle:
        lines.append(f"- Lifestyle notes: {', '.join(lifestyle)}")

    if patient.family_history and patient.family_history.lower() not in ("no", "none", ""):
        lines.append(f"- Family history: {patient.family_history}")

    return "\n".join(lines) if lines else "- No detailed records available yet"


# ─────────────────────────────────────────────
# Data-aware personalized greeting
# ─────────────────────────────────────────────

def _build_greeting(patient: Patient, language: str) -> str:
    name      = patient.name
    camp      = patient.health_camp_name or ""
    condition = patient.condition or ""

    greetings = {
        "hindi": (
            f"नमस्ते {name} जी! मैं आरोग्यवाणी से आरोग्या बोल रही हूँ। "
            + (f"आप हमारे {camp} में आए थे — " if camp else "")
            + (f"आपकी {condition} की देखभाल के लिए आज कॉल की है। " if condition and condition != "General Monitoring" else "आपकी सेहत का हाल जानने के लिए कॉल की है। ")
            + "बताइए — आज आप कैसा महसूस कर रहे हैं?"
        ),
        "english": (
            f"Hello {name}! This is Aarogya calling from AarogyaVaani. "
            + (f"You visited our {camp} — " if camp else "")
            + (f"I'm calling to follow up on your {condition}. " if condition and condition != "General Monitoring" else "I'm calling to check on your health today. ")
            + "How are you feeling?"
        ),
        "marathi": (
            f"नमस्कार {name} जी! मी आरोग्यवाणीमधून आरोग्या बोलतेय। "
            + (f"तुम्ही आमच्या {camp} ला आला होतात — " if camp else "")
            + "आज तुम्ही कसे आहात?"
        ),
        "tamil": (
            f"வணக்கம் {name}! நான் ஆரோக்யவாணியிலிருந்து ஆரோக்யா பேசுகிறேன். "
            + "இன்று நீங்கள் எப்படி இருக்கிறீர்கள்?"
        ),
        "telugu": (
            f"నమస్కారం {name} గారు! నేను ఆరోగ్యవాణి నుండి మాట్లాడుతున్నాను. "
            + "మీరు ఈరోజు ఎలా ఉన్నారు?"
        ),
        "gujarati": (
            f"નમસ્તે {name} જી! હું આરોગ્યવાણીથી બોલી રહી છું. "
            + "આજે તમે કેવા અનુભવો છો?"
        ),
        "bengali": (
            f"নমস্কার {name} জি! আমি আরোগ্যবাণী থেকে বলছি। "
            + "আজ আপনি কেমন অনুভব করছেন?"
        ),
    }
    return greetings.get(language, greetings["hindi"])


# ─────────────────────────────────────────────
# Language switch acknowledgement
# ─────────────────────────────────────────────

def _language_switch_ack(new_language: str, patient_name: str) -> str:
    acks = {
        "hindi":    f"बिल्कुल {patient_name} जी, अब हम हिंदी में बात करते हैं। तो बताइए, आप कैसा महसूस कर रहे हैं?",
        "english":  f"Of course {patient_name}, let's switch to English. So tell me, how are you feeling?",
        "marathi":  f"नक्की {patient_name} जी, आता मराठीत बोलूया. सांगा, तुम्ही कसे आहात?",
        "tamil":    f"சரி {patient_name}, இப்போது தமிழில் பேசலாம். சொல்லுங்கள், நீங்கள் எப்படி இருக்கிறீர்கள்?",
        "telugu":   f"సరే {patient_name}, ఇప్పుడు తెలుగులో మాట్లాడుకుందాం. మీరు ఎలా ఉన్నారు?",
        "gujarati": f"જરૂર {patient_name} જી, હવે ગુજરાતીમાં વાત કરીએ. કહો, તમે કેવા છો?",
        "bengali":  f"অবশ্যই {patient_name} জি, এখন বাংলায় কথা বলি। বলুন, আপনি কেমন আছেন?",
    }
    return acks.get(new_language, acks["hindi"])


# ─────────────────────────────────────────────
# Groq AI — main brain
# ─────────────────────────────────────────────

async def _groq_respond(
    patient_name: str,
    condition: str,
    patient_context: str,
    language: str,
    history: list[dict],
    patient_said: str,
    health_questions_done: bool,
    closing: bool,
    appointment_asked: bool,
    custom_note: str = None,
) -> str:

    lang_instruction = {
        "hindi":    "Respond ONLY in Hindi (Devanagari script). Warm conversational Hindi like a caring hospital nurse who is also a friend.",
        "english":  "Respond in simple conversational Indian English. Warm, friendly, and clear.",
        "marathi":  "Respond ONLY in Marathi (Devanagari). Warm and conversational.",
        "tamil":    "Respond ONLY in Tamil script. Simple and warm.",
        "telugu":   "Respond ONLY in Telugu script. Simple and warm.",
        "gujarati": "Respond ONLY in Gujarati script. Simple and warm.",
        "bengali":  "Respond ONLY in Bengali script. Simple and warm.",
    }.get(language, "Respond ONLY in Hindi.")

    custom_note_instruction = ""
    if custom_note and not closing:
        custom_note_instruction = f"""
SPECIAL INSTRUCTION: At a natural point in the conversation, mention this to the patient warmly and casually — like a caring friend, NOT an announcement:
\"{custom_note}\"
Mention it ONCE only. Weave it in naturally.
"""

    if closing:
        appt_line = ""
        if not appointment_asked:
            appt_line = """
IMPORTANT: Before saying goodbye, you MUST ask the patient warmly if they would like to book an appointment with the doctor.
Example: 'Would you like me to arrange a doctor's appointment for you?' 
Only after they answer (yes or no), say goodbye.
"""
        mode_instruction = f"""
The patient is ending the call OR the health check is complete.
{appt_line}
Rules:
- FIRST reply warmly to exactly what the patient just said
- If they said YES to appointment — confirm it warmly, say the hospital will contact them soon
- If they said NO to appointment — that's fine, wish them well
- Give a warm, human goodbye
- Tell them their health records are safely updated with the hospital
- Say Aarogya is always here if they need anything
- Do NOT ask more health questions
"""
    elif health_questions_done:
        mode_instruction = """
All health questions are done. Now chat naturally like a warm caring friend.
Rules:
- ALWAYS respond to what the patient said first — show real interest and warmth
- Ask casual friendly follow-up questions about their day, family, or whatever they brought up
- If the patient raises any health concern — address it warmly and follow up
- Keep it light and human
- Do NOT hang up — keep going until they say bye
"""
    else:
        mode_instruction = """
You are conducting a hospital follow-up health check call.
Rules:
- ALWAYS respond to what the patient said FIRST — empathy and warmth before anything else
- If they share something personal (family, feelings, problems) — engage genuinely, then naturally steer back to health
- Ask ONE focused health question per turn
- Use the patient's data (vitals, condition, symptoms, camp visit) to ask SPECIFIC relevant questions:
  * If they have diabetes data → ask about sugar levels, diet, medication adherence
  * If they have BP data → ask about headaches, dizziness, salt intake
  * If they visited a camp → ask how they felt after the camp, any changes since
  * If symptoms were reported → ask if those symptoms have improved or are still there
- Sound like a hospital nurse who genuinely KNOWS this patient — not a generic script
- Do NOT end the call yet
- NEVER mention risk tier, risk score, or RED/AMBER/GREEN to the patient
"""

    system = f"""You are Aarogya — a warm, caring hospital health assistant calling patients for AarogyaVaani, a rural India hospital follow-up service.

PATIENT INFORMATION (use this to personalize every response):
- Name: {patient_name}
- Condition: {condition}
{patient_context}

YOUR PERSONA:
- You are like a hospital nurse who genuinely knows and cares about this patient
- You have their medical records — reference them naturally so the patient feels seen and cared for
- Sound human, warm, and personal — NOT robotic or scripted
- React to EVERYTHING the patient says — then guide conversation back to health naturally
- Use the patient's name occasionally — it makes it personal
- If patient mentions pain, worry, or distress — show REAL concern first, then ask more
- Keep responses to 2-3 SHORT sentences MAX — this is a phone call
- Never use bullet points, lists, or medical jargon
- Never say you are an AI — you are Aarogya, their hospital health friend
- NEVER mention risk tier (RED/AMBER/GREEN) or risk scores to the patient ever

LANGUAGE:
{lang_instruction}
If the patient asks to switch language mid-call — you have already switched, continue in the new language.

{custom_note_instruction}

{mode_instruction}

Output ONLY the spoken words. No stage directions. No labels. No extra formatting."""

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
                    "max_tokens": 220,
                    "temperature": 0.75,
                    "messages": [{"role": "system", "content": system}] + messages,
                },
            )
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            mode = "CLOSING" if closing else ("CHAT" if health_questions_done else "HEALTH")
            print(f"[Groq] [{mode}] [{language.upper()}] Turn {len(history)//2 + 1}: {text[:80]}...")
            return text

    except Exception as e:
        print(f"[Groq] Error: {e}")
        fallbacks = {
            "hindi":   f"{patient_name} जी, क्षमा करें। आप कैसा महसूस कर रहे हैं?",
            "english": f"Sorry {patient_name}, could you say that again?",
            "marathi": f"{patient_name} जी, माफ करा. तुम्ही कसे आहात?",
        }
        return fallbacks.get(language, fallbacks["hindi"])


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
        "hindi":    "क्या आप वहाँ हैं? कृपया बोलें।",
        "english":  "Are you there? Please go ahead.",
        "marathi":  "तुम्ही तिथे आहात का? कृपया बोला.",
        "tamil":    "நீங்கள் இங்கே இருக்கிறீர்களா?",
        "telugu":   "మీరు అక్కడ ఉన్నారా?",
        "gujarati": "શું તમે ત્યાં છો?",
        "bengali":  "আপনি কি সেখানে আছেন?",
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
    call_sid      = CallSid or request.query_params.get("CallSid", "")
    custom_note   = request.query_params.get("custom_note", None)
    patient_phone = To
    print(f"[Twilio] Call answered: {call_sid} To:{patient_phone} Note:{custom_note}")

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

        language     = (patient.language or "hindi").lower()
        health_turns = TURNS_BY_RISK.get(patient.current_risk_tier or "GREEN", 4)
        patient_ctx  = _build_patient_context(patient)

        _call_states[call_sid] = {
            "patient_id":         patient.id,
            "patient_name":       patient.name,
            "condition":          patient.condition or "",
            "patient_context":    patient_ctx,
            "risk_tier":          patient.current_risk_tier or "GREEN",
            "language":           language,
            "health_turns":       health_turns,
            "turn_number":        0,
            "history":            [],
            "transcript_parts":   [],
            "overall_risk_score": patient.overall_risk_score or 0,
            "patient_phone":      patient.phone or "",
            "module_type":        patient.module_type or "post_discharge",
            "record_saved":       False,
            "health_done":        False,
            "closing_sent":       False,
            "appointment_asked":  False,
            "custom_note":        custom_note,
        }
    finally:
        db.close()

    state    = _call_states[call_sid]
    greeting = _build_greeting(patient, language)
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
    state    = _call_states.get(call_sid)

    if not state:
        resp = VoiceResponse()
        resp.say("सत्र समाप्त हो गया। धन्यवाद।", language="hi-IN", voice="Polly.Aditi")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    language          = state["language"]
    patient_said      = SpeechResult.strip()
    turn_number       = state["turn_number"]
    health_turns      = state["health_turns"]
    health_done       = state["health_done"]
    appointment_asked = state["appointment_asked"]

    print(f"[Twilio] Turn {turn_number + 1} | Lang:{language} | Health done:{health_done} | Said: '{patient_said}'")

    # ── Mid-call language switch ──
    new_lang = _detect_language_switch(patient_said)
    if new_lang and new_lang != language:
        print(f"[Twilio] Language switch: {language} → {new_lang}")
        state["language"] = new_lang
        language = new_lang
        ack_text = _language_switch_ack(new_lang, state["patient_name"])
        if patient_said:
            state["transcript_parts"].append(patient_said)
        state["history"].append({"role": "user",      "content": patient_said})
        state["history"].append({"role": "assistant", "content": ack_text})
        state["turn_number"] += 1
        action_url = f"{BASE_URL}/twilio/conversation?call_sid={call_sid}"
        twiml = _make_gather(ack_text, action_url, language)
        return Response(content=twiml, media_type="application/xml")

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

    # Mark health questions done after health_turns
    if not health_done and turn_number >= health_turns:
        state["health_done"] = True
        health_done = True

    # Detect patient wanting to end
    patient_ending = _patient_wants_to_end(patient_said)

    # Closing condition
    chat_turns_after_health = turn_number - health_turns
    closing = patient_ending or (health_done and chat_turns_after_health >= 1)

    # Track that appointment question was asked once we enter closing
    if closing and not appointment_asked:
        state["appointment_asked"] = True

    # Generate Groq response
    ai_response = await _groq_respond(
        patient_name          = state["patient_name"],
        condition             = state["condition"],
        patient_context       = state["patient_context"],
        language              = language,
        history               = state["history"],
        patient_said          = patient_said,
        health_questions_done = health_done,
        closing               = closing,
        appointment_asked     = appointment_asked,
        custom_note           = state.get("custom_note"),
    )

    # Update history
    if patient_said:
        state["history"].append({"role": "user",      "content": patient_said})
    state["history"].append(    {"role": "assistant", "content": ai_response})
    state["turn_number"] += 1

    # ── Closing — save record and hang up ──
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

        # Auto-detect appointment request from transcript
        appt_keywords = [
            "appointment", "अपॉइंटमेंट", "हाँ", "yes", "doctor se milna",
            "milna hai", "dikhana hai", "मिलना है", "दिखाना है", "हाँ बुक करो", "हां",
        ]
        if any(kw in full_transcript.lower() for kw in appt_keywords):
            if nlp_output is not None:
                nlp_output["wants_appointment"] = True

        await _save_call_record(call_sid, state, risk_tier, escalate, reason, nlp_output)
        twiml = _make_say_and_hangup(ai_response, language)
        return Response(content=twiml, media_type="application/xml")

    # Continue conversation
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
        print(f"[Twilio] Saved. Patient:{state['patient_id']} Risk:{risk_tier} Turns:{state['turn_number']} Lang:{state['language']}")

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
                    "patient_concern", "Patient requested appointment during follow-up call"
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
                        f"*Condition:* {state.get('condition')}\n"
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

Only file to replace: `backend/routers/twilio.py`

git add .
git commit -m "Data-aware greeting, mid-call language switch, appointment ask at close"
git push