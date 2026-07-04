# Architecture

This bot is a small FastAPI service that SignalWire or Twilio calls during an
outbound phone call. The carrier starts a bidirectional media stream to
`/{provider}/media`; the server forwards the remote agent's `mulaw/8000` audio
to Deepgram streaming STT, sends final agent utterances to a DeepSeek-backed
patient brain, converts the patient reply to `mulaw/8000` with Deepgram TTS, and
streams that audio back to the carrier. The CLI creates calls only to the Pretty
Good AI assessment number configured in `.env` and attaches provider-specific
status and recording callbacks.

The key design choice is to keep the real-time loop simple and observable:
scenario prompts are static JSON, secrets are environment variables, every
conversation turn is written immediately to a call artifact directory, and
provider-specific code is isolated behind small adapters. That makes it easier
to iterate after listening to early calls, which matters more for this challenge
than production-grade infrastructure.
