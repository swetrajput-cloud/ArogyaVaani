# Vaccination keyword detection + Hindi responses

VACCINATION_KEYWORDS = [
    "vaccine", "vaccination", "टीका", "टीकाकरण", "injection", "इंजेक्शन",
    "baby", "बच्चा", "बच्चे", "newborn", "नवजात", "शिशु",
    "bcg", "opv", "pentavalent", "rotavirus", "measles", "hepatitis",
    "immunization", "immunisation", "due vaccine", "next vaccine",
]

AGE_LABEL_TO_WEEKS = {
    "birth": 0,
    "6 weeks": 6,
    "10 weeks": 10,
    "14 weeks": 14,
    "9 months": 36,
    "12 months": 52,
}

WEEKS_TO_HINDI = {
    0:  "जन्म के समय",
    6:  "6 हफ्ते में",
    10: "10 हफ्ते में",
    14: "14 हफ्ते में",
    36: "9 महीने में",
    52: "12 महीने में",
}

def is_vaccination_query(transcript: str) -> bool:
    """Check if caller is asking about vaccination."""
    text = transcript.lower()
    return any(kw in text for kw in VACCINATION_KEYWORDS)

def extract_age_from_transcript(transcript: str) -> int | None:
    """Try to extract baby age in weeks from transcript."""
    text = transcript.lower()
    age_map = {
        "birth": 0, "born": 0, "जन्म": 0, "नवजात": 0,
        "6 week": 6, "six week": 6, "छह हफ्ते": 6, "6 हफ्ते": 6,
        "10 week": 10, "ten week": 10, "दस हफ्ते": 10, "10 हफ्ते": 10,
        "14 week": 14, "fourteen week": 14, "चौदह हफ्ते": 14, "14 हफ्ते": 14,
        "9 month": 36, "nine month": 36, "नौ महीने": 36, "9 महीने": 36,
        "12 month": 52, "twelve month": 52, "बारह महीने": 52, "12 महीने": 52,
    }
    for key, weeks in age_map.items():
        if key in text:
            return weeks
    return None

def get_vaccination_response_hindi(vaccines: list, age_label: str) -> str:
    """Generate Hindi voice response for due vaccines."""
    if not vaccines:
        return "इस उम्र में कोई टीका नहीं है।"
    
    names = ", ".join([v["vaccine_name"] for v in vaccines])
    return (
        f"{age_label} में {len(vaccines)} टीके लगवाने हैं। "
        f"ये हैं: {names}। "
        f"कृपया नज़दीकी सरकारी अस्पताल या आशा कार्यकर्ता से संपर्क करें।"
    )

ASK_AGE_HINDI = (
    "आपके बच्चे की उम्र कितनी है? "
    "जन्म, 6 हफ्ते, 10 हफ्ते, 14 हफ्ते, 9 महीने, या 12 महीने बताएं।"
)