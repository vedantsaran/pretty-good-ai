from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ASSESSMENT_NUMBER = "+18054398008"


class ConfigError(RuntimeError):
    """Raised when required local configuration is missing or unsafe."""


def normalize_e164(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if value and value.strip().startswith("+") and 8 <= len(digits) <= 15:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return value.strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    voice_provider: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    signalwire_project_id: str
    signalwire_api_token: str
    signalwire_space_url: str
    signalwire_from_number: str
    public_base_url: str
    pg_target_number: str
    deepgram_api_key: str
    deepgram_stt_model: str
    deepgram_tts_model: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    app_host: str
    app_port: int
    artifact_dir: Path
    initial_utterance_delay_seconds: float
    max_call_seconds: int
    record_calls: bool

    def require_supported_voice_provider(self) -> None:
        if self.voice_provider not in {"twilio", "signalwire"}:
            raise ConfigError("VOICE_PROVIDER must be either 'twilio' or 'signalwire'.")

    @property
    def caller_from_number(self) -> str:
        if self.voice_provider == "signalwire":
            return self.signalwire_from_number
        return self.twilio_from_number

    @property
    def public_ws_base_url(self) -> str:
        if self.public_base_url.startswith("https://"):
            return "wss://" + self.public_base_url.removeprefix("https://")
        if self.public_base_url.startswith("http://"):
            return "ws://" + self.public_base_url.removeprefix("http://")
        return self.public_base_url

    def require_safe_call_target(self) -> None:
        if normalize_e164(self.pg_target_number) != ASSESSMENT_NUMBER:
            raise ConfigError(
                "Refusing to call the configured target. "
                "This assessment bot is locked to the official assessment number."
            )


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    if env_file:
        load_dotenv(env_file)

    target = normalize_e164(os.getenv("PG_TARGET_NUMBER", ASSESSMENT_NUMBER))
    from_number = normalize_e164(os.getenv("TWILIO_FROM_NUMBER", ""))
    signalwire_from_number = normalize_e164(os.getenv("SIGNALWIRE_FROM_NUMBER", ""))
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    signalwire_space_url = _normalize_signalwire_space_url(os.getenv("SIGNALWIRE_SPACE_URL", ""))

    return Settings(
        voice_provider=os.getenv("VOICE_PROVIDER", "twilio").strip().lower(),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
        twilio_from_number=from_number,
        signalwire_project_id=os.getenv("SIGNALWIRE_PROJECT_ID", "").strip(),
        signalwire_api_token=os.getenv("SIGNALWIRE_API_TOKEN", "").strip(),
        signalwire_space_url=signalwire_space_url,
        signalwire_from_number=signalwire_from_number,
        public_base_url=public_base_url,
        pg_target_number=target,
        deepgram_api_key=os.getenv("DEEPGRAM_API_KEY", "").strip(),
        deepgram_stt_model=os.getenv("DEEPGRAM_STT_MODEL", "nova-3").strip(),
        deepgram_tts_model=os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-thalia-en").strip(),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        .strip()
        .rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
        app_host=os.getenv("APP_HOST", "0.0.0.0").strip(),
        app_port=int(os.getenv("APP_PORT", "8000")),
        artifact_dir=Path(os.getenv("ARTIFACT_DIR", "artifacts/calls")),
        initial_utterance_delay_seconds=float(
            os.getenv("INITIAL_UTTERANCE_DELAY_SECONDS", "4.0")
        ),
        max_call_seconds=int(os.getenv("MAX_CALL_SECONDS", "210")),
        record_calls=_env_bool("RECORD_CALLS", True),
    )


def _normalize_signalwire_space_url(value: str) -> str:
    value = value.strip().removeprefix("https://").removeprefix("http://").strip("/")
    if value and "." not in value:
        return f"{value}.signalwire.com"
    return value


def missing_for_server(settings: Settings) -> list[str]:
    required = {
        "PUBLIC_BASE_URL": settings.public_base_url,
        "DEEPGRAM_API_KEY": settings.deepgram_api_key,
        "DEEPSEEK_API_KEY": settings.deepseek_api_key,
    }
    return [name for name, value in required.items() if not value]


def missing_for_calls(settings: Settings) -> list[str]:
    required = {
        "PUBLIC_BASE_URL": settings.public_base_url,
        "DEEPGRAM_API_KEY": settings.deepgram_api_key,
        "DEEPSEEK_API_KEY": settings.deepseek_api_key,
    }
    if settings.voice_provider == "twilio":
        required.update(
            {
                "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
                "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
                "TWILIO_FROM_NUMBER": settings.twilio_from_number,
            }
        )
    elif settings.voice_provider == "signalwire":
        required.update(
            {
                "SIGNALWIRE_PROJECT_ID": settings.signalwire_project_id,
                "SIGNALWIRE_API_TOKEN": settings.signalwire_api_token,
                "SIGNALWIRE_SPACE_URL": settings.signalwire_space_url,
                "SIGNALWIRE_FROM_NUMBER": settings.signalwire_from_number,
            }
        )
    else:
        required["VOICE_PROVIDER"] = ""
    return [name for name, value in required.items() if not value]


def assert_ready_for_server(settings: Settings) -> None:
    settings.require_supported_voice_provider()
    settings.require_safe_call_target()
    missing = missing_for_server(settings)
    if missing:
        raise ConfigError("Missing required server environment variables: " + ", ".join(missing))


def assert_ready_for_calls(settings: Settings) -> None:
    settings.require_supported_voice_provider()
    settings.require_safe_call_target()
    missing = missing_for_calls(settings)
    if missing:
        raise ConfigError("Missing required call environment variables: " + ", ".join(missing))
