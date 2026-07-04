from __future__ import annotations

from urllib.parse import urlencode

import httpx

from .config import Settings


class DeepgramTTS:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def synthesize_mulaw(self, text: str) -> bytes:
        query = urlencode(
            {
                "model": self.settings.deepgram_tts_model,
                "encoding": "mulaw",
                "sample_rate": "8000",
                "container": "none",
            }
        )
        url = f"https://api.deepgram.com/v1/speak?{query}"
        headers = {
            "Authorization": f"Token {self.settings.deepgram_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json={"text": text})
            response.raise_for_status()
            return response.content


def deepgram_stt_url(settings: Settings) -> str:
    query = urlencode(
        {
            "model": settings.deepgram_stt_model,
            "language": "en-US",
            "encoding": "mulaw",
            "sample_rate": "8000",
            "channels": "1",
            "interim_results": "true",
            "endpointing": "350",
            "utterance_end_ms": "1000",
            "smart_format": "true",
        }
    )
    return f"wss://api.deepgram.com/v1/listen?{query}"
