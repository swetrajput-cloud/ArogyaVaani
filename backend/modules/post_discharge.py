LANGUAGE_QUESTIONS = {
    "hindi": [
        "नमस्ते! मैं आरोग्यवाणी से बोल रही हूं। अस्पताल से छुट्टी के बाद आप कैसा महसूस कर रहे हैं?",
        "क्या आपको बुखार, सीने में दर्द, या सांस लेने में तकलीफ हो रही है?",
        "क्या आप अपनी सभी दवाइयां समय पर ले रहे हैं?",
        "क्या आपके घाव या ऑपरेशन वाली जगह पर कोई सूजन या लालिमा है?",
        "क्या आप खाना-पानी ठीक से ले पा रहे हैं?",
        "क्या आपको चक्कर आना या बेहोशी जैसा लग रहा है?",
        "आपका दर्द 1 से 10 में कितना है?",
        "धन्यवाद! आपकी जानकारी हमारे डॉक्टर देखेंगे। जरूरत पड़ने पर हम आपसे संपर्क करेंगे।"
    ],
    "marathi": [
        "नमस्कार! मी आरोग्यवाणीतून बोलत आहे. रुग्णालयातून घरी आल्यावर तुम्हाला कसे वाटत आहे?",
        "तुम्हाला ताप, छातीत दुखणे किंवा श्वास घेण्यास त्रास होत आहे का?",
        "तुम्ही सर्व औषधे वेळेवर घेत आहात का?",
        "जखम किंवा ऑपरेशनच्या ठिकाणी सूज किंवा लालसरपणा आहे का?",
        "तुम्ही नीट जेवण-पाणी घेत आहात का?",
        "तुम्हाला चक्कर येणे किंवा बेशुद्धी वाटत आहे का?",
        "तुमचे दुखणे 1 ते 10 मध्ये किती आहे?",
        "धन्यवाद! तुमची माहिती आमचे डॉक्टर पाहतील."
    ],
    "english": [
        "Hello! I am calling from AarogyaVaani. How are you feeling after being discharged?",
        "Are you experiencing fever, chest pain, or difficulty breathing?",
        "Are you taking all your medications on time?",
        "Is there any swelling or redness at your wound or surgery site?",
        "Are you able to eat and drink normally?",
        "Are you feeling dizzy or faint?",
        "On a scale of 1 to 10, how is your pain level?",
        "Thank you! Our doctors will review your information and contact you if needed."
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