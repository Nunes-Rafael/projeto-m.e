from evaluation import run as evaluation
from evaluation.run import SCENARIOS, run_scenario


def test_all_evaluation_scenarios_pass_with_controlled_fixtures():
    results = [run_scenario(scenario) for scenario in SCENARIOS]

    assert len(results) == 5
    assert all(passed for passed, _ in results)


def test_scenario_results_are_deterministic():
    first = [run_scenario(scenario) for scenario in SCENARIOS]
    second = [run_scenario(scenario) for scenario in SCENARIOS]

    assert first == second


def test_cli_exits_nonzero_when_any_case_fails(monkeypatch):
    monkeypatch.setattr(evaluation, "run_scenario", lambda _scenario: (False, "falha simulada"))

    assert evaluation.main_cli() == 1
