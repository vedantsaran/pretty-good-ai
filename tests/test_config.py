from dataclasses import replace
from pathlib import Path
import re

import pytest

from pgai_patient_bot import telephony
from pgai_patient_bot.cli import check_env
from pgai_patient_bot.config import (
    ASSESSMENT_NUMBER,
    ConfigError,
    Settings,
    load_settings,
    missing_for_calls,
    normalize_e164,
)
from pgai_patient_bot.scenarios import get_scenario


def _settings(target: str = ASSESSMENT_NUMBER) -> Settings:
    return Settings(
        voice_provider="twilio",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_from_number="+15551234567",
        signalwire_project_id="",
        signalwire_api_token="",
        signalwire_space_url="",
        signalwire_from_number="",
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


def test_signalwire_settings_require_signalwire_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOICE_PROVIDER", "signalwire")
    monkeypatch.setenv("PG_TARGET_NUMBER", ASSESSMENT_NUMBER)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.ngrok-free.app/")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds")
    monkeypatch.setenv("SIGNALWIRE_PROJECT_ID", "project")
    monkeypatch.setenv("SIGNALWIRE_API_TOKEN", "token")
    monkeypatch.setenv("SIGNALWIRE_SPACE_URL", "patientbot")
    monkeypatch.setenv("SIGNALWIRE_FROM_NUMBER", "555-765-4321")

    settings = load_settings(env_file=None)

    assert settings.signalwire_space_url == "patientbot.signalwire.com"
    assert settings.signalwire_from_number == "+15557654321"
    assert missing_for_calls(settings) == []


def test_target_number_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PG_TARGET_NUMBER", raising=False)

    settings = load_settings(env_file=None)

    assert "PG_TARGET_NUMBER" in missing_for_calls(settings)
    with pytest.raises(ConfigError, match="PG_TARGET_NUMBER"):
        settings.require_safe_call_target()


def test_check_env_does_not_print_phone_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("VOICE_PROVIDER", "signalwire")
    monkeypatch.setenv("PG_TARGET_NUMBER", ASSESSMENT_NUMBER)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.ngrok-free.app/")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds")
    monkeypatch.setenv("SIGNALWIRE_PROJECT_ID", "project")
    monkeypatch.setenv("SIGNALWIRE_API_TOKEN", "token")
    monkeypatch.setenv("SIGNALWIRE_SPACE_URL", "patientbot")
    monkeypatch.setenv("SIGNALWIRE_FROM_NUMBER", "555-765-4321")

    check_env()

    output = capsys.readouterr().out
    assert "Assessment target lock: OK" in output
    assert not re.search(r"\+?1?[\s().-]*\d{3}[\s().-]*\d{3}[\s().-]*\d{4}", output)


@pytest.mark.parametrize("provider", ["twilio", "signalwire"])
def test_start_assessment_call_enforces_target_lock(
    provider: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("provider-specific call function should not be reached")

    monkeypatch.setattr(telephony, "_start_twilio_call", fail_if_called)
    monkeypatch.setattr(telephony, "_start_signalwire_call", fail_if_called)
    unsafe_settings = replace(_settings("+15551234567"), voice_provider=provider)

    with pytest.raises(ConfigError, match="official assessment number"):
        telephony.start_assessment_call(unsafe_settings, get_scenario("appointment_simple"))
