import httpx
import io
import wave
import struct
import numpy as np
from config import settings

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


def convert_twilio_wav_to_16k(audio_bytes: bytes) -> bytes:
    """Convert Twilio 8kHz mulaw WAV to 16kHz PCM WAV for Sarvam."""
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_in:
            channels   = wav_in.getnchannels()
            sampwidth  = wav_in.getsampwidth()
            framerate  = wav_in.getframerate()
            raw_frames = wav_in.readframes(wav_in.getnframes())

        print(f"[STT] Input: {framerate}Hz, {channels}ch, {sampwidth}byte")

        # If already good, return as-is
        if framerate == 16000 and sampwidth == 2 and channels == 1:
            return audio_bytes

        # Step 1: Decode mulaw (8-bit) to 16-bit PCM
        if sampwidth == 1:
            # mulaw decode table
            MULAW_BIAS = 33
            samples = []
            for byte in raw_frames:
                byte = ~byte & 0xFF
                sign = byte & 0x80
                exp  = (byte >> 4) & 0x07
                mant = byte & 0x0F
                val  = ((mant << 1) + MULAW_BIAS) << (exp + 2)
                if sign:
                    val = -val
                samples.append(max(-32768, min(32767, val)))
            pcm = np.array(samples, dtype=np.int16)
            sampwidth = 2
        else:
            # Already PCM
            if sampwidth == 2:
                pcm = np.frombuffer(raw_frames, dtype=np.int16)
            else:
                pcm = np.frombuffer(raw_frames, dtype=np.int8).astype(np.int16) * 256

        # Step 2: Stereo to mono
        if channels == 2:
            pcm = pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)
            channels = 1

        # Step 3: Resample to 16000Hz using linear interpolation
        if framerate != 16000:
            original_len = len(pcm)
            target_len   = int(original_len * 16000 / framerate)
            x_old = np.linspace(0, 1, original_len)
            x_new = np.linspace(0, 1, target_len)
            pcm   = np.interp(x_new, x_old, pcm).astype(np.int16)

        # Write output WAV
        out_buf = io.BytesIO()
        with wave.open(out_buf, 'wb') as wav_out:
            wav_out.setnchannels(1)
            wav_out.setsampwidth(2)
            wav_out.setframerate(16000)
            wav_out.writeframes(pcm.tobytes())

        result = out_buf.getvalue()
        print(f"[STT] Converted to 16kHz PCM, size: {len(result)} bytes")
        return result

    except Exception as e:
        print(f"[STT] Conversion failed: {e}, sending original")
        return audio_bytes


async def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN") -> str:
    try:
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
            print(f"[STT] Response: {response.text}")
            response.raise_for_status()
            result = response.json()
            return result.get("transcript", "")

    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""
```

Now add `numpy` to `backend/requirements.txt`:
```
numpy==1.26.4