from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings
from .prompts import BUG_ANALYSIS_PROMPT, build_patient_messages
from .scenarios import Scenario


@dataclass(frozen=True)
class PatientReply:
    utterance: str
    end_call: bool
    reason: str


class DeepSeekClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.4) -> str:
        url = f"{self.settings.deepseek_base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


class PatientBrain:
    def __init__(self, settings: Settings) -> None:
        self.client = DeepSeekClient(settings)

    async def next_reply(
        self,
        scenario: Scenario,
        transcript: list[dict[str, str]],
        last_agent_utterance: str,
    ) -> PatientReply:
        messages = build_patient_messages(scenario, transcript, last_agent_utterance)
        raw = await self.client.chat(messages, temperature=0.45)
        try:
            parsed = _extract_json_object(raw)
            utterance = str(parsed.get("utterance", "")).strip()
            end_call = bool(parsed.get("end_call", False))
            reason = str(parsed.get("reason", "")).strip()
        except (json.JSONDecodeError, TypeError, ValueError):
            utterance = raw.strip().splitlines()[0][:220]
            end_call = False
            reason = "Model returned non-JSON; used first line as fallback."
        if not utterance:
            utterance = "Sorry, could you say that one more time?"
        return PatientReply(utterance=utterance, end_call=end_call, reason=reason)


class TranscriptAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.client = DeepSeekClient(settings)

    async def analyze(self, transcript_markdown: str) -> str:
        return await self.client.chat(
            [
                {"role": "system", "content": BUG_ANALYSIS_PROMPT},
                {"role": "user", "content": transcript_markdown},
            ],
            temperature=0.2,
        )
