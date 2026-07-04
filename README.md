# Pretty Good AI Patient Voice Bot

Python voice bot for the Pretty Good AI engineering challenge. It calls only the
assessment number, behaves as a synthetic patient, records/transcribes calls,
and writes artifacts for the final GitHub submission.

## What it uses

- Twilio Programmable Voice for outbound calls and call recordings
- Twilio Media Streams for real-time bidirectional call audio
- Deepgram for live speech-to-text and text-to-speech
- DeepSeek for the patient-dialogue brain and transcript analysis

## Safety guard

The code refuses to call anything except:

```text
+1-805-439-8008
```

Keep `PG_TARGET_NUMBER=+18054398008` in `.env`.

## Setup

```bash
uv sync --extra dev
cp .env.example .env
```

Fill `.env` with local credentials:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
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
uv run pgai-bot call-batch --limit 10 --pause 20
```

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

Twilio recording callbacks also download mixed/dual call recordings when Twilio
makes the recording available.

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
