from groq import Groq
import json
import re
from config import settings

client = Groq(api_key=settings.GROQ_API_KEY.strip())

SYSTEM_PROMPT = """You are a clinical NLP engine for AarogyaVaani, an Indian healthcare platform.
Extract structured information from patient speech transcripts.
Always respond with ONLY valid JSON in this exact format:
{
  "topic": "string (main health topic discussed)",
  "sentiment": "positive|neutral|negative|distressed",
  "severity": 1,
  "keywords": ["list", "of", "clinical", "keywords"],
  "wants_appointment": false,
  "structured_answer": {
    "pain_level": "none|mild|moderate|severe",
    "symptoms": ["list of symptoms mentioned"],
    "medication_taken": true,
    "needs_followup": true,
    "patient_concern": "brief summary of main concern"
  }
}
severity is 1-5 (1=mild, 5=critical).
wants_appointment should be true if patient mentions booking, appointment, doctor visit, milna hai, book karo, bulao, dikha do, appointment chahiye, doctor se milna.
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
        user_prompt = f"""Patient language: {language}
Patient said: "{transcript}"
Extract clinical intent as JSON."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000
        )

        raw = response.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group()

        result = json.loads(raw)

        # Keyword fallback in case LLM misses it
        if not result.get("wants_appointment"):
            text_lower = transcript.lower()
            result["wants_appointment"] = any(
                kw.lower() in text_lower for kw in APPOINTMENT_KEYWORDS
            )

        return result

    except Exception as e:
        print(f"[NLP] Error: {e}")
        print(f"[NLP] Raw response: {raw}")
        text_lower = transcript.lower()
        result = _empty_intent()
        result["wants_appointment"] = any(
            kw.lower() in text_lower for kw in APPOINTMENT_KEYWORDS
        )
        return result


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