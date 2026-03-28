from twilio.rest import Client
from config import settings

def make_call(
    to_number: str,
    callback_url: str,
    status_callback_url: str = None,
) -> dict:
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    call = client.calls.create(
        to=to_number,
        from_=settings.TWILIO_PHONE_NUMBER,
        url=callback_url,
        status_callback=status_callback_url or callback_url,
        status_callback_method="POST",
        record=True,
    )

    return {
    "sid": call.sid,
    "status": call.status,
    "to": call.to,
    "from": str(settings.TWILIO_PHONE_NUMBER),   # ✅ use settings directly
}