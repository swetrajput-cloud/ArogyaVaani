import json
import os
from typing import Optional

# Load question bank once at startup
QUESTION_BANK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "question_bank.json"
)

with open(QUESTION_BANK_PATH, encoding="utf-8") as f:
    QUESTION_BANK = json.load(f)

QUESTIONS = QUESTION_BANK["questions"]
CATEGORIES = QUESTION_BANK["categories"]
URGENT_KEYWORDS = QUESTION_BANK["urgent_keywords"]


def get_greeting(name: str, language: str = "hindi") -> str:
    template = CATEGORIES["greeting"].get(language, CATEGORIES["greeting"]["hindi"])
    return template.replace("{name}", name)


def get_closing(name: str, language: str = "hindi") -> str:
    template = CATEGORIES["closing"].get(language, CATEGORIES["closing"]["hindi"])
    return template.replace("{name}", name)


def get_urgent_alert(language: str = "hindi") -> str:
    return CATEGORIES["urgent_alert"].get(language, CATEGORIES["urgent_alert"]["hindi"])


def is_urgent(transcript: str, language: str = "hindi") -> bool:
    """Check if transcript contains urgent keywords."""
    text = transcript.lower()
    keywords = URGENT_KEYWORDS.get(language, URGENT_KEYWORDS["hindi"])
    return any(kw.lower() in text for kw in keywords)


def get_questions_for_patient(
    condition: str,
    risk_level: str,
    language: str = "hindi",
    max_questions: int = 5
) -> list[dict]:
    """
    Get relevant questions for a patient based on their condition and risk level.
    Returns list of {id, question_text} dicts.
    """
    # Map RED/AMBER/GREEN → HIGH/MODERATE/LOW to match question bank format
    tier_map = {
        "RED": "HIGH",
        "AMBER": "MODERATE",
        "GREEN": "LOW",
        "HIGH": "HIGH",
        "MODERATE": "MODERATE",
        "LOW": "LOW",
    }
    mapped_risk = tier_map.get(risk_level.upper(), risk_level.upper())

    matched = []
    for q in QUESTIONS:
        # Check if condition matches
        condition_match = (
            "all" in q["conditions"] or
            any(c.lower() in condition.lower() for c in q["conditions"])
        )
        # Check both original and mapped risk level
        risk_match = (
            risk_level.upper() in q["risk_levels"] or
            mapped_risk in q["risk_levels"]
        )

        if condition_match and risk_match:
            question_text = q.get(language, q.get("hindi", ""))
            if question_text:
                matched.append({
                    "id": q["id"],
                    "category": q["category"],
                    "text": question_text
                })

    # Prioritize: pain > medication > condition-specific > general
    priority_order = ["pain", "medication", "diabetes", "hypertension",
                      "heart", "respiratory", "kidney", "mental_health",
                      "fever", "general", "diet", "sleep", "followup"]

    matched.sort(key=lambda x: (
        priority_order.index(x["category"])
        if x["category"] in priority_order else 99
    ))

    return matched[:max_questions]


def get_followup_questions_from_consultation(
    consultation_follow_up: list,
    language: str = "hindi"
) -> list[str]:
    """
    Extract follow-up questions stored from a doctor consultation.
    These override the standard question bank.
    """
    if not consultation_follow_up:
        return []
    return [q.get(language, q.get("text", "")) for q in consultation_follow_up if q]


def build_call_script(
    patient_name: str,
    condition: str,
    risk_level: str,
    language: str = "hindi",
    consultation_followups: Optional[list] = None,
    max_questions: int = 5
) -> dict:
    """
    Build a complete call script for a patient.
    Returns: { greeting, questions: [...], closing, urgent_alert }
    """
    # Use consultation follow-ups if available, else use question bank
    if consultation_followups:
        questions = get_followup_questions_from_consultation(
            consultation_followups, language
        )
        questions = [{"id": f"CF{i}", "category": "consultation", "text": q}
                     for i, q in enumerate(questions)]
    else:
        questions = get_questions_for_patient(
            condition, risk_level, language, max_questions
        )

    return {
        "greeting": get_greeting(patient_name, language),
        "questions": questions,
        "closing": get_closing(patient_name, language),
        "urgent_alert": get_urgent_alert(language),
        "total_questions": len(questions),
        "language": language,
        "patient_name": patient_name,
    }