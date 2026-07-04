from urllib.parse import parse_qs

from pgai_patient_bot.telephony import STATUS_CALLBACK_EVENTS, _encode_signalwire_form


def test_encode_signalwire_form_preserves_duplicate_callback_events() -> None:
    body = _encode_signalwire_form(
        [("To", "target"), *[("StatusCallbackEvent", event) for event in STATUS_CALLBACK_EVENTS]]
    )

    parsed = parse_qs(body.decode("ascii"))

    assert parsed["To"] == ["target"]
    assert parsed["StatusCallbackEvent"] == STATUS_CALLBACK_EVENTS
