from typing import Tuple, List

RED_KEYWORDS = [
    "chest pain", "सीने में दर्द", "heart attack", "दिल का दौरा",
    "can't breathe", "सांस नहीं", "unconscious", "बेहोश",
    "severe bleeding", "तेज खून", "stroke", "लकवा",
    "very high bp", "बीपी बहुत ज्यादा", "sugar very high", "शुगर बहुत ज्यादा",
    "not moving", "हिल नहीं रहे", "collapsed", "गिर गए",
    "critical", "emergency", "ambulance",
]

AMBER_KEYWORDS = [
    "fever", "बुखार", "vomiting", "उल्टी", "diarrhea", "दस्त",
    "headache", "सिरदर्द", "dizziness", "चक्कर", "swelling", "सूजन",
    "not eating", "खाना नहीं", "weakness", "कमजोरी", "pain", "दर्द",
    "missed medicine", "दवाई नहीं ली", "high bp", "बीपी ज्यादा",
    "high sugar", "शुगर ज्यादा", "breathless", "सांस फूलना",
    "irregular", "अनियमित", "no sleep", "नींद नहीं",
]

def compute_risk(
    transcript: str,
    nlp_output: dict,
    patient_risk_score: float = 0.0
) -> Tuple[str, bool, str, List[str]]:
    """
    Returns: (risk_tier, escalate_flag, escalation_reason, detected_keywords)
    risk_tier: RED / AMBER / GREEN
    """
    text_lower = transcript.lower() if transcript else ""
    detected = []

    # Check RED keywords
    for kw in RED_KEYWORDS:
        if kw.lower() in text_lower:
            detected.append(kw)

    if detected:
        return "RED", True, f"Critical keywords detected: {', '.join(detected)}", detected

    # Check NLP severity
    severity = nlp_output.get("severity", 1)
    sentiment = nlp_output.get("sentiment", "neutral")

    if severity >= 4 or sentiment == "distressed":
        return "RED", True, f"High severity ({severity}) or distressed sentiment", detected

    # Check AMBER keywords
    amber_detected = []
    for kw in AMBER_KEYWORDS:
        if kw.lower() in text_lower:
            amber_detected.append(kw)

    if amber_detected or severity >= 3:
        detected.extend(amber_detected)
        return "AMBER", False, f"Moderate symptoms: {', '.join(amber_detected)}", detected

    # Use patient's existing risk score from dataset
    if patient_risk_score >= 52:
        return "AMBER", False, "High baseline risk score from health camp data", detected

    return "GREEN", False, "", detected