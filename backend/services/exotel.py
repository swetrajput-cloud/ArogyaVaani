import httpx

async def make_call(to_number: str, from_number: str, api_key: str,
                    api_token: str, account_sid: str, callback_url: str):
    """Make an outbound call using Exotel."""
    
    # Clean the customer number - Exotel needs 0XXXXXXXXXX format for India
    to = to_number.strip()
    if to.startswith("+91"):
        to = "0" + to[3:]
    elif to.startswith("+"):
        to = to[1:]
    
    # Exotel virtual number stays as-is (09513886363)
    caller_id = from_number.strip()

    url = f"https://api.exotel.com/v1/Accounts/{account_sid}/Calls/connect"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            auth=(api_key, api_token),
            data={
                "From": caller_id,   # Your Exotel number (09513886363)
                "To": to,            # Patient's number (0XXXXXXXXXX)
                "CallerId": caller_id,
                "Url": callback_url,
                "Method": "POST",
                "StatusCallback": callback_url.replace("/inbound/voice", "/inbound/status"),
                "StatusCallbackMethod": "POST",
                "TimeLimit": 300,    # 5 min max call duration
            }
        )
        
        try:
            result = response.json()
        except Exception:
            result = {"raw": response.text}
        
        print(f"[Exotel] Call initiated to {to} | Status: {response.status_code} | Response: {result}")
        return result


async def send_sms(to_number: str, from_number: str, message: str,
                   api_key: str, api_token: str, account_sid: str):
    """Send SMS using Exotel."""
    to = to_number.strip()
    if to.startswith("+91"):
        to = "0" + to[3:]
    elif to.startswith("+"):
        to = to[1:]

    url = f"https://api.exotel.com/v1/Accounts/{account_sid}/Sms/send"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            auth=(api_key, api_token),
            data={
                "From": from_number,
                "To": to,
                "Body": message,
            }
        )
        try:
            result = response.json()
        except Exception:
            result = {"raw": response.text}
            
        print(f"[Exotel SMS] To {to}: {result}")
        return result