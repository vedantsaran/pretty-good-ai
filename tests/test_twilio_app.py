from pathlib import Path

from fastapi.testclient import TestClient

from pgai_patient_bot.config import Settings
from pgai_patient_bot.twilio_app import create_app


def _settings() -> Settings:
    return Settings(
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_from_number="+15551234567",
        public_base_url="https://example.ngrok-free.app",
        pg_target_number="+18054398008",
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


def test_twilio_voice_returns_bidirectional_stream_twiml() -> None:
    client = TestClient(create_app(_settings()))
    response = client.post("/twilio/voice?scenario=appointment_simple")

    assert response.status_code == 200
    assert '<Connect><Stream url="wss://example.ngrok-free.app/twilio/media?scenario=' in (
        response.text
    )
