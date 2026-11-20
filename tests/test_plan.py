import json

import pytest

from file_manager.plan import Action, PlanError, parse_plan

VALID = {
    "file": "Scan 12.pdf",
    "dest": "00_Personal/01_Financial",
    "new_name": "2026-10-31_bank_statement.pdf",
    "confidence": "high",
    "reason": "Bank statement dated 31 Oct 2026",
}


def plan_json(*actions):
    return json.dumps(list(actions))


def test_parses_valid_action():
    assert parse_plan(plan_json(VALID)) == [Action(**VALID)]


def test_parses_multiple_actions_in_order():
    second = {**VALID, "file": "b.txt", "confidence": "low"}

    actions = parse_plan(plan_json(VALID, second))

    assert [a.file for a in actions] == ["Scan 12.pdf", "b.txt"]


def test_empty_plan_is_valid():
    assert parse_plan("[]") == []


def test_ignores_extra_fields():
    assert parse_plan(plan_json({**VALID, "extra": 1})) == [Action(**VALID)]


def test_action_is_sure_only_when_confidence_is_high():
    assert Action(**VALID).is_sure
    assert not Action(**{**VALID, "confidence": "low"}).is_sure


def test_rejects_invalid_json():
    with pytest.raises(PlanError, match="not valid JSON"):
        parse_plan("not json")


def test_rejects_non_list():
    with pytest.raises(PlanError, match="list"):
        parse_plan(json.dumps(VALID))


def test_rejects_non_object_action():
    with pytest.raises(PlanError, match="action 0"):
        parse_plan('["Scan 12.pdf"]')


@pytest.mark.parametrize("field", ["file", "dest", "new_name", "confidence", "reason"])
def test_rejects_missing_field(field):
    action = {k: v for k, v in VALID.items() if k != field}

    with pytest.raises(PlanError, match=field):
        parse_plan(plan_json(action))


@pytest.mark.parametrize("field", ["file", "dest", "new_name", "confidence", "reason"])
def test_rejects_non_string_field(field):
    with pytest.raises(PlanError, match=field):
        parse_plan(plan_json({**VALID, field: 1}))


@pytest.mark.parametrize("field", ["file", "dest", "new_name"])
def test_rejects_empty_path_field(field):
    with pytest.raises(PlanError, match=field):
        parse_plan(plan_json({**VALID, field: "  "}))


def test_rejects_unknown_confidence():
    with pytest.raises(PlanError, match="confidence"):
        parse_plan(plan_json({**VALID, "confidence": "very sure"}))


def test_error_names_the_bad_action():
    with pytest.raises(PlanError, match="action 1"):
        parse_plan(plan_json(VALID, {**VALID, "dest": 5}))
