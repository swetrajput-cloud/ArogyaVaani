from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
import os

# Load from backend/.env first, then fall back to root .env
backend_env = os.path.join(os.path.dirname(__file__), ".env")
root_env = os.path.join(os.path.dirname(__file__), "..", ".env")

if os.path.exists(backend_env):
    load_dotenv(backend_env, override=True)
else:
    load_dotenv(root_env, override=True)

class Settings(BaseSettings):
    APP_NAME: str = "AarogyaVaani"
    DEBUG: bool = True
    SECRET_KEY: str = "aarogyavaani_secret_key_2024"

    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_PHONE_NUMBER: str = ""

    SARVAM_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/arogyavaani"

    WS_SECRET: str = "ws_secret_key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()