LANGUAGE_QUESTIONS = {
    "hindi": [
        "नमस्ते! मैं आरोग्यवाणी से बोल रही हूं। क्या मैं मरीज के परिवार के किसी सदस्य से बात कर सकती हूं?",
        "मरीज अभी कैसा महसूस कर रहे हैं?",
        "क्या मरीज ने आज अपनी सभी दवाइयां ली हैं?",
        "क्या मरीज खाना-पानी ठीक से ले पा रहे हैं?",
        "क्या मरीज को कोई तकलीफ हो रही है जैसे बुखार, दर्द या सांस लेने में दिक्कत?",
        "क्या मरीज चल-फिर पा रहे हैं या बिस्तर पर हैं?",
        "धन्यवाद! आपकी जानकारी हमारे डॉक्टर देखेंगे।"
    ],
    "english": [
        "Hello! I am calling from AarogyaVaani. May I speak with a family member of the patient?",
        "How is the patient feeling right now?",
        "Has the patient taken all medications today?",
        "Is the patient able to eat and drink normally?",
        "Is the patient experiencing any discomfort such as fever, pain, or breathing difficulty?",
        "Is the patient able to move around or are they bedridden?",
        "Thank you! Our doctors will review this information."
    ]
}

def get_questions(language: str = "hindi") -> list:
    return LANGUAGE_QUESTIONS.get(language.lower(), LANGUAGE_QUESTIONS["hindi"])

def get_question(index: int, language: str = "hindi") -> str:
    questions = get_questions(language)
    if index < len(questions):
        return questions[index]
    return ""

def is_complete(index: int, language: str = "hindi") -> bool:
    return index >= len(get_questions(language))