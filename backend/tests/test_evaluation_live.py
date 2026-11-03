from __future__ import annotations

import builtins
import json
from decimal import Decimal
from unittest.mock import Mock

import pytest

from evaluation import live, run


def _per_request_reserve(payload: dict[str, str]) -> tuple[int, Decimal]:
    body_bytes = len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii"))
    input_tokens = body_bytes + live.INPUT_TOKEN_OVERHEAD
    raw_cost = (
        Decimal(input_tokens) * live.INPUT_USD_PER_MILLION_TOKENS
        + Decimal(live.MAX_COMPLETION_TOKENS) * live.OUTPUT_USD_PER_MILLION_TOKENS
    ) / Decimal(1_000_000)
    return input_tokens, raw_cost * live.COST_SAFETY_MULTIPLIER


def test_cost_guard_rejects_next_call_before_request_when_remaining_budget_is_insufficient():
    payload = {"model": live.MODEL}
    max_input_tokens, one_call_reserve = _per_request_reserve(payload)
    guard = live.CostGuard(one_call_reserve * Decimal("1.5"))

    guard.before_request(payload)
    guard.record_usage(
        {"prompt_tokens": max_input_tokens, "completion_tokens": live.MAX_COMPLETION_TOKENS}
    )

    with pytest.raises(live.LiveEvaluationError, match="cost_limit_before_request"):
        guard.before_request(payload)

    assert guard.requests == 1
    assert guard.pending_request_cost == Decimal("0")


def test_cost_guard_rejects_oversized_body_without_reserving_request():
    guard = live.CostGuard(Decimal("0.50"))

    with pytest.raises(live.LiveEvaluationError, match="request_size_limit"):
        guard.before_request({"pedido": "x" * live.MAX_REQUEST_BODY_BYTES})

    assert guard.requests == 0
    assert guard.pending_request_cost == Decimal("0")


@pytest.mark.parametrize(
    ("usage", "error"),
    [
        (None, "provider_usage_missing"),
        ({"prompt_tokens": "12", "completion_tokens": 4}, "provider_usage_invalid"),
        ({"prompt_tokens": 12, "completion_tokens": -1}, "provider_usage_invalid"),
    ],
)
def test_cost_guard_keeps_reservation_and_request_count_when_usage_is_missing_or_invalid(usage, error):
    guard = live.CostGuard(Decimal("0.50"))
    guard.before_request({"model": live.MODEL})
    reservation = guard.pending_request_cost

    with pytest.raises(live.LiveEvaluationError, match=error):
        guard.record_usage(usage)

    assert guard.requests == 1
    assert guard.pending_request_cost == reservation > 0
    assert guard.prompt_tokens == guard.completion_tokens == 0


@pytest.mark.parametrize(
    ("environment", "price_profile"),
    [
        ({"AGENT_MODE": "local"}, None),
        ({"OPENAI_API_KEY": ""}, None),
        ({"OPENAI_MODEL": "another-model"}, None),
        ({}, (Decimal("0.21"), live.OUTPUT_USD_PER_MILLION_TOKENS)),
    ],
)
def test_configuration_mismatch_fails_before_agent_or_provider_request(
    monkeypatch, capsys, environment, price_profile
):
    valid_environment = {
        "AGENT_MODE": "openai",
        "OPENAI_API_KEY": "test-only-placeholder",
        "OPENAI_MODEL": live.MODEL,
    }
    valid_environment.update(environment)
    for name, value in valid_environment.items():
        monkeypatch.setenv(name, value)
    if price_profile is not None:
        monkeypatch.setattr(live, "INPUT_USD_PER_MILLION_TOKENS", price_profile[0])
        monkeypatch.setattr(live, "OUTPUT_USD_PER_MILLION_TOKENS", price_profile[1])
    get_agent = Mock(side_effect=AssertionError("agent creation must not happen"))
    monkeypatch.setattr(live.main, "get_purchase_agent", get_agent)

    assert live.run_live_evaluation(Decimal("0.50")) == 2
    assert get_agent.call_count == 0
    assert "test-only-placeholder" not in capsys.readouterr().out


def test_cost_above_approved_cap_fails_before_agent_creation(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", live.MODEL)
    get_agent = Mock(side_effect=AssertionError("agent creation must not happen"))
    monkeypatch.setattr(live.main, "get_purchase_agent", get_agent)

    assert live.run_live_evaluation(Decimal("0.51")) == 2
    assert get_agent.call_count == 0


@pytest.mark.parametrize(
    "arguments",
    [
        ["--live", "--max-cost-usd", "0.50"],
        ["--confirm-paid"],
        ["--live", "--confirm-paid", "--max-cost-usd", "0.51"],
    ],
)
def test_cli_rejects_missing_opt_in_or_over_budget_before_live_import(arguments):
    with pytest.raises(SystemExit) as error:
        run.main_cli(arguments)

    assert error.value.code == 2


def test_default_cli_keeps_deterministic_path_and_does_not_import_live(monkeypatch):
    original_import = builtins.__import__
    scenario_calls: list[str] = []

    def reject_live_import(name, *args, **kwargs):
        if name == "evaluation.live":
            raise AssertionError("default mode must not load paid evaluation code")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_live_import)
    monkeypatch.setattr(run, "run_scenario", lambda scenario: (scenario_calls.append(scenario.name) or True, "ok"))

    assert run.main_cli([]) == 0
    assert len(scenario_calls) == 5
