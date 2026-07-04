# Live Test Runbook

Use this when you are ready to place real assessment calls.

## 1. Fill `.env`

Required values:

- `VOICE_PROVIDER`
- SignalWire: `SIGNALWIRE_PROJECT_ID`, `SIGNALWIRE_API_TOKEN`, `SIGNALWIRE_SPACE_URL`, `SIGNALWIRE_FROM_NUMBER`
- Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
- `PUBLIC_BASE_URL`
- `DEEPGRAM_API_KEY`
- `DEEPSEEK_API_KEY`

Set `PG_TARGET_NUMBER` to the official assessment number from the challenge PDF.
The app refuses any other target number and does not print configured phone
values during readiness checks.

## 2. Start the tunnel

In terminal 1:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the generated `https://...trycloudflare.com` URL into `.env` as:

```text
PUBLIC_BASE_URL=https://...trycloudflare.com
```

## 3. Start the bot server

In terminal 2:

```bash
uv run pgai-bot check-env
uv run pgai-bot serve
```

## 4. Place one smoke-test call

In terminal 3:

```bash
uv run pgai-bot call --scenario appointment_simple
```

Listen to the resulting recording before running the batch.

## 5. Run the required batch

The planned primary batch is documented in `docs/CALL_PLAN.md`.

```bash
uv run pgai-bot call-batch --limit 10 --pause 150
```

## 6. Validate artifacts

```bash
uv run pgai-bot validate-artifacts
```

Review each transcript and enough audio to confirm call quality, both-side
conversation, turn-taking, and scenario coverage.

## 7. Draft bug report

```bash
uv run pgai-bot analyze --output docs/bug_report_draft.md
```

Review the draft manually against recordings and transcripts.

## Final blockers before live calls

- The local server and public tunnel must both pass `/health`.
- The public voice webhook must return a stream URL using the active tunnel.
- The configured caller number must be the single caller ID used for all calls.
- Deepgram and DeepSeek API keys must be present in `.env`.
- You must explicitly sign off before any real call is placed.
