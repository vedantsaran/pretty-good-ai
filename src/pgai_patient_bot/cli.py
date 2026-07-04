from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import uvicorn

from .config import (
    ConfigError,
    assert_ready_for_calls,
    assert_ready_for_server,
    load_settings,
    missing_for_calls,
    missing_for_server,
)
from .llm import TranscriptAnalyzer
from .scenarios import get_scenario, load_scenarios
from .telephony import start_assessment_call
from .validation import validate_call_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(prog="pgai-bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-env", help="Check local environment variables.")

    serve_parser = subparsers.add_parser("serve", help="Run the local FastAPI server.")
    serve_parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload.")

    call_parser = subparsers.add_parser("call", help="Start one assessment call.")
    call_parser.add_argument("--scenario", required=True, help="Scenario id from scenarios.json.")

    batch_parser = subparsers.add_parser("call-batch", help="Start several assessment calls.")
    batch_parser.add_argument("--limit", type=int, default=10, help="Number of scenarios to call.")
    batch_parser.add_argument("--pause", type=int, default=20, help="Seconds between calls.")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze transcripts into a bug report draft.")
    analyze_parser.add_argument(
        "--output",
        default="docs/bug_report_draft.md",
        help="Path to write the Markdown bug report draft.",
    )

    list_parser = subparsers.add_parser("list-scenarios", help="List scenario ids.")
    list_parser.add_argument("--verbose", action="store_true")

    validate_parser = subparsers.add_parser(
        "validate-artifacts",
        help="Check call artifacts for submission-required files.",
    )
    validate_parser.add_argument("--min-calls", type=int, default=10)

    args = parser.parse_args()
    try:
        if args.command == "check-env":
            check_env()
        elif args.command == "serve":
            serve(reload=args.reload)
        elif args.command == "call":
            call_one(args.scenario)
        elif args.command == "call-batch":
            call_batch(args.limit, args.pause)
        elif args.command == "analyze":
            asyncio.run(analyze_transcripts(Path(args.output)))
        elif args.command == "list-scenarios":
            list_scenarios(verbose=args.verbose)
        elif args.command == "validate-artifacts":
            validate_artifacts(min_calls=args.min_calls)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)


def check_env() -> None:
    settings = load_settings()
    settings.require_supported_voice_provider()
    print("Server readiness:")
    server_missing = missing_for_server(settings)
    print("  OK" if not server_missing else "  Missing: " + ", ".join(server_missing))
    print("Call readiness:")
    call_missing = missing_for_calls(settings)
    print("  OK" if not call_missing else "  Missing: " + ", ".join(call_missing))
    settings.require_safe_call_target()
    print("Assessment target lock: OK")


def serve(reload: bool = False) -> None:
    settings = load_settings()
    assert_ready_for_server(settings)
    uvicorn.run(
        "pgai_patient_bot.twilio_app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=reload,
    )


def call_one(scenario_id: str) -> str:
    settings = load_settings()
    assert_ready_for_calls(settings)
    scenario = get_scenario(scenario_id)
    call = start_assessment_call(settings, scenario)
    print(
        f"Started {call.provider} call {call.sid} "
        f"for scenario {scenario.id}: {scenario.title}"
    )
    return call.sid


def call_batch(limit: int, pause: int) -> None:
    scenarios = load_scenarios()[:limit]
    for index, scenario in enumerate(scenarios, start=1):
        print(f"[{index}/{len(scenarios)}] {scenario.id}")
        call_one(scenario.id)
        if index < len(scenarios):
            time.sleep(pause)


def list_scenarios(verbose: bool = False) -> None:
    for scenario in load_scenarios():
        if verbose:
            print(f"{scenario.id}: {scenario.title} - {scenario.objective}")
        else:
            print(scenario.id)


def validate_artifacts(min_calls: int = 10) -> None:
    settings = load_settings()
    result = validate_call_artifacts(settings.artifact_dir, min_calls=min_calls)
    print(f"Artifact directory: {result.artifact_dir}")
    print(f"Call directories: {len(result.call_dirs)}")
    print(f"Structurally complete calls: {len(result.qualifying_call_dirs)}")
    if result.issues:
        print("Issues:")
        for issue in result.issues:
            prefix = f"{issue.call_dir.name}: " if issue.call_dir else ""
            print(f"  - {prefix}{issue.message}")
        raise ConfigError("Call artifacts are not submission-ready.")
    print("Artifacts structurally complete.")


async def analyze_transcripts(output_path: Path) -> None:
    settings = load_settings()
    if not settings.deepseek_api_key:
        raise ConfigError("Missing DEEPSEEK_API_KEY")
    transcript_paths = sorted(settings.artifact_dir.glob("*/transcript.txt"))
    if not transcript_paths:
        raise ConfigError(f"No transcripts found in {settings.artifact_dir}")
    combined = []
    for path in transcript_paths:
        combined.append(f"## {path.parent.name}\n\n{path.read_text(encoding='utf-8')}")
    analyzer = TranscriptAnalyzer(settings)
    report = await analyzer.analyze("\n\n".join(combined))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
