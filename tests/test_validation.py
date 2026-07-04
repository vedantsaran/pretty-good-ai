import json
from pathlib import Path

from pgai_patient_bot.validation import validate_call_artifacts


def _write_complete_call(root: Path, name: str) -> None:
    call_dir = root / name
    call_dir.mkdir(parents=True)
    (call_dir / "metadata.json").write_text(
        json.dumps(
            {
                "turns": [
                    {"speaker": "agent", "text": "How can I help?"},
                    {"speaker": "patient", "text": "I need an appointment."},
                ]
            }
        ),
        encoding="utf-8",
    )
    (call_dir / "transcript.txt").write_text(
        "[00:01.00] agent: How can I help?\n"
        "[00:02.00] patient: I need an appointment.\n",
        encoding="utf-8",
    )
    (call_dir / "agent-side.mp3").write_bytes(b"agent")
    (call_dir / "patient-side.mp3").write_bytes(b"patient")


def test_validate_call_artifacts_accepts_complete_calls(tmp_path: Path) -> None:
    for index in range(2):
        _write_complete_call(tmp_path, f"call-{index}")

    result = validate_call_artifacts(tmp_path, min_calls=2)

    assert result.ok
    assert len(result.qualifying_call_dirs) == 2
    assert result.issues == []


def test_validate_call_artifacts_reports_missing_audio(tmp_path: Path) -> None:
    _write_complete_call(tmp_path, "call-1")
    (tmp_path / "call-1" / "agent-side.mp3").unlink()

    result = validate_call_artifacts(tmp_path, min_calls=1)

    assert not result.ok
    assert [issue.message for issue in result.issues] == [
        "Missing agent-side MP3/OGG audio.",
        "Expected at least 1 structurally complete calls, found 0.",
    ]
