import httpx
import base64
from config import settings

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

async def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN") -> str:
    try:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "audio": audio_b64,
            "language_code": language,
            "model": "saarika:v2",
        }
        headers = {
            "api-subscription-key": settings.SARVAM_API_KEY,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(SARVAM_STT_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("transcript", "")
    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""