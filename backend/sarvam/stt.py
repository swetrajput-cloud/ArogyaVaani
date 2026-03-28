import httpx
import io
import wave
import numpy as np
import asyncio
from config import settings

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


def convert_twilio_wav_to_16k(audio_bytes: bytes) -> bytes:
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_in:
            channels   = wav_in.getnchannels()
            sampwidth  = wav_in.getsampwidth()
            framerate  = wav_in.getframerate()
            raw_frames = wav_in.readframes(wav_in.getnframes())

        print(f"[STT] Input: {framerate}Hz, {channels}ch, {sampwidth}byte, {len(raw_frames)} raw bytes")

        if sampwidth == 1:
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
        elif sampwidth == 2:
            pcm = np.frombuffer(raw_frames, dtype=np.int16)
        else:
            pcm = np.frombuffer(raw_frames, dtype=np.int8).astype(np.int16) * 256

        if channels == 2:
            pcm = pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)

        if framerate != 16000:
            original_len = len(pcm)
            target_len   = int(original_len * 16000 / framerate)
            x_old = np.linspace(0, 1, original_len)
            x_new = np.linspace(0, 1, target_len)
            pcm   = np.interp(x_new, x_old, pcm).astype(np.int16)

        # Trim to max 25 seconds to stay under Sarvam 30s limit
        max_samples = 25 * 16000
        if len(pcm) > max_samples:
            print(f"[STT] Trimming audio from {len(pcm)} to {max_samples} samples (25s max)")
            pcm = pcm[:max_samples]

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


async def download_recording_with_retry(url: str, auth: tuple, max_attempts: int = 6) -> bytes:
    prev_size = 0
    audio_bytes = b""

    for attempt in range(max_attempts):
        wait = 3 + (attempt * 2)
        print(f"[STT] Waiting {wait}s before download attempt {attempt + 1}...")
        await asyncio.sleep(wait)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{url}.wav", auth=auth)
                audio_bytes = resp.content
                size = len(audio_bytes)
                print(f"[STT] Attempt {attempt + 1}: downloaded {size} bytes")

                if size > 10000 and size == prev_size:
                    print(f"[STT] Size stable at {size} bytes — recording ready")
                    return audio_bytes

                prev_size = size

                if attempt == max_attempts - 1:
                    print(f"[STT] Max attempts reached, using last download ({size} bytes)")
                    return audio_bytes

        except Exception as e:
            print(f"[STT] Download attempt {attempt + 1} failed: {e}")

    return audio_bytes


async def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN") -> str:
    try:
        converted = convert_twilio_wav_to_16k(audio_bytes)

        with wave.open(io.BytesIO(converted), 'rb') as w:
            raw = w.readframes(w.getnframes())
        pcm_check = np.frombuffer(raw, dtype=np.int16)
        rms = np.sqrt(np.mean(pcm_check.astype(np.float32) ** 2))
        print(f"[STT] Audio RMS (volume): {rms:.1f}")
        if rms < 50:
            print(f"[STT] Audio is silent (RMS {rms:.1f} < 50), skipping STT")
            return ""

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