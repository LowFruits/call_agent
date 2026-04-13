from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    redis_url: str = ""
    scheduling_api_url: str = "https://scheduling-simulation-api.onrender.com"

    # Single-route config for Phase 1
    route_phone: str = ""
    route_clinic_id: str = ""
    route_doctor_id: str = ""
