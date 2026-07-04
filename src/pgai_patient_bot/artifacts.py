from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .config import Settings
from .telephony import recording_auth

logger = logging.getLogger(__name__)


@dataclass
class CallArtifacts:
    settings: Settings
    call_sid: str
    scenario_id: str
    started_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        safe_call_sid = self.call_sid.replace("/", "_")
        self.call_dir = self.settings.artifact_dir / f"{self.scenario_id}-{safe_call_sid}"
        self.raw_dir = self.call_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.turns: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.agent_audio_path = self.raw_dir / "agent.ulaw"
        self.patient_audio_path = self.raw_dir / "patient.ulaw"
        self.metadata_path = self.call_dir / "metadata.json"
        self.transcript_path = self.call_dir / "transcript.txt"
        self.agent_audio = self.agent_audio_path.open("ab")
        self.patient_audio = self.patient_audio_path.open("ab")

    def append_event(self, event: str, payload: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "time": round(time.time() - self.started_at, 3),
                "event": event,
                "payload": payload or {},
            }
        )

    def append_turn(self, speaker: str, text: str, meta: dict[str, Any] | None = None) -> None:
        self.turns.append(
            {
                "time": round(time.time() - self.started_at, 3),
                "speaker": speaker,
                "text": text.strip(),
                "meta": meta or {},
            }
        )
        self.write_transcript()

    def write_agent_audio(self, payload: bytes) -> None:
        self.agent_audio.write(payload)

    def write_patient_audio(self, payload: bytes) -> None:
        self.patient_audio.write(payload)

    def write_transcript(self) -> None:
        lines = [
            f"Call SID: {self.call_sid}",
            f"Scenario: {self.scenario_id}",
            "",
        ]
        for turn in self.turns:
            timestamp = _format_time(float(turn["time"]))
            lines.append(f"[{timestamp}] {turn['speaker']}: {turn['text']}")
        self.transcript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def close(self) -> None:
        self.agent_audio.close()
        self.patient_audio.close()
        self.write_transcript()
        self.metadata_path.write_text(
            json.dumps(
                {
                    "call_sid": self.call_sid,
                    "scenario_id": self.scenario_id,
                    "started_at_epoch": self.started_at,
                    "duration_seconds": round(time.time() - self.started_at, 3),
                    "turns": self.turns,
                    "events": self.events,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self._convert_raw_audio()

    def _convert_raw_audio(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.append_event("ffmpeg_missing", {"message": "Install ffmpeg to convert raw audio."})
            return
        for source, destination in [
            (self.agent_audio_path, self.call_dir / "agent-side.mp3"),
            (self.patient_audio_path, self.call_dir / "patient-side.mp3"),
        ]:
            if not source.exists() or source.stat().st_size == 0:
                continue
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "mulaw",
                    "-ar",
                    "8000",
                    "-ac",
                    "1",
                    "-i",
                    str(source),
                    str(destination),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def _format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes:02d}:{remaining:05.2f}"


async def download_call_recording(
    settings: Settings,
    recording_url: str,
    recording_sid: str,
    call_sid: str,
) -> Path | None:
    destination_dir = settings.artifact_dir / f"recordings-{call_sid}"
    destination_dir.mkdir(parents=True, exist_ok=True)
    url = recording_url
    if not url.endswith(".mp3"):
        url = f"{url}.mp3"
    destination = destination_dir / f"{recording_sid}.mp3"
    auth = recording_auth(settings)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            url,
            auth=auth,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Could not download provider recording %s for call %s: HTTP %s",
                recording_sid,
                call_sid,
                exc.response.status_code,
            )
            return None
        destination.write_bytes(response.content)
    return destination


download_twilio_recording = download_call_recording
