from groq import Groq
import json
import re
from config import settings

client = Groq(api_key=settings.GROQ_API_KEY.strip())

SYSTEM_PROMPT = """You are a clinical NLP engine for AarogyaVaani, an Indian healthcare platform.
Extract structured information from patient speech transcripts in Hindi, English, or mixed language.
Always respond with ONLY valid JSON in this exact format:
{
  "topic": "string (one of: chest_pain, breathlessness, fever, back_pain, headache, dizziness, weakness, diabetes, hypertension, vomiting, diarrhea, swelling, heart_attack, stroke, unconscious, bleeding, medication, sleep, diet, appointment, general, unknown)",
  "sentiment": "positive|neutral|negative|distressed",
  "severity": 1,
  "keywords": ["list", "of", "clinical", "keywords"],
  "wants_appointment": false,
  "structured_answer": {
    "pain_level": "none|mild|moderate|severe",
    "symptoms": ["list of symptoms mentioned"],
    "medication_taken": true,
    "needs_followup": true,
    "patient_concern": "brief summary of main concern in English"
  }
}

Severity scoring rules (1-5):
- 1: No symptoms, doing well
- 2: Mild symptoms (slight pain, minor discomfort)
- 3: Moderate symptoms (pain affecting daily life, high BP, high sugar)
- 4: Severe symptoms (very high BP, very high sugar, severe pain, breathlessness)
- 5: Critical/Emergency (chest pain, heart attack, stroke, can't breathe, unconscious)

Topic must be the single most relevant topic from the allowed list.
wants_appointment = true if patient mentions: बुक, appointment, अपॉइंटमेंट, मिलना, दिखाना, doctor se milna, schedule.
No explanation, no markdown, only JSON."""

APPOINTMENT_KEYWORDS = [
    "अपॉइंटमेंट", "appointment", "बुक", "book", "डॉक्टर से मिलना",
    "मिलना है", "बुलाओ", "दिखाना", "दिखाओ", "दिखा दो", "बुक कर",
    "अपॉइन्टमेंट", "दिखाइए", "मिलना चाहता", "मिलना चाहती",
    "book appointment", "see doctor", "meet doctor", "schedule",
    "visit doctor", "need appointment", "appointment chahiye",
]

async def extract_intent(transcript: str, language: str = "hindi") -> dict:
    if not transcript or not transcript.strip():
        return _empty_intent()

    raw = ""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f'Patient language: {language}\nPatient said: "{transcript}"\nExtract clinical intent as JSON.'}
            ],
            max_tokens=1000
        )

        raw = response.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group()

        result = json.loads(raw)

        # Keyword fallback for appointment
        if not result.get("wants_appointment"):
            text_lower = transcript.lower()
            result["wants_appointment"] = any(
                kw.lower() in text_lower for kw in APPOINTMENT_KEYWORDS
            )

        # Ensure topic is never empty
        if not result.get("topic") or result.get("topic") == "unknown":
            result["topic"] = _fallback_topic(transcript)

        # Ensure severity is always an int 1-5
        try:
            result["severity"] = max(1, min(5, int(result.get("severity", 1))))
        except:
            result["severity"] = 1

        return result

    except Exception as e:
        print(f"[NLP] Error: {e}, raw: {raw}")
        result = _empty_intent()
        text_lower = transcript.lower()
        result["wants_appointment"] = any(kw.lower() in text_lower for kw in APPOINTMENT_KEYWORDS)
        result["topic"] = _fallback_topic(transcript)
        result["severity"] = _fallback_severity(transcript)
        return result


def _fallback_topic(transcript: str) -> str:
    t = transcript.lower()
    topic_keywords = {
        "chest_pain":     ["सीने में दर्द", "chest pain", "सीना", "दिल में दर्द"],
        "breathlessness": ["सांस", "breathless", "सांस नहीं", "सांस फूल", "breathing"],
        "heart_attack":   ["दिल का दौरा", "heart attack", "हार्ट अटैक"],
        "stroke":         ["लकवा", "stroke", "paralysis"],
        "unconscious":    ["बेहोश", "unconscious", "गिर गए"],
        "fever":          ["बुखार", "fever", "temperature", "तापमान"],
        "back_pain":      ["पीठ में दर्द", "back pain", "कमर दर्द", "पीठ दर्द"],
        "headache":       ["सिरदर्द", "headache", "सिर में दर्द", "head pain"],
        "dizziness":      ["चक्कर", "dizziness", "dizzy", "vertigo"],
        "weakness":       ["कमजोरी", "weakness", "थकान", "fatigue"],
        "vomiting":       ["उल्टी", "vomiting", "nausea", "मतली"],
        "diarrhea":       ["दस्त", "diarrhea", "loose motion", "पेचिश"],
        "swelling":       ["सूजन", "swelling", "edema"],
        "diabetes":       ["शुगर", "diabetes", "diabetic", "blood sugar"],
        "hypertension":   ["बीपी", "blood pressure", "hypertension", "bp"],
        "medication":     ["दवाई", "medicine", "tablet", "दवा"],
        "sleep":          ["नींद", "sleep", "insomnia"],
        "appointment":    ["अपॉइंटमेंट", "appointment", "मिलना", "बुक"],
    }
    for topic, kws in topic_keywords.items():
        if any(kw in t for kw in kws):
            return topic
    return "general"


def _fallback_severity(transcript: str) -> int:
    t = transcript.lower()
    if any(kw in t for kw in ["बेहोश", "unconscious", "heart attack", "दिल का दौरा", "सांस नहीं", "stroke", "लकवा"]):
        return 5
    if any(kw in t for kw in ["सीने में दर्द", "chest pain", "बहुत तेज दर्द", "severe", "emergency", "ambulance"]):
        return 4
    if any(kw in t for kw in ["दर्द", "pain", "बुखार", "fever", "सांस फूल", "breathless", "बीपी", "शुगर"]):
        return 3
    if any(kw in t for kw in ["कमजोरी", "weakness", "थकान", "fatigue", "थोड़ा"]):
        return 2
    return 1


def _empty_intent() -> dict:
    return {
        "topic": "unknown",
        "sentiment": "neutral",
        "severity": 1,
        "keywords": [],
        "wants_appointment": False,
        "structured_answer": {
            "pain_level": "none",
            "symptoms": [],
            "medication_taken": False,
            "needs_followup": False,
            "patient_concern": ""
        }
    }