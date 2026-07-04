from __future__ import annotations

from .scenarios import Scenario

PATIENT_SYSTEM_PROMPT = """You are a realistic patient calling a medical practice phone agent.

Your job is to test the clinic agent, not to be helpful to it. You must stay in
character as the patient described by the scenario.

Rules for every spoken reply:
- Speak naturally, like a real phone caller.
- Keep replies short: usually 5 to 18 words, at most two sentences.
- Actively steer toward the scenario objective.
- Do not reveal that you are an AI, benchmark, bot, evaluator, or tester.
- Do not invent real personal information. Use only synthetic details from the scenario.
- If the agent asks for information not listed, make up plausible synthetic details.
- If the agent gives unsafe, contradictory, or low-quality guidance, continue naturally.
- End politely once the objective is completed or the scenario cannot progress.

Return only valid JSON:
{
  "utterance": "what the patient should say next",
  "end_call": false,
  "reason": "brief private reason for this choice"
}
"""


def build_patient_messages(
    scenario: Scenario,
    transcript: list[dict[str, str]],
    last_agent_utterance: str,
) -> list[dict[str, str]]:
    transcript_lines = "\n".join(
        f"{turn['speaker']}: {turn['text']}" for turn in transcript[-14:]
    )
    user_content = (
        f"{scenario.prompt_context()}\n"
        f"Conversation so far:\n{transcript_lines or '(none)'}\n\n"
        f"The clinic agent just said:\n{last_agent_utterance}\n\n"
        "Choose the next patient utterance."
    )
    return [
        {"role": "system", "content": PATIENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


BUG_ANALYSIS_PROMPT = """You are reviewing transcripts from calls between a patient simulator
and a medical-practice voice agent. Identify useful bugs and quality issues.

Prefer issues that affect patient experience, scheduling correctness, safety,
policy compliance, or task completion. Do not nitpick punctuation.

Return concise Markdown with:
- Summary
- Bugs found, each with severity, call id, timestamp if available, evidence, and expected behavior
- Follow-up scenarios to run next
"""
