LANGUAGE_QUESTIONS = {
    "hindi": [
        "नमस्ते! मैं आरोग्यवाणी से बोल रही हूं। इस हफ्ते आपकी तबीयत कैसी रही?",
        "क्या आपने इस हफ्ते अपनी सभी दवाइयां नियमित रूप से लीं?",
        "आपने आज सुबह अपना ब्लड शुगर या बीपी मापा? क्या रीडिंग आई?",
        "क्या आपने इस हफ्ते व्यायाम या टहलना किया?",
        "आपने क्या खाया इस हफ्ते? मीठा, तला हुआ या नमकीन ज्यादा तो नहीं खाया?",
        "क्या आपको कोई नई तकलीफ हुई जैसे सूजन, धुंधला दिखना, या पैरों में दर्द?",
        "आपकी नींद कैसी रही इस हफ्ते?",
        "धन्यवाद! आप बहुत अच्छा काम कर रहे हैं। अगले हफ्ते फिर बात करेंगे।"
    ],
    "marathi": [
        "नमस्कार! मी आरोग्यवाणीतून बोलत आहे. या आठवड्यात तुम्हाला कसे वाटले?",
        "या आठवड्यात तुम्ही सर्व औषधे नियमितपणे घेतली का?",
        "आज सकाळी तुम्ही रक्तातील साखर किंवा बीपी मोजली का? काय रीडिंग आली?",
        "या आठवड्यात तुम्ही व्यायाम किंवा चालणे केले का?",
        "या आठवड्यात तुम्ही काय खाल्ले? जास्त गोड, तळलेले खाल्ले का?",
        "तुम्हाला नवीन त्रास झाला का जसे सूज, अंधुक दिसणे किंवा पायात दुखणे?",
        "या आठवड्यात तुमची झोप कशी होती?",
        "धन्यवाद! तुम्ही खूप चांगले करत आहात. पुढच्या आठवड्यात पुन्हा बोलू."
    ],
    "english": [
        "Hello! I am calling from AarogyaVaani. How have you been feeling this week?",
        "Did you take all your medications regularly this week?",
        "Did you check your blood sugar or BP this morning? What was the reading?",
        "Did you exercise or go for walks this week?",
        "How was your diet this week? Did you consume too much sugar, fried, or salty food?",
        "Did you experience any new symptoms like swelling, blurred vision, or leg pain?",
        "How was your sleep this week?",
        "Thank you! You are doing great. We will talk again next week."
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