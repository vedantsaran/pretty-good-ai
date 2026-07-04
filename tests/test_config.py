from pathlib import Path

import pytest

from pgai_patient_bot.config import ASSESSMENT_NUMBER, ConfigError, Settings, normalize_e164


def _settings(target: str = ASSESSMENT_NUMBER) -> Settings:
    return Settings(
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_from_number="+15551234567",
        public_base_url="https://example.ngrok-free.app",
        pg_target_number=target,
        deepgram_api_key="dg",
        deepgram_stt_model="nova-3",
        deepgram_tts_model="aura-2-thalia-en",
        deepseek_api_key="ds",
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
        app_host="0.0.0.0",
        app_port=8000,
        artifact_dir=Path("artifacts/calls"),
        initial_utterance_delay_seconds=4.0,
        max_call_seconds=210,
        record_calls=True,
    )


def test_normalize_e164_us_number() -> None:
    assert normalize_e164("805-439-8008") == "+18054398008"


def test_assessment_number_allowed() -> None:
    _settings("+1 (805) 439-8008").require_safe_call_target()


def test_other_target_rejected() -> None:
    with pytest.raises(ConfigError):
        _settings("+15551234567").require_safe_call_target()
