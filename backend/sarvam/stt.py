import httpx
import io
from config import settings

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

async def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN") -> str:
    try:
        files = {
            "file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav"),
        }
        data = {
            "language_code": language,
            "model": "saarika:v2.5",
        }
        headers = {
            "api-subscription-key": settings.SARVAM_API_KEY,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                SARVAM_STT_URL,
                files=files,
                data=data,
                headers=headers,
            )
            print(f"[STT] Status: {response.status_code}")
            print(f"[STT] Response body: {response.text}")  # ADD THIS
            response.raise_for_status()
            result = response.json()
            return result.get("transcript", "")
    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""