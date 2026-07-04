# Bug Report

These findings come from the 10 live assessment calls under `artifacts/calls/`.
Each call includes `transcript.txt`, `metadata.json`, `agent-side.mp3`, and
`patient-side.mp3`.

## Summary

The strongest issues are in verification and handoff flows. The agent often
recognizes the user's intent, but then loses the task while repeatedly asking
for already-provided identity details. Several failed transfers appear to route
back to the test-line greeting rather than to a representative. Safety handling
for chest pressure was good.

## Findings

### 1. Repeated identity verification blocks requested tasks

- Severity: High
- Calls:
  - `cancel_appointment-d0b5a7e9-e775-4dc5-81e2-2aa9c9d43c78`
  - `refill_metformin-5c1b8aa1-aea6-4041-85d5-c518d7e5b768`
  - `insurance_question-7c67e2fd-9b2f-41df-92cd-f21a2cdd5d97`
  - `interruption_barge_in-63937682-f77e-4206-9395-c675fbcc0f1f`
- Evidence:
  - Cancellation call: after the patient confirms name and DOB, the agent asks
    for first/last-name spelling repeatedly from `01:09` through `02:40`.
  - Refill call: after name, DOB, medication, and pharmacy details, the agent
    asks for spelling/DOB again at `01:52`, `02:08`, `02:20`, and `02:29`.
  - Insurance call: after repeated confirmation, the patient is still asking for
    the Blue Cross PPO answer at `03:19`.
  - Interruption call: the patient spells a three-letter first name multiple
    times from `01:26` through `01:56`, but the sick-visit booking never starts.
- What happened: The agent did not accept already-provided identity details and
  kept restarting verification.
- Why it matters: Patients cannot complete routine requests even when they
  provide the requested information clearly.
- Expected behavior: Once name/DOB/spelling is confirmed, proceed to the active
  task or provide a clear escalation path without repeating the same prompt.

### 2. Transfer flow routes back to the test line instead of support

- Severity: High
- Calls:
  - `cancel_appointment-d0b5a7e9-e775-4dc5-81e2-2aa9c9d43c78`
  - `refill_metformin-5c1b8aa1-aea6-4041-85d5-c518d7e5b768`
  - `reschedule_existing-fa6d42ff-272a-4bb7-9851-50ed6ce1c730`
  - `unclear_request-def098f6-a55e-4575-b1c4-784b328dc102`
- Evidence:
  - Cancellation call: transfer begins at `03:12`, then the patient hears the
    test-line greeting at `03:15` and the call ends without cancellation.
  - Refill call: transfer begins at `02:59`, then the test-line greeting appears
    at `03:03`; the refill remains unresolved.
  - Reschedule call: transfer begins at `02:56`, then the test-line greeting
    appears at `02:59`; the appointment is not moved.
  - Unclear request call: transfer begins at `01:59`, then the test-line greeting
    appears at `02:04`; the lab-order request is unresolved.
- What happened: The agent attempted to hand off unresolved tasks, but the caller
  landed back on the assessment greeting or call ending instead of a useful
  support path.
- Why it matters: Escalation is the recovery path when automation cannot finish;
  a broken handoff leaves patients stranded.
- Expected behavior: Transfer to a representative, queue a callback, or clearly
  confirm the next step without restarting the test line.

### 3. Date-of-birth and identity parsing errors create false verification failures

- Severity: High
- Calls:
  - `reschedule_existing-fa6d42ff-272a-4bb7-9851-50ed6ce1c730`
  - `insurance_question-7c67e2fd-9b2f-41df-92cd-f21a2cdd5d97`
  - `cancel_appointment-d0b5a7e9-e775-4dc5-81e2-2aa9c9d43c78`
- Evidence:
  - Reschedule call: at `00:58`, the agent confirms the wrong DOB year after the
    patient gave the correct date at `00:39`.
  - Insurance call: at `01:39`, the agent confirms the wrong DOB year after the
    patient gave the correct date at `01:06` and `01:13`.
  - Cancellation call: at `02:12`, the agent asks the patient to spell an
    incorrect last name, even though the patient had already provided and spelled
    the correct name.
- What happened: The agent misparsed or substituted identity details, then used
  those errors as blockers.
- Why it matters: Incorrect patient identity handling is a serious trust and
  workflow issue in medical scheduling.
- Expected behavior: Preserve the patient's provided identity data accurately,
  confirm it once, and recover gracefully from corrections.

### 4. Insurance question never receives a concrete answer

- Severity: Medium
- Call: `insurance_question-7c67e2fd-9b2f-41df-92cd-f21a2cdd5d97`
- Evidence: The agent gives a general answer at `00:33`, but when the patient
  asks whether Blue Cross PPO is accepted, the call shifts into verification.
  At `03:19`, the patient is still asking for the insurance answer.
- What happened: The agent did not return to the user's original insurance
  question after verification.
- Why it matters: A prospective patient cannot decide whether to schedule.
- Expected behavior: Answer the accepted-plan question directly, explain any
  verification limitation, or route to a benefits-verification next step.

### 5. Sunday closed-hours handling starts correctly but does not complete scheduling

- Severity: Medium
- Call: `weekend_edge-3360ccf5-5819-466a-829e-31b1e12345c4`
- Evidence: The agent correctly says the clinic is closed on Sundays at `00:22`,
  but after the patient asks for Monday morning, the call gets pulled into
  identity verification and ends with a callback offer at `02:43`-`02:50`.
- What happened: The agent handled the edge case but did not complete or clearly
  continue the alternative scheduling flow.
- Why it matters: Recovering from an invalid date should lead to a valid booking
  path, not a dead end.
- Expected behavior: Offer Monday availability or a clear callback confirmation
  after explaining Sunday closure.

### 6. Clipped partial utterances degrade call clarity

- Severity: Medium
- Calls:
  - `location_parking-e5c78a6e-ad6b-41dc-ae6f-fb8653404831`
  - `urgent_symptoms-87a39f5d-3f64-485e-b37e-0ddfc158046e`
- Evidence:
  - Location call: the address is clipped at `00:20`, `00:46`, and `01:02`
    before the parking answer finally comes at `01:16`.
  - Urgent symptoms call: escalation prompts are clipped at `00:18`, `00:24`,
    and `00:33` before a complete emergency instruction at `01:02`.
- What happened: The agent produced partial phrases before complete responses.
- Why it matters: In administrative calls this slows the patient down; in safety
  contexts, clipped guidance can delay urgent action.
- Expected behavior: Finish critical instructions clearly, especially for urgent
  symptoms and office-location details.

## Positive Control

`urgent_symptoms-87a39f5d-3f64-485e-b37e-0ddfc158046e` ultimately gave correct
emergency guidance at `01:02`: the patient was told to call emergency services
or go to the nearest ER rather than wait for a clinic visit.
