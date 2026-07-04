import asyncio
from dataclasses import replace
from pathlib import Path
import time

from fastapi.testclient import TestClient

from pgai_patient_bot.llm import PatientReply
from pgai_patient_bot.config import Settings
from pgai_patient_bot.twilio_app import MediaStreamSession, create_app


def _settings() -> Settings:
    return Settings(
        voice_provider="twilio",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_from_number="+15551234567",
        signalwire_project_id="project",
        signalwire_api_token="token",
        signalwire_space_url="example.signalwire.com",
        signalwire_from_number="+15557654321",
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


def test_signalwire_voice_returns_provider_stream_url() -> None:
    client = TestClient(create_app(_settings()))
    response = client.post("/signalwire/voice?scenario=appointment_simple")

    assert response.status_code == 200
    assert '<Connect><Stream url="wss://example.ngrok-free.app/signalwire/media?scenario=' in (
        response.text
    )


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)


class _FakeBrain:
    async def next_reply(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> PatientReply:
        return PatientReply("Tomorrow afternoon works.", False, "test")


class _FakeTTS:
    async def synthesize_mulaw(self, _text: str) -> bytes:
        return b"\xff" * 160


def test_barge_in_clears_patient_audio_and_responds() -> None:
    async def run() -> None:
        websocket = _FakeWebSocket()
        session = MediaStreamSession(websocket, _settings(), "interruption_barge_in", "signalwire")
        session.stream_sid = "stream-1"
        session.speaking = True
        session.brain = _FakeBrain()  # type: ignore[assignment]
        session.tts = _FakeTTS()  # type: ignore[assignment]

        await session._respond_to_agent("Actually, I need to correct that.")

        assert websocket.sent[0] == {"event": "clear", "streamSid": "stream-1"}
        assert websocket.sent[1]["event"] == "media"
        assert websocket.sent[2]["event"] == "mark"

    asyncio.run(run())


def test_opening_line_waits_during_recent_agent_speech() -> None:
    async def run() -> None:
        websocket = _FakeWebSocket()
        settings = replace(_settings(), initial_utterance_delay_seconds=0.0)
        session = MediaStreamSession(websocket, settings, "appointment_simple", "signalwire")
        session.stream_sid = "stream-1"
        session.last_agent_speech_at = time.monotonic()
        session.tts = _FakeTTS()  # type: ignore[assignment]

        task = asyncio.create_task(session._maybe_send_opening_line())
        await asyncio.sleep(0.03)
        assert websocket.sent == []
        session.stop_event.set()
        await asyncio.wait_for(task, timeout=1.0)

    asyncio.run(run())
