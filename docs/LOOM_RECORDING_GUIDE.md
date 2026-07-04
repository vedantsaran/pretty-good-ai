# Loom Recording Guide

Keep the recording under 5 minutes if possible. Do not show `.env`, API keys,
SignalWire credentials, the target assessment number, or the configured caller
ID on screen.

## 1. Open With The Submission

Show the public repository:

```text
https://github.com/vedantsaran/pretty-good-ai
```

Say that the bot is a Python patient voice simulator that made real assessment
calls, recorded both sides, transcribed them, and produced a bug report.

## 2. Show The Main Deliverables

Open these files or folders in GitHub:

- `README.md`
- `ARCHITECTURE.md`
- `BUG_REPORT.md`
- `artifacts/calls/`
- `docs/SUBMISSION_CHECKLIST.md`

Call out that `artifacts/calls/` contains 10 submitted call folders and each
folder has:

- `transcript.txt`
- `metadata.json`
- `agent-side.mp3`
- `patient-side.mp3`

For playback, use `agent-side.mp3` as the full-duration remote-agent side.
Mention that `patient-side.mp3` is the isolated synthesized-patient speech
stream, so it is shorter because silence between patient utterances is omitted.

## 3. Show One Complete Call

Use this call as the clean example:

```text
artifacts/calls/appointment_simple-605be7ff-3872-46f2-b6b4-d509876a8d79/
```

Show the transcript lines where the patient asks for a follow-up appointment,
the agent offers Tuesday availability, the patient chooses 11 AM, and the agent
confirms the appointment.

Frame the bug-heavy calls as failure demonstrations, not successful task
completions. For example, the insurance call hit the configured call-time limit
while the patient was still trying to get the Blue Cross PPO answer; that is the
evidence behind the unresolved-insurance bug report item.

## 4. Show Validation

In a terminal, run:

```bash
uv run pytest
uv run ruff check .
uv run pgai-bot validate-artifacts
```

Say that tests pass, lint passes, and the artifact validator confirms 10
structurally complete calls.

## 5. Show AI-Assisted Debugging

Use a short narrative around the actual iteration:

1. Ask AI to review the repo against the challenge requirements.
2. Ask AI to add SignalWire support while preserving Twilio support.
3. Ask AI to enforce the official assessment-number lock at the telephony
   boundary.
4. Ask AI to add artifact validation and tests.
5. Ask AI to review the final artifacts and bug report for submission
   readiness.

Example prompts to show on screen:

```text
Review this Python voice bot repo against the Pretty Good AI challenge
requirements. Identify blockers before live calls, especially telephony config,
target-number safety, artifact recording, and docs.
```

```text
The app needs to support SignalWire for live calls, but the current
implementation is Twilio-oriented. Inspect the call creation path and propose a
minimal provider abstraction that keeps Twilio support while adding SignalWire.
```

```text
Implement the provider abstraction and make sure outbound calls still enforce
the official assessment target lock at the telephony boundary. Do not print
secrets or configured phone numbers.
```

```text
Add tests for provider selection, target-lock enforcement, and artifact
validation. Run the tests and fix any failures.
```

```text
Review the completed repo for submission readiness. Confirm that artifacts,
README, bug report, architecture notes, and validation commands are all
present.
```

## 6. Close

End by saying that the remaining action is submitting the Google Form with the
GitHub URL, Loom URL, and the single configured caller ID in E.164 format.
