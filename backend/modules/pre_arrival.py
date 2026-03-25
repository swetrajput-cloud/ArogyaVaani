LANGUAGE_QUESTIONS = {
    "hindi": [
        "नमस्ते! मैं आरोग्यवाणी से बोल रही हूं। आपका नाम क्या है?",
        "आप किस समस्या के लिए अस्पताल आ रहे हैं?",
        "आपको यह समस्या कितने दिनों से है?",
        "क्या आपको अभी कोई दर्द हो रहा है? अगर हां, तो 1 से 10 में कितना?",
        "क्या आप कोई दवाई ले रहे हैं? अगर हां, तो कौन सी?",
        "क्या आपको कोई एलर्जी है?",
        "धन्यवाद! हमने आपकी जानकारी दर्ज कर ली है। डॉक्टर जल्द आपसे मिलेंगे।"
    ],
    "marathi": [
        "नमस्कार! मी आरोग्यवाणीतून बोलत आहे. तुमचे नाव काय आहे?",
        "तुम्ही कोणत्या समस्येसाठी रुग्णालयात येत आहात?",
        "ही समस्या तुम्हाला किती दिवसांपासून आहे?",
        "तुम्हाला आत्ता काही वेदना होत आहेत का? असल्यास 1 ते 10 मध्ये किती?",
        "तुम्ही कोणती औषधे घेत आहात?",
        "तुम्हाला काही ऍलर्जी आहे का?",
        "धन्यवाद! आम्ही तुमची माहिती नोंदवली आहे."
    ],
    "english": [
        "Hello! I am calling from AarogyaVaani. May I know your name?",
        "What is the reason for your hospital visit today?",
        "How long have you been experiencing this problem?",
        "Are you in any pain right now? If yes, on a scale of 1 to 10?",
        "Are you currently taking any medications? If yes, which ones?",
        "Do you have any known allergies?",
        "Thank you! We have recorded your information. The doctor will see you shortly."
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