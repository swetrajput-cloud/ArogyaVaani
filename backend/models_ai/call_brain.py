import json
import os
from typing import Optional

QUESTION_BANK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "question_bank.json"
)

with open(QUESTION_BANK_PATH, encoding="utf-8") as f:
    QUESTION_BANK = json.load(f)

QUESTIONS = QUESTION_BANK["questions"]
CATEGORIES = QUESTION_BANK["categories"]
URGENT_KEYWORDS = QUESTION_BANK["urgent_keywords"]

RISK_LABELS = {
    "hindi":   {"RED": "उच्च", "AMBER": "मध्यम", "GREEN": "सामान्य"},
    "english": {"RED": "High", "AMBER": "Moderate", "GREEN": "Normal"},
    "marathi": {"RED": "उच्च", "AMBER": "मध्यम", "GREEN": "सामान्य"},
    "tamil":   {"RED": "அதிக", "AMBER": "மிதமான", "GREEN": "சாதாரண"},
}

LANGUAGE_NAMES = {
    "hindi":   "हिंदी",
    "english": "English",
    "marathi": "मराठी",
    "tamil":   "தமிழ்",
}


def get_greeting(
    name: str,
    language: str = "hindi",
    camp: str = "",
    condition: str = "",
    risk_level: str = "GREEN",
) -> str:
    template = CATEGORIES["greeting"].get(language, CATEGORIES["greeting"]["hindi"])
    risk_label = RISK_LABELS.get(language, RISK_LABELS["hindi"]).get(risk_level.upper(), risk_level)
    camp_str = camp if camp else ("स्वास्थ्य शिविर" if language == "hindi" else "health camp")
    condition_str = condition if condition else ("सामान्य स्वास्थ्य जांच" if language == "hindi" else "general health check")
    return (
        template
        .replace("{name}", name)
        .replace("{camp}", camp_str)
        .replace("{condition}", condition_str)
        .replace("{risk}", risk_label)
    )


def get_closing(name: str, language: str = "hindi") -> str:
    template = CATEGORIES["closing"].get(language, CATEGORIES["closing"]["hindi"])
    return template.replace("{name}", name)


def get_urgent_alert(language: str = "hindi") -> str:
    return CATEGORIES["urgent_alert"].get(language, CATEGORIES["urgent_alert"]["hindi"])


def is_urgent(transcript: str, language: str = "hindi") -> bool:
    text = transcript.lower()
    keywords = URGENT_KEYWORDS.get(language, URGENT_KEYWORDS["hindi"])
    return any(kw.lower() in text for kw in keywords)


def get_questions_for_patient(
    condition: str,
    risk_level: str,
    language: str = "hindi",
    max_questions: int = 1,
) -> list[dict]:
    tier_map = {
        "RED": "HIGH", "AMBER": "MODERATE", "GREEN": "LOW",
        "HIGH": "HIGH", "MODERATE": "MODERATE", "LOW": "LOW",
    }
    mapped_risk = tier_map.get(risk_level.upper(), "MODERATE")

    matched = []
    for q in QUESTIONS:
        condition_match = (
            "all" in q["conditions"] or
            any(c.lower() in condition.lower() for c in q["conditions"])
        )
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
                    "text": question_text,
                })

    return matched[:max_questions]


def build_call_script(
    patient_name: str,
    condition: str,
    risk_level: str,
    language: str = "hindi",
    camp: str = "",
    consultation_followups: Optional[list] = None,
    max_questions: int = 1,
) -> dict:
    questions = get_questions_for_patient(
        condition, risk_level, language, max_questions
    )

    # Fallback if no question matched
    if not questions:
        fallback = {
            "hindi":   "बीप के बाद आप जो चाहें बताएं।",
            "english": "After the beep, please tell us anything.",
            "marathi": "बीपनंतर तुम्हाला काय सांगायचे ते सांगा।",
            "tamil":   "பீப்க்கு பிறகு நீங்கள் சொல்ல விரும்புவதை சொல்லுங்கள்.",
        }
        questions = [{"id": "Q_FB", "category": "general", "text": fallback.get(language, fallback["hindi"])}]

    return {
        "greeting":        get_greeting(patient_name, language, camp, condition, risk_level),
        "questions":       questions,
        "closing":         get_closing(patient_name, language),
        "urgent_alert":    get_urgent_alert(language),
        "total_questions": len(questions),
        "language":        language,
        "patient_name":    patient_name,
    }