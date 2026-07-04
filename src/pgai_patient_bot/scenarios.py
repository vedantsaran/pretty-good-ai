from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class ScenarioError(RuntimeError):
    """Raised when scenario configuration is invalid."""


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    patient_profile: str
    objective: str
    opening_line: str
    facts: dict[str, str]
    test_focus: list[str]
    success_criteria: list[str]
    max_turns: int = 10

    def prompt_context(self) -> str:
        facts = "\n".join(f"- {key}: {value}" for key, value in self.facts.items())
        focus = "\n".join(f"- {item}" for item in self.test_focus)
        criteria = "\n".join(f"- {item}" for item in self.success_criteria)
        return (
            f"Scenario: {self.title}\n"
            f"Patient profile: {self.patient_profile}\n"
            f"Objective: {self.objective}\n"
            f"Opening line if needed: {self.opening_line}\n"
            f"Soft turn budget: {self.max_turns} patient replies before politely ending.\n"
            f"Known facts:\n{facts}\n"
            f"Test focus:\n{focus}\n"
            f"Success criteria:\n{criteria}\n"
        )


def default_scenario_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scenarios" / "scenarios.json"


def load_scenarios(path: Path | None = None) -> list[Scenario]:
    scenario_path = path or default_scenario_path()
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    scenarios = [Scenario(**item) for item in raw]
    ids = [scenario.id for scenario in scenarios]
    duplicate_ids = sorted({scenario_id for scenario_id in ids if ids.count(scenario_id) > 1})
    if duplicate_ids:
        raise ScenarioError(f"Duplicate scenario ids: {', '.join(duplicate_ids)}")
    return scenarios


def get_scenario(scenario_id: str, path: Path | None = None) -> Scenario:
    for scenario in load_scenarios(path):
        if scenario.id == scenario_id:
            return scenario
    raise ScenarioError(f"Unknown scenario id: {scenario_id}")
