from workbench_analysis import corrected_focus_replay as replay
from workbench_analysis import r43_focus_replay as daily_replay
import pytest


def install_scanner(monkeypatch, branch_states):
    scenarios = ["LAUNCH_CONFIRM", "RECOVERY_TURN", "STRONG_PULLBACK", "TREND_CONTINUE"]
    machine = {"scenario_priority": scenarios}
    manifest = {"legacy_source": {"sha256": "a" * 64}}

    def scanner(_values):
        result = {}
        for scenario in scenarios:
            checks = branch_states.get(scenario, {"PREDICATE": False})
            result[replay.d0.SCENARIO_KEYS[scenario]] = {
                "checks": checks,
                "eligible": all(value is True for value in checks.values()),
            }
        return result

    monkeypatch.setattr(replay.d0, "package", lambda: (None, manifest, None, machine, scanner))


@pytest.mark.parametrize('producer',[replay,daily_replay])
def test_diagnostic_unknowns_do_not_poison_formal_false(monkeypatch,producer):
    install_scanner(monkeypatch, {
        "LAUNCH_CONFIRM": {"FORMAL": False},
        "RECOVERY_TURN": {"FORMAL": False},
        "STRONG_PULLBACK": {"DIAGNOSTIC": None},
        "TREND_CONTINUE": {"DIAGNOSTIC": None},
    })

    result = producer.confirmation({})

    assert result["confirmation_status"] == "FALSE"
    assert result['legacy_confirmation_status']=='UNKNOWN'
    assert result['production_admission'] is False
    assert result["formal_aggregation_scenarios"] == ["LAUNCH_CONFIRM", "RECOVERY_TURN"]
    assert all(row["aggregation_role"] == "DIAGNOSTIC_ONLY"
               for row in result["scenario_evidence"] if row["scenario"] in {"STRONG_PULLBACK", "TREND_CONTINUE"})


def test_formal_unknown_remains_unknown(monkeypatch):
    install_scanner(monkeypatch, {
        "LAUNCH_CONFIRM": {"FORMAL": None},
        "RECOVERY_TURN": {"FORMAL": False},
        "STRONG_PULLBACK": {"DIAGNOSTIC": None},
        "TREND_CONTINUE": {"DIAGNOSTIC": None},
    })

    result = replay.confirmation({})

    assert result["confirmation_status"] == "UNKNOWN"
    assert "FORMAL:UNKNOWN" in result["scenario_evidence"][0]["unknown_reasons"]


def test_focus_prefers_candidate_date_bound_identity_rows():
    accepted = {"path": "accepted.json", "sha256": "a" * 64}
    dated = {"path": "dated.json", "sha256": "b" * 64}
    assert replay.focus_identity_source_binding({"identity": accepted, "candidate_identity": dated}) == dated
    assert replay.focus_identity_source_binding({"identity": accepted}) == accepted
