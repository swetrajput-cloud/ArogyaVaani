from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AarogyaVaani"
    DEBUG: bool = True
    SECRET_KEY: str = "aarogyavaani_secret_key_2024"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Sarvam AI
    SARVAM_API_KEY: str = ""

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/arogyavaaninew"

    # WebSocket
    WS_SECRET: str = "ws_secret_key"

    class Config:
        env_file = ".env"
        extra = "allow"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()