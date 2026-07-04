from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from twilio.rest import Client

from .config import ConfigError, Settings
from .scenarios import Scenario

STATUS_CALLBACK_EVENTS = ["initiated", "ringing", "answered", "completed"]
FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


@dataclass(frozen=True)
class StartedCall:
    sid: str
    provider: str


def provider_path(settings: Settings) -> str:
    settings.require_supported_voice_provider()
    return settings.voice_provider


def callback_url(settings: Settings, path: str, query: dict[str, str] | None = None) -> str:
    url = f"{settings.public_base_url}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def start_assessment_call(settings: Settings, scenario: Scenario) -> StartedCall:
    provider = provider_path(settings)
    settings.require_safe_call_target()
    if provider == "signalwire":
        return _start_signalwire_call(settings, scenario)
    return _start_twilio_call(settings, scenario)


def complete_call(settings: Settings, call_sid: str) -> None:
    provider = provider_path(settings)
    if provider == "signalwire":
        _complete_signalwire_call(settings, call_sid)
        return

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    client.calls(call_sid).update(status="completed")


def recording_auth(settings: Settings) -> tuple[str, str]:
    provider = provider_path(settings)
    if provider == "signalwire":
        return settings.signalwire_project_id, settings.signalwire_api_token
    return settings.twilio_account_sid, settings.twilio_auth_token


def _start_twilio_call(settings: Settings, scenario: Scenario) -> StartedCall:
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    kwargs: dict[str, Any] = {
        "to": settings.pg_target_number,
        "from_": settings.twilio_from_number,
        "url": callback_url(settings, "twilio/voice", {"scenario": scenario.id}),
        "method": "POST",
        "status_callback": callback_url(settings, "twilio/status"),
        "status_callback_event": STATUS_CALLBACK_EVENTS,
        "status_callback_method": "POST",
    }
    if settings.record_calls:
        kwargs.update(
            {
                "record": True,
                "recording_channels": "dual",
                "recording_status_callback": callback_url(settings, "twilio/recording"),
                "recording_status_callback_method": "POST",
            }
        )
    call = client.calls.create(**kwargs)
    return StartedCall(sid=call.sid, provider="twilio")


def _start_signalwire_call(settings: Settings, scenario: Scenario) -> StartedCall:
    data: list[tuple[str, str]] = [
        ("To", settings.pg_target_number),
        ("From", settings.signalwire_from_number),
        ("Url", callback_url(settings, "signalwire/voice", {"scenario": scenario.id})),
        ("Method", "POST"),
        ("StatusCallback", callback_url(settings, "signalwire/status")),
        ("StatusCallbackMethod", "POST"),
    ]
    data.extend(("StatusCallbackEvent", event) for event in STATUS_CALLBACK_EVENTS)
    if settings.record_calls:
        data.extend(
            [
                ("Record", "true"),
                ("RecordingTrack", "both"),
                ("RecordingStatusCallback", callback_url(settings, "signalwire/recording")),
                ("RecordingStatusCallbackMethod", "POST"),
            ]
        )

    payload = _signalwire_post(settings, "Calls", data)
    sid = str(payload.get("sid") or payload.get("Sid") or "")
    if not sid:
        raise ConfigError("SignalWire did not return a call SID.")
    return StartedCall(sid=sid, provider="signalwire")


def _complete_signalwire_call(settings: Settings, call_sid: str) -> None:
    _signalwire_post(settings, f"Calls/{call_sid}", [("Status", "completed")])


def _signalwire_post(
    settings: Settings,
    path: str,
    data: list[tuple[str, str]],
) -> dict[str, Any]:
    base_url = (
        f"https://{settings.signalwire_space_url}/api/laml/2010-04-01/"
        f"Accounts/{settings.signalwire_project_id}/{path}"
    )
    auth = (settings.signalwire_project_id, settings.signalwire_api_token)
    body = _encode_signalwire_form(data)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{base_url}.json", content=body, headers=FORM_HEADERS, auth=auth)
        if response.status_code == 404:
            response = client.post(base_url, content=body, headers=FORM_HEADERS, auth=auth)
        response.raise_for_status()
    if not response.content:
        return {}
    try:
        payload = response.json()
    except ValueError as exc:
        raise ConfigError("SignalWire returned a non-JSON response.") from exc
    if not isinstance(payload, dict):
        raise ConfigError("SignalWire returned an unexpected response shape.")
    return payload


def _encode_signalwire_form(data: list[tuple[str, str]]) -> bytes:
    return urlencode(data).encode("ascii")
