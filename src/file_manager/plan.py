"""The plan: what the model says to do with each file (design §2)."""

from __future__ import annotations

import json
from dataclasses import dataclass

CONFIDENCE_LEVELS = ("high", "medium", "low")
FIELDS = ("file", "dest", "new_name", "confidence", "reason")
PATH_FIELDS = ("file", "dest", "new_name")


class PlanError(ValueError):
    """The model's output is not a valid plan."""


@dataclass(frozen=True)
class Action:
    """One file and where the model says it goes."""

    file: str
    dest: str
    new_name: str
    confidence: str
    reason: str

    @property
    def is_sure(self) -> bool:
        """Sure actions move without asking; the rest are asked (design §3)."""
        return self.confidence == "high"


def parse_plan(text: str) -> list[Action]:
    """Parse the model's JSON output into actions, or raise PlanError."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise PlanError(f"plan is not valid JSON: {e}") from e

    if not isinstance(data, list):
        raise PlanError("plan must be a JSON list of actions")

    return [_parse_action(i, item) for i, item in enumerate(data)]


def _parse_action(index: int, item: object) -> Action:
    where = f"action {index}"
    if not isinstance(item, dict):
        raise PlanError(f"{where}: must be a JSON object")

    for field in FIELDS:
        if field not in item:
            raise PlanError(f"{where}: missing {field!r}")
        if not isinstance(item[field], str):
            raise PlanError(f"{where}: {field!r} must be a string")

    for field in PATH_FIELDS:
        if not item[field].strip():
            raise PlanError(f"{where}: {field!r} is empty")

    if item["confidence"] not in CONFIDENCE_LEVELS:
        raise PlanError(
            f"{where}: 'confidence' must be one of {', '.join(CONFIDENCE_LEVELS)}"
        )

    return Action(**{field: item[field] for field in FIELDS})
