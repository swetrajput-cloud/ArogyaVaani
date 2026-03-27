from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv  # ADD THIS
import os
load_dotenv(override=True)  # ADD THIS — forces .env to load before Settings is built

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

    # GROQ
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/arogyavaaninew"

    # WebSocket
    WS_SECRET: str = "ws_secret_key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"  # ADD THIS — prevents encoding issues on Windows
        extra = "allow"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()