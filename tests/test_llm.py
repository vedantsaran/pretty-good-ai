from pgai_patient_bot.llm import PatientReply, _force_end_after_turn_budget
from pgai_patient_bot.scenarios import get_scenario


def test_force_end_after_turn_budget() -> None:
    scenario = get_scenario("appointment_simple")
    transcript = [
        {"speaker": "patient", "text": "patient turn"}
        for _ in range(scenario.max_turns)
    ]
    reply = PatientReply("Please call me back with the next step.", False, "looping")

    forced = _force_end_after_turn_budget(scenario, transcript, reply)

    assert forced.end_call
    assert forced.utterance.endswith("Thank you, goodbye.")
    assert "turn budget" in forced.reason


def test_force_end_after_turn_budget_keeps_short_conversation_open() -> None:
    scenario = get_scenario("appointment_simple")
    reply = PatientReply("Tuesday morning works.", False, "progress")

    forced = _force_end_after_turn_budget(scenario, [], reply)

    assert forced == reply
