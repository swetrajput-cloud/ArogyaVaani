import httpx

async def make_call(to_number: str, from_number: str, api_key: str, 
                    api_token: str, account_sid: str, callback_url: str):
    """Make an outbound call using Exotel."""
    # Clean number - ensure it starts with 0 for Indian numbers
    to = to_number.replace("+91", "0").replace("+", "")
    
    url = f"https://api.exotel.com/v1/Accounts/{account_sid}/Calls/connect"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            auth=(api_key, api_token),
            data={
                "From": to,
                "To": from_number,
                "CallerId": from_number,
                "Url": callback_url,
                "Method": "POST",
                "StatusCallback": callback_url.replace("/outbound/voice", "/outbound/status"),
                "StatusCallbackMethod": "POST",
            }
        )
        result = response.json()
        print(f"[Exotel] Call to {to}: {result}")
        return result

async def send_sms(to_number: str, from_number: str, message: str,
                   api_key: str, api_token: str, account_sid: str):
    """Send SMS using Exotel."""
    to = to_number.replace("+91", "0").replace("+", "")
    
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
        result = response.json()
        print(f"[Exotel SMS] To {to}: {result}")
        return result