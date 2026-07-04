# Live Test Runbook

Use this when you are ready to place real assessment calls.

## 1. Fill `.env`

Required values:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
- `DEEPGRAM_API_KEY`
- `DEEPSEEK_API_KEY`

Keep:

```text
PG_TARGET_NUMBER=+18054398008
```

The app refuses any other target number.

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

```bash
uv run pgai-bot call-batch --limit 10 --pause 20
```

## 6. Draft bug report

```bash
uv run pgai-bot analyze --output docs/bug_report_draft.md
```

Review the draft manually against recordings and transcripts.

## Final blockers before live calls

- Twilio must be upgraded or otherwise allowed to call the assessment number.
- `TWILIO_FROM_NUMBER` must be a rented Twilio Voice number or verified caller ID.
- Deepgram and DeepSeek API keys must be present in `.env`.
- You must sign off before any real call is placed.
