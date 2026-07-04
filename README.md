# Pretty Good AI Patient Voice Bot

Python voice bot for the Pretty Good AI engineering challenge. It calls only the
assessment number, behaves as a synthetic patient, records/transcribes calls,
and writes artifacts for the final GitHub submission.

## What it uses

- SignalWire or Twilio for outbound calls and call recordings
- SignalWire cXML Streams or Twilio Media Streams for real-time bidirectional call audio
- Deepgram for live speech-to-text and text-to-speech
- DeepSeek for the patient-dialogue brain and transcript analysis

## Safety guard

Set `PG_TARGET_NUMBER` in `.env` to the official assessment test number from
the challenge PDF. The code refuses to call any other target, and
`pgai-bot check-env` verifies that lock without printing configured phone
values.

## Setup

```bash
uv sync --extra dev
cp .env.example .env
```

Fill `.env` with local credentials:

- `VOICE_PROVIDER=signalwire` or `VOICE_PROVIDER=twilio`
- SignalWire: `SIGNALWIRE_PROJECT_ID`, `SIGNALWIRE_API_TOKEN`, `SIGNALWIRE_SPACE_URL`, `SIGNALWIRE_FROM_NUMBER`
- Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
- `PUBLIC_BASE_URL`
- `DEEPGRAM_API_KEY`
- `DEEPSEEK_API_KEY`

Do not commit `.env`.

## Expose the local server

Recommended free temporary tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the generated `https://...trycloudflare.com` URL into `PUBLIC_BASE_URL`.
You can also use ngrok if you prefer.

## Run

Terminal 1:

```bash
uv run pgai-bot check-env
uv run pgai-bot serve
```

Terminal 2:

```bash
uv run pgai-bot list-scenarios
uv run pgai-bot call --scenario appointment_simple
```

For the required 10-call run:

```bash
uv run pgai-bot call-batch --limit 10 --pause 150
```

The planned 10-call scenario set is documented in `docs/CALL_PLAN.md`. Do not
run live calls without explicit approval at action time.

## Artifacts

Call artifacts are written under:

```text
artifacts/calls/
```

Each call directory includes:

- `transcript.txt`
- `metadata.json`
- `agent-side.mp3`
- `patient-side.mp3`

Carrier recording callbacks also download call recordings when the provider
makes the recording available.

Check artifact structure after calls:

```bash
uv run pgai-bot validate-artifacts
```

## Submission checklist

- Working Python voice bot: ready
- README, architecture doc, and `.env.example`: ready
- Call plan and submission checklist: ready
- 10+ calls with transcripts and MP3 recordings: ready under `artifacts/calls/`
- Bug report with call references and evidence: ready in `BUG_REPORT.md`
- Loom walkthrough and AI-debugging screen recording: pending user action

## Bug report draft

After calls complete:

```bash
uv run pgai-bot analyze --output docs/bug_report_draft.md
```

Manually review the generated report against the recordings before submitting.

## Local tools already installed on this machine

- `uv`
- `ffmpeg`
- `cloudflared`
