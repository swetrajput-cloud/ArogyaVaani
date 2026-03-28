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
    """Send WhatsApp alert to doctor when patient is RED or escalated."""
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

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{settings.DOCTOR_PHONE}",
        )
        print(f"[Alert] Doctor WhatsApp sent: {msg.sid}")
        return True
    except Exception as e:
        print(f"[Alert] Doctor WhatsApp failed: {e}")
        return False