import httpx
import base64
from config import settings

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

LANGUAGE_VOICE_MAP = {
    "hindi":    ("hi-IN", "meera"),
    "marathi":  ("mr-IN", "meera"),
    "bengali":  ("bn-IN", "meera"),
    "tamil":    ("ta-IN", "meera"),
    "telugu":   ("te-IN", "meera"),
    "gujarati": ("gu-IN", "meera"),
    "bhojpuri": ("hi-IN", "meera"),
}

async def synthesize_speech(text: str, language: str = "hindi") -> bytes:
    lang_code, voice = LANGUAGE_VOICE_MAP.get(language.lower(), ("hi-IN", "meera"))
    try:
        payload = {
            "inputs": [text],
            "target_language_code": lang_code,
            "speaker": voice,
            "model": "bulbul:v2",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "enable_preprocessing": True,
        }
        headers = {
            "api-subscription-key": settings.SARVAM_API_KEY,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(SARVAM_TTS_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            audio_b64 = data.get("audios", [""])[0]
            return base64.b64decode(audio_b64) if audio_b64 else b""
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return b""