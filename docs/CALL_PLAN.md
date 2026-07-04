# Call Plan

Use this plan after local readiness checks pass and the user explicitly approves
the live batch command at action time.

## Approved Batch Shape

```bash
uv run pgai-bot call-batch --limit 10 --pause 150
```

The batch uses the first 10 scenarios in
`src/pgai_patient_bot/data/scenarios.json`, all from the single configured
caller ID in `.env`, and the code locks the destination to the official
assessment target configured from the challenge PDF.

## Primary 10-Call Set

| Order | Scenario | Coverage |
| --- | --- | --- |
| 1 | `appointment_simple` | Basic scheduling, identity collection, date/time confirmation |
| 2 | `reschedule_existing` | Existing appointment rescheduling and conflict handling |
| 3 | `cancel_appointment` | Cancellation without unwanted rescheduling |
| 4 | `refill_metformin` | Medication refill intake and pharmacy capture |
| 5 | `insurance_question` | Insurance acceptance and verification handling |
| 6 | `weekend_edge` | Unusual closed-hours scheduling request |
| 7 | `location_parking` | Office location, accessibility, and unknown-answer handling |
| 8 | `unclear_request` | Ambiguous request and clarification behavior |
| 9 | `interruption_barge_in` | Patient correction, interruption, and turn-taking |
| 10 | `urgent_symptoms` | Medical safety escalation for potentially urgent symptoms |

## Reserve Scenarios

Use these only after another explicit approval if fewer than 10 calls qualify:

| Scenario | Coverage |
| --- | --- |
| `new_patient_registration` | New patient flow, insurance, contact capture |
| `prior_authorization` | Administrative status uncertainty and escalation |

## Quality Review

After each batch:

1. Run `uv run pgai-bot validate-artifacts`.
2. Inspect each `artifacts/calls/*/transcript.txt` for both speakers, coherent
   turn-taking, and scenario completion.
3. Listen to enough of each MP3/OGG artifact to confirm audio quality, pacing,
   and that the conversation is substantial.
4. Run `uv run pgai-bot analyze --output docs/bug_report_draft.md`.
5. Manually turn high-signal findings into `BUG_REPORT.md` with severity, call
   reference, timestamp/evidence, what happened, why it matters, and expected
   behavior.
