from twilio.rest import Client
from config import settings


def send_doctor_alert(
    patient_name: str,
    patient_phone: str,
    condition: str,
    risk_tier: str,
    transcript: str,
    escalation_reason: str = "",
) -> bool:
    if not settings.DOCTOR_PHONE:
        print("[Alert] DOCTOR_PHONE not set, skipping WhatsApp alert")
        return False

    risk_emoji = {"RED": "🔴", "AMBER": "🟡", "GREEN": "🟢"}.get(risk_tier.upper(), "⚠️")
    transcript_snippet = transcript[:200] + "..." if len(transcript) > 200 else transcript

    message = (
        f"{risk_emoji} *AROGYAVAANI ALERT*\n"
        f"*Patient:* {patient_name}\n"
        f"*Phone:* {patient_phone}\n"
        f"*Condition:* {condition}\n"
        f"*Risk:* {risk_tier.upper()}\n"
        f"*Reason:* {escalation_reason or 'High risk detected'}\n"
        f"*Transcript:* {transcript_snippet}"
    )

    return _send_whatsapp(settings.DOCTOR_PHONE, message)


def send_whatsapp_to_patient(phone: str, message: str) -> bool:
    return _send_whatsapp(phone, message)


def _send_whatsapp(to_phone: str, message: str) -> bool:
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{to_phone}",
        )
        print(f"[Alert] WhatsApp sent to {to_phone}: {msg.sid}")
        return True
    except Exception as e:
        print(f"[Alert] WhatsApp failed to {to_phone}: {e}")
        return False