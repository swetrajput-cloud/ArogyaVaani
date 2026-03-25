import asyncio
import json
import base64
from fastapi import WebSocket
from call_engine.state_machine import get_session, CallState
from sarvam.stt import transcribe_audio
from sarvam.tts import synthesize_speech
from nlp.intent_extractor import extract_intent
from nlp.risk_scorer import compute_risk
from modules import pre_arrival, post_discharge, chronic_coach, caregiver
from dashboard.ws_broadcaster import broadcast_update

MODULE_MAP = {
    "pre_arrival": pre_arrival,
    "post_discharge": post_discharge,
    "chronic_coach": chronic_coach,
    "caregiver": caregiver,
}

async def handle_media_stream(websocket: WebSocket, call_sid: str):
    """
    WebSocket handler for Twilio Media Streams.
    Receives raw audio, runs STT → NLP → TTS pipeline.
    """
    await websocket.accept()
    print(f"[MediaStream] Connected: {call_sid}")

    session = get_session(call_sid)
    if not session:
        await websocket.close()
        return

    session.transition(CallState.GREETING)
    audio_buffer = bytearray()

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                print(f"[MediaStream] Stream started: {call_sid}")

            elif event == "media":
                # Accumulate audio chunks
                chunk = base64.b64decode(data["media"]["payload"])
                audio_buffer.extend(chunk)

            elif event == "stop":
                print(f"[MediaStream] Stream stopped: {call_sid}")
                if audio_buffer:
                    await process_audio_turn(
                        websocket, session, bytes(audio_buffer)
                    )
                    audio_buffer.clear()
                break

    except Exception as e:
        print(f"[MediaStream] Error: {e}")
        session.transition(CallState.FAILED)
    finally:
        await websocket.close()

async def process_audio_turn(websocket, session, audio_bytes: bytes):
    """Run the full STT → NLP → Risk → TTS pipeline for one patient turn."""
    session.transition(CallState.PROCESSING)

    # 1. STT
    transcript = await transcribe_audio(audio_bytes, language=session.language)
    if transcript:
        session.add_transcript(transcript)
        print(f"[STT] Transcript: {transcript}")

    # 2. NLP
    nlp_output = await extract_intent(transcript, language=session.language)
    session.nlp_outputs.append(nlp_output)

    # 3. Risk scoring
    risk_tier, escalate, reason, keywords = compute_risk(transcript, nlp_output)
    session.risk_tier = risk_tier
    session.escalate_flag = escalate
    session.escalation_reason = reason

    # 4. Broadcast to dashboard
    await broadcast_update({
        "call_sid": session.call_sid,
        "patient_id": session.patient_id,
        "risk_tier": risk_tier,
        "escalate": escalate,
        "transcript": transcript,
        "nlp": nlp_output,
    })

    # 5. Advance to next question
    session.advance_question()
    module = MODULE_MAP.get(session.module_type, post_discharge)

    if module.is_complete(session.question_index, session.language):
        session.transition(CallState.COMPLETE)
        return

    session.transition(CallState.QUESTIONING)
    next_q = module.get_question(session.question_index, session.language)

    # 6. TTS → send audio back
    audio_response = await synthesize_speech(next_q, language=session.language)
    if audio_response:
        encoded = base64.b64encode(audio_response).decode("utf-8")
        await websocket.send_text(json.dumps({
            "event": "media",
            "media": {"payload": encoded}
        }))