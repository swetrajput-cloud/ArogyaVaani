import httpx
import io
import audioop
import wave
from config import settings

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


def convert_twilio_wav_to_16k(audio_bytes: bytes) -> bytes:
    """Convert Twilio's 8kHz mulaw WAV to 16kHz PCM WAV for Sarvam."""
    try:
        # Read the original WAV
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_in:
            channels    = wav_in.getnchannels()
            sampwidth   = wav_in.getsampwidth()
            framerate   = wav_in.getframerate()
            raw_frames  = wav_in.readframes(wav_in.getnframes())

        print(f"[STT] Input audio: {framerate}Hz, {channels}ch, {sampwidth}byte width")

        # If already 16kHz PCM, return as-is
        if framerate == 16000 and sampwidth == 2:
            return audio_bytes

        # Step 1: Convert mulaw to linear PCM if needed
        if sampwidth == 1:
            raw_frames = audioop.ulaw2lin(raw_frames, 2)
            sampwidth  = 2

        # Step 2: Convert to mono if stereo
        if channels == 2:
            raw_frames = audioop.tomono(raw_frames, sampwidth, 1)
            channels   = 1

        # Step 3: Resample to 16kHz
        if framerate != 16000:
            raw_frames, _ = audioop.ratecv(
                raw_frames, sampwidth, channels,
                framerate, 16000, None
            )
            framerate = 16000

        # Write back as WAV
        out_buf = io.BytesIO()
        with wave.open(out_buf, 'wb') as wav_out:
            wav_out.setnchannels(channels)
            wav_out.setsampwidth(sampwidth)
            wav_out.setframerate(framerate)
            wav_out.writeframes(raw_frames)

        result = out_buf.getvalue()
        print(f"[STT] Converted to 16kHz PCM, size: {len(result)} bytes")
        return result

    except Exception as e:
        print(f"[STT] Conversion failed: {e}, sending original")
        return audio_bytes


async def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN") -> str:
    try:
        # Convert audio to 16kHz PCM first
        converted = convert_twilio_wav_to_16k(audio_bytes)

        files = {
            "file": ("audio.wav", io.BytesIO(converted), "audio/wav"),
        }
        data = {
            "language_code": language,
            "model":         "saarika:v2.5",
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
            print(f"[STT] Response body: {response.text}")
            response.raise_for_status()
            result = response.json()
            return result.get("transcript", "")

    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""