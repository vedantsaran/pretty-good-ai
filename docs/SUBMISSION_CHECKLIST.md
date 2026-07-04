# Submission Checklist

## Code And Docs

- [x] Python voice bot implementation
- [x] Destination lock to the official assessment target configured from the PDF
- [x] Diverse realistic patient scenarios in
      `src/pgai_patient_bot/data/scenarios.json`
- [x] README with setup, run, artifact, and safety instructions
- [x] Architecture doc with system overview and design choices
- [x] `.env.example` with required variables and no secrets
- [x] Local tests and lint checks
- [x] Artifact validator command

## Live Call Evidence

- [x] 10+ qualifying calls completed
- [x] Each submitted call has `transcript.txt`
- [x] Each transcript includes both agent and patient turns
- [x] Each submitted call has MP3/OGG audio artifacts
- [x] `agent-side.mp3` is the full-duration remote-agent side;
      `patient-side.mp3` is the isolated synthesized-patient speech stream
- [x] Calls are substantial and lucid; several are bug-heavy or slightly over
      the typical target because the assessed agent looped verification
- [x] Scenarios cover scheduling, rescheduling/canceling, refills, office or
      location or insurance questions, unclear requests, interruptions, and
      unusual edge cases

## Bug Report

- [x] `BUG_REPORT.md` contains only useful, high-signal issues
- [x] Each bug includes severity
- [x] Each bug includes call reference and timestamp/evidence where possible
- [x] Each bug says what happened, why it matters, and expected behavior

## User-Owned Submission Items

- [x] Public GitHub repository created and pushed:
      `https://github.com/vedantsaran/pretty-good-ai`
- [ ] Submission form:
      `https://forms.gle/sdnbrJX2XbgZeQaY6`
- [ ] Loom walkthrough
- [ ] AI-debugging screen recording
