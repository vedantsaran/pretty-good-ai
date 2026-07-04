from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactIssue:
    call_dir: Path | None
    message: str


@dataclass(frozen=True)
class ArtifactValidationResult:
    artifact_dir: Path
    min_calls: int
    call_dirs: list[Path]
    qualifying_call_dirs: list[Path]
    issues: list[ArtifactIssue]

    @property
    def ok(self) -> bool:
        return not self.issues and len(self.qualifying_call_dirs) >= self.min_calls


def validate_call_artifacts(artifact_dir: Path, min_calls: int = 10) -> ArtifactValidationResult:
    call_dirs = _call_dirs(artifact_dir)
    issues: list[ArtifactIssue] = []
    qualifying: list[Path] = []

    if len(call_dirs) < min_calls:
        issues.append(
            ArtifactIssue(
                None,
                f"Expected at least {min_calls} call artifact directories, found {len(call_dirs)}.",
            )
        )

    for call_dir in call_dirs:
        call_issues = _validate_call_dir(call_dir)
        if call_issues:
            issues.extend(call_issues)
        else:
            qualifying.append(call_dir)

    if len(qualifying) < min_calls:
        issues.append(
            ArtifactIssue(
                None,
                f"Expected at least {min_calls} structurally complete calls, found {len(qualifying)}.",
            )
        )

    return ArtifactValidationResult(
        artifact_dir=artifact_dir,
        min_calls=min_calls,
        call_dirs=call_dirs,
        qualifying_call_dirs=qualifying,
        issues=issues,
    )


def _call_dirs(artifact_dir: Path) -> list[Path]:
    if not artifact_dir.exists():
        return []
    return sorted(
        path
        for path in artifact_dir.iterdir()
        if path.is_dir() and not path.name.startswith("recordings-")
    )


def _validate_call_dir(call_dir: Path) -> list[ArtifactIssue]:
    issues: list[ArtifactIssue] = []
    metadata_path = call_dir / "metadata.json"
    transcript_path = call_dir / "transcript.txt"

    metadata = _read_metadata(metadata_path)
    if metadata is None:
        issues.append(ArtifactIssue(call_dir, "Missing or invalid metadata.json."))
    elif not _metadata_has_both_speakers(metadata):
        issues.append(ArtifactIssue(call_dir, "metadata.json does not contain both speakers."))

    if not transcript_path.exists():
        issues.append(ArtifactIssue(call_dir, "Missing transcript.txt."))
    elif not _transcript_has_both_speakers(transcript_path):
        issues.append(ArtifactIssue(call_dir, "transcript.txt does not contain both speakers."))

    if not _audio_exists(call_dir, "agent-side"):
        issues.append(ArtifactIssue(call_dir, "Missing agent-side MP3/OGG audio."))
    if not _audio_exists(call_dir, "patient-side"):
        issues.append(ArtifactIssue(call_dir, "Missing patient-side MP3/OGG audio."))

    return issues


def _read_metadata(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _metadata_has_both_speakers(metadata: dict[str, Any]) -> bool:
    turns = metadata.get("turns")
    if not isinstance(turns, list):
        return False
    speakers = {str(turn.get("speaker", "")).lower() for turn in turns if isinstance(turn, dict)}
    return {"agent", "patient"}.issubset(speakers)


def _transcript_has_both_speakers(path: Path) -> bool:
    text = path.read_text(encoding="utf-8").lower()
    return "agent:" in text and "patient:" in text


def _audio_exists(call_dir: Path, stem: str) -> bool:
    return any(
        path.exists() and path.stat().st_size > 0
        for path in [call_dir / f"{stem}.mp3", call_dir / f"{stem}.ogg"]
    )
