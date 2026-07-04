from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from contextlib import suppress
from typing import Any

import websockets
from fastapi import BackgroundTasks, FastAPI, Query, Request, Response, WebSocket
from twilio.rest import Client

from .artifacts import CallArtifacts, download_twilio_recording
from .config import Settings, assert_ready_for_server, load_settings
from .deepgram import DeepgramTTS, deepgram_stt_url
from .llm import PatientBrain
from .scenarios import get_scenario

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="PGAI Patient Bot")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/twilio/voice")
    async def twilio_voice(scenario: str = Query(...)) -> Response:
        assert_ready_for_server(settings)
        get_scenario(scenario)
        stream_url = f"{settings.public_ws_base_url}/twilio/media?scenario={scenario}"
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Connect>"
            f'<Stream url="{stream_url}" />'
            "</Connect>"
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")

    @app.post("/twilio/status")
    async def twilio_status(request: Request) -> dict[str, str]:
        form = await request.form()
        logger.info("Twilio status callback: %s", dict(form))
        return {"status": "ok"}

    @app.post("/twilio/recording")
    async def twilio_recording(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
        form = await request.form()
        recording_url = str(form.get("RecordingUrl", ""))
        recording_sid = str(form.get("RecordingSid", ""))
        call_sid = str(form.get("CallSid", ""))
        if recording_url and recording_sid and call_sid:
            background_tasks.add_task(
                download_twilio_recording,
                settings,
                recording_url,
                recording_sid,
                call_sid,
            )
        return {"status": "ok"}

    @app.websocket("/twilio/media")
    async def twilio_media(websocket: WebSocket, scenario: str = Query(...)) -> None:
        assert_ready_for_server(settings)
        session = TwilioMediaSession(websocket, settings, scenario)
        await session.run()

    return app


app = create_app()


class TwilioMediaSession:
    def __init__(self, websocket: WebSocket, settings: Settings, scenario_id: str) -> None:
        self.websocket = websocket
        self.settings = settings
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

    async def run(self) -> None:
        await self.websocket.accept()
        stt_ws = await _connect_deepgram_stt(self.settings)
        tasks = [
            asyncio.create_task(self._receive_twilio(stt_ws)),
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

    async def _receive_twilio(self, stt_ws: Any) -> None:
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
                        self.artifacts.append_event("twilio_stop", message)
                    self.stop_event.set()
                    return
        except Exception as exc:
            logger.exception("Twilio receive loop failed: %s", exc)
            self.stop_event.set()

    async def _handle_start(self, message: dict[str, Any]) -> None:
        start = message.get("start", {})
        self.stream_sid = str(start.get("streamSid") or message.get("streamSid") or "")
        self.call_sid = str(start.get("callSid") or "")
        self.artifacts = CallArtifacts(self.settings, self.call_sid or "unknown-call", self.scenario.id)
        self.artifacts.append_event("twilio_start", start)
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
            return
        now = time.monotonic()
        if now - self.last_response_at < 1.0:
            return
        reply = await self.brain.next_reply(self.scenario, self.transcript, agent_text)
        await self._speak(reply.utterance, {"reason": reply.reason, "end_call": reply.end_call})
        if reply.end_call:
            asyncio.create_task(self._complete_call_after_delay(4.0))

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
        agent_has_spoken = any(turn["speaker"] == "agent" for turn in self.transcript)
        if not agent_has_spoken and not self.speaking and not self.stop_event.is_set():
            await self._speak(self.scenario.opening_line, {"reason": "opening_line_timeout"})

    async def _complete_call_after_delay(self, delay: float) -> None:
        await asyncio.sleep(delay)
        if not self.call_sid:
            return
        try:
            client = Client(self.settings.twilio_account_sid, self.settings.twilio_auth_token)
            client.calls(self.call_sid).update(status="completed")
        except Exception as exc:
            logger.warning("Could not complete Twilio call %s: %s", self.call_sid, exc)

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
