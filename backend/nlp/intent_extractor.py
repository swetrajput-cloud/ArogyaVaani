import anthropic
import json
from config import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a clinical NLP engine for AarogyaVaani, an Indian healthcare platform.
Extract structured information from patient speech transcripts.

Always respond with ONLY valid JSON in this exact format:
{
  "topic": "string (main health topic discussed)",
  "sentiment": "positive|neutral|negative|distressed",
  "severity": 1,
  "keywords": ["list", "of", "clinical", "keywords"],
  "structured_answer": {
    "pain_level": "none|mild|moderate|severe",
    "symptoms": ["list of symptoms mentioned"],
    "medication_taken": true,
    "needs_followup": true,
    "patient_concern": "brief summary of main concern"
  }
}
severity is 1-5 (1=mild, 5=critical).
No explanation, no markdown, only JSON."""

async def extract_intent(transcript: str, language: str = "hindi") -> dict:
    if not transcript or not transcript.strip():
        return _empty_intent()

    try:
        user_prompt = f"""Patient language: {language}
Patient said: "{transcript}"

Extract clinical intent as JSON."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    except Exception as e:
        print(f"[NLP] Error: {e}")
        return _empty_intent()

def _empty_intent() -> dict:
    return {
        "topic": "unknown",
        "sentiment": "neutral",
        "severity": 1,
        "keywords": [],
        "structured_answer": {
            "pain_level": "none",
            "symptoms": [],
            "medication_taken": False,
            "needs_followup": False,
            "patient_concern": ""
        }
    }