from typing import Tuple, List

RED_KEYWORDS = [
    # Hindi critical
    "सीने में दर्द", "सीना दर्द", "दिल में दर्द", "दिल का दौरा",
    "सांस नहीं", "सांस नहीं आ", "सांस रुक", "सांस बंद",
    "बेहोश", "होश नहीं", "गिर गए", "गिर गया", "गिर गई",
    "लकवा", "हाथ सुन्न", "मुंह टेढ़ा",
    "तेज खून", "खून बह", "बहुत खून",
    "बीपी बहुत ज्यादा", "शुगर बहुत ज्यादा", "बहुत तेज बुखार",
    "हिल नहीं रहे", "उठ नहीं पा",
    # English critical
    "chest pain", "heart attack", "can't breathe", "cannot breathe",
    "not breathing", "unconscious", "collapsed", "severe bleeding",
    "stroke", "paralysis", "very high bp", "sugar very high",
    "not moving", "critical", "emergency", "ambulance",
    "severe chest", "crushing pain", "pressure in chest",
]

AMBER_KEYWORDS = [
    # Hindi moderate
    "बुखार", "उल्टी", "दस्त", "सिरदर्द", "चक्कर", "सूजन",
    "खाना नहीं", "कमजोरी", "दर्द", "दवाई नहीं ली", "दवा नहीं",
    "बीपी ज्यादा", "शुगर ज्यादा", "सांस फूलना", "सांस फूल",
    "अनियमित", "नींद नहीं", "थकान", "पेट दर्द", "पीठ दर्द",
    "कमर दर्द", "जोड़ों में दर्द", "मतली", "पेचिश",
    "ज्यादा पसीना", "हाथ पैर ठंडे", "धड़कन तेज",
    # English moderate
    "fever", "vomiting", "diarrhea", "headache", "dizziness",
    "swelling", "not eating", "weakness", "pain", "missed medicine",
    "high bp", "high sugar", "breathless", "irregular", "no sleep",
    "fatigue", "stomach pain", "back pain", "joint pain", "nausea",
    "palpitations", "sweating", "cold hands", "cold feet",
    "loose motion", "edema", "blurred vision", "numbness",
]

# Topic → default severity if NLP fails
TOPIC_BASE_SEVERITY = {
    "chest_pain": 4,
    "heart_attack": 5,
    "stroke": 5,
    "unconscious": 5,
    "breathlessness": 4,
    "bleeding": 4,
    "fever": 3,
    "back_pain": 2,
    "headache": 2,
    "dizziness": 3,
    "weakness": 2,
    "diabetes": 3,
    "hypertension": 3,
    "vomiting": 2,
    "diarrhea": 2,
    "swelling": 2,
    "medication": 2,
    "sleep": 1,
    "diet": 1,
    "appointment": 1,
    "general": 1,
    "unknown": 1,
}


def compute_risk(
    transcript: str,
    nlp_output: dict,
    patient_risk_score: float = 0.0
) -> Tuple[str, bool, str, List[str]]:
    """
    Returns: (risk_tier, escalate_flag, escalation_reason, detected_keywords)
    """
    text_lower = transcript.lower() if transcript else ""
    detected = []

    # 1. RED keyword check
    for kw in RED_KEYWORDS:
        if kw.lower() in text_lower:
            detected.append(kw)

    if detected:
        return "RED", True, f"Critical keywords: {', '.join(detected[:3])}", detected

    # 2. NLP severity + sentiment
    severity = nlp_output.get("severity", 1)
    sentiment = nlp_output.get("sentiment", "neutral")
    topic = nlp_output.get("topic", "unknown")

    # Boost severity from topic if NLP gave low score but topic is serious
    topic_min = TOPIC_BASE_SEVERITY.get(topic, 1)
    severity = max(severity, topic_min)

    if severity >= 4 or sentiment == "distressed":
        return "RED", True, f"Severity {severity}/5 — {topic}", detected

    # 3. AMBER keyword check
    amber_detected = []
    for kw in AMBER_KEYWORDS:
        if kw.lower() in text_lower:
            amber_detected.append(kw)

    if amber_detected or severity >= 3:
        detected.extend(amber_detected)
        return "AMBER", False, f"Moderate symptoms — {topic}", detected

    # 4. Baseline risk score from health camp data
    if patient_risk_score >= 52:
        return "AMBER", False, "High baseline risk score", detected

    return "GREEN", False, "", detected