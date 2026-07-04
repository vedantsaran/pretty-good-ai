from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from contextlib import suppress
from typing import Any

import websockets
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
)

from .artifacts import CallArtifacts, download_call_recording
from .config import Settings, assert_ready_for_server, load_settings
from .deepgram import DeepgramTTS, deepgram_stt_url
from .llm import PatientBrain
from .scenarios import get_scenario
from .telephony import complete_call

logger = logging.getLogger(__name__)

OPENING_SILENCE_SECONDS = 1.25
OPENING_RECHECK_SECONDS = 0.1


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="PGAI Patient Bot")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.api_route("/{provider}/voice", methods=["GET", "POST"])
    async def carrier_voice(provider: str, scenario: str = Query(...)) -> Response:
        _require_provider_path(provider)
        assert_ready_for_server(settings)
        get_scenario(scenario)
        stream_url = f"{settings.public_ws_base_url}/{provider}/media?scenario={scenario}"
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Connect>"
            f'<Stream url="{stream_url}" />'
            "</Connect>"
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")

    @app.api_route("/{provider}/status", methods=["GET", "POST"])
    async def carrier_status(provider: str, request: Request) -> dict[str, str]:
        _require_provider_path(provider)
        form = await request.form()
        logger.info("%s status callback: %s", provider, dict(form))
        return {"status": "ok"}

    @app.api_route("/{provider}/recording", methods=["GET", "POST"])
    async def carrier_recording(
        provider: str,
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> dict[str, str]:
        _require_provider_path(provider)
        form = await request.form()
        recording_url = str(form.get("RecordingUrl", ""))
        recording_sid = str(form.get("RecordingSid", ""))
        call_sid = str(form.get("CallSid", ""))
        if recording_url and recording_sid and call_sid:
            background_tasks.add_task(
                download_call_recording,
                settings,
                recording_url,
                recording_sid,
                call_sid,
            )
        return {"status": "ok"}

    @app.websocket("/{provider}/media")
    async def carrier_media(websocket: WebSocket, provider: str, scenario: str = Query(...)) -> None:
        _require_provider_path(provider)
        assert_ready_for_server(settings)
        session = MediaStreamSession(websocket, settings, scenario, provider)
        await session.run()

    return app


app = create_app()


def _require_provider_path(provider: str) -> None:
    if provider not in {"twilio", "signalwire"}:
        raise HTTPException(status_code=404, detail="Unknown voice provider.")


class MediaStreamSession:
    def __init__(
        self,
        websocket: WebSocket,
        settings: Settings,
        scenario_id: str,
        provider: str,
    ) -> None:
        self.websocket = websocket
        self.settings = settings
        self.provider = provider
        self.scenario = get_scenario(scenario_id)
        self.brain = PatientBrain(settings)
        self.tts = DeepgramTTS(settings)
        self.stream_sid = ""
        self.call_sid = ""
        self.artifacts: CallArtifacts | None = None
        self.transcript: list[dict[str, str]] = []
        self.stop_event = asyncio.Event()
        self.speaking = False
        self.pending_final_parts: list[str] = []
        self.last_response_at = 0.0
        self.last_agent_speech_at = 0.0

    async def run(self) -> None:
        await self.websocket.accept()
        stt_ws = await _connect_deepgram_stt(self.settings)
        tasks = [
            asyncio.create_task(self._receive_carrier(stt_ws)),
            asyncio.create_task(self._receive_deepgram(stt_ws)),
            asyncio.create_task(self._deepgram_keepalive(stt_ws)),
            asyncio.create_task(self._timeout_guard()),
        ]
        try:
            await self.stop_event.wait()
        finally:
            for task in tasks:
                task.cancel()
            with suppress(Exception):
                await stt_ws.close()
            if self.artifacts:
                self.artifacts.close()

    async def _receive_carrier(self, stt_ws: Any) -> None:
        try:
            async for raw in self.websocket.iter_text():
                message = json.loads(raw)
                event = message.get("event")
                if event == "start":
                    await self._handle_start(message)
                elif event == "media":
                    await self._handle_media(message, stt_ws)
                elif event == "mark":
                    self.speaking = False
                elif event == "stop":
                    if self.artifacts:
                        self.artifacts.append_event(f"{self.provider}_stop", message)
                    self.stop_event.set()
                    return
        except Exception as exc:
            logger.exception("%s receive loop failed: %s", self.provider, exc)
            self.stop_event.set()

    async def _handle_start(self, message: dict[str, Any]) -> None:
        start = message.get("start", {})
        self.stream_sid = str(start.get("streamSid") or message.get("streamSid") or "")
        self.call_sid = str(start.get("callSid") or "")
        self.artifacts = CallArtifacts(
            self.settings,
            self.call_sid or "unknown-call",
            self.scenario.id,
        )
        self.artifacts.append_event(f"{self.provider}_start", start)
        asyncio.create_task(self._maybe_send_opening_line())

    async def _handle_media(self, message: dict[str, Any], stt_ws: Any) -> None:
        payload = message.get("media", {}).get("payload", "")
        if not payload:
            return
        audio = base64.b64decode(payload)
        if self.artifacts:
            self.artifacts.write_agent_audio(audio)
        await stt_ws.send(audio)

    async def _receive_deepgram(self, stt_ws: Any) -> None:
        try:
            async for raw in stt_ws:
                if isinstance(raw, bytes):
                    continue
                data = json.loads(raw)
                transcript = _extract_transcript(data)
                if not transcript:
                    if data.get("type") == "UtteranceEnd":
                        await self._flush_agent_utterance()
                    continue
                self.last_agent_speech_at = time.monotonic()
                if data.get("is_final"):
                    self.pending_final_parts.append(transcript)
                if data.get("speech_final"):
                    await self._flush_agent_utterance()
        except Exception as exc:
            logger.exception("Deepgram receive loop failed: %s", exc)
            self.stop_event.set()

    async def _flush_agent_utterance(self) -> None:
        if not self.pending_final_parts:
            return
        text = " ".join(self.pending_final_parts).strip()
        self.pending_final_parts.clear()
        if not text:
            return
        self.transcript.append({"speaker": "agent", "text": text})
        if self.artifacts:
            self.artifacts.append_turn("agent", text)
        await self._respond_to_agent(text)

    async def _respond_to_agent(self, agent_text: str) -> None:
        if self.speaking:
            await self._interrupt_patient_audio()
        now = time.monotonic()
        if now - self.last_response_at < 1.0:
            return
        reply = await self.brain.next_reply(self.scenario, self.transcript, agent_text)
        await self._speak(reply.utterance, {"reason": reply.reason, "end_call": reply.end_call})
        if reply.end_call:
            asyncio.create_task(self._complete_call_after_delay(4.0))

    async def _interrupt_patient_audio(self) -> None:
        self.speaking = False
        if not self.stream_sid:
            return
        await self.websocket.send_json({"event": "clear", "streamSid": self.stream_sid})
        if self.artifacts:
            self.artifacts.append_event("patient_audio_interrupted", {"reason": "agent_barge_in"})

    async def _speak(self, text: str, meta: dict[str, Any] | None = None) -> None:
        if not self.stream_sid:
            return
        self.speaking = True
        self.last_response_at = time.monotonic()
        audio = await self.tts.synthesize_mulaw(text)
        payload = base64.b64encode(audio).decode("ascii")
        await self.websocket.send_json(
            {"event": "media", "streamSid": self.stream_sid, "media": {"payload": payload}}
        )
        mark_name = f"patient-{len(self.transcript) + 1}"
        await self.websocket.send_json(
            {"event": "mark", "streamSid": self.stream_sid, "mark": {"name": mark_name}}
        )
        self.transcript.append({"speaker": "patient", "text": text})
        if self.artifacts:
            self.artifacts.write_patient_audio(audio)
            self.artifacts.append_turn("patient", text, meta)

    async def _maybe_send_opening_line(self) -> None:
        await asyncio.sleep(self.settings.initial_utterance_delay_seconds)
        while not self.stop_event.is_set():
            agent_has_spoken = any(turn["speaker"] == "agent" for turn in self.transcript)
            if agent_has_spoken or self.speaking:
                return
            if time.monotonic() - self.last_agent_speech_at < OPENING_SILENCE_SECONDS:
                await asyncio.sleep(OPENING_RECHECK_SECONDS)
                continue
            await self._speak(self.scenario.opening_line, {"reason": "opening_line_timeout"})
            return

    async def _complete_call_after_delay(self, delay: float) -> None:
        await asyncio.sleep(delay)
        if not self.call_sid:
            return
        try:
            await asyncio.to_thread(complete_call, self.settings, self.call_sid)
        except Exception as exc:
            logger.warning("Could not complete %s call %s: %s", self.provider, self.call_sid, exc)

    async def _deepgram_keepalive(self, stt_ws: Any) -> None:
        while not self.stop_event.is_set():
            await asyncio.sleep(6)
            with suppress(Exception):
                await stt_ws.send(json.dumps({"type": "KeepAlive"}))

    async def _timeout_guard(self) -> None:
        await asyncio.sleep(self.settings.max_call_seconds)
        if self.artifacts:
            self.artifacts.append_event("max_call_seconds_reached")
        await self._complete_call_after_delay(0.0)
        self.stop_event.set()


async def _connect_deepgram_stt(settings: Settings) -> Any:
    headers = {"Authorization": f"Token {settings.deepgram_api_key}"}
    url = deepgram_stt_url(settings)
    try:
        return await websockets.connect(url, additional_headers=headers)
    except TypeError:
        return await websockets.connect(url, extra_headers=headers)


def _extract_transcript(data: dict[str, Any]) -> str:
    try:
        alternatives = data["channel"]["alternatives"]
        return str(alternatives[0].get("transcript", "")).strip()
    except (KeyError, IndexError, TypeError):
        return ""
