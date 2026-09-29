import pytest

from src.v4.market_regime_ui import candidate, project


def row(date, trend="STRONG", breadth="STABLE", participation="NORMAL", stress="LOW", change="STABLE"):
    return dict(trade_date=date, trend_axis=trend, breadth_axis=breadth,
                participation_axis=participation, stress_level=stress,
                stress_change=change, output_digest=date)


@pytest.mark.parametrize("item,expected", [
    (row("1", trend="WEAK", stress="HIGH"), "CAPITULATION"),
    (row("1", trend="WEAK", breadth="IMPROVING", change="DECLINING"), "RECOVERY_ATTEMPT"),
    (row("1"), "RISK_ON"),
    (row("1", trend="WEAK"), "RISK_OFF"),
    (row("1", breadth="DETERIORATING"), "NEUTRAL"),
    (row("1", stress="UNKNOWN"), "UNKNOWN"),
])
def test_candidate_first_true(item, expected):
    assert candidate(item) == expected


def test_two_session_hysteresis_capitulation_immediate_and_unknown_last_known():
    path = [row("1"), row("2"), row("3", trend="WEAK"), row("4", trend="WEAK"),
            row("5", trend="WEAK", stress="HIGH"), row("6", stress="UNKNOWN")]
    result = project(path)
    assert result["1"].value == "UNKNOWN"
    assert result["2"].value == "RISK_ON"
    assert result["3"].value == "RISK_ON"
    assert result["4"].value == "RISK_OFF"
    assert result["5"].value == "CAPITULATION"
    assert result["6"].value == "UNKNOWN"
    assert result["6"].last_known == "CAPITULATION"
    with pytest.raises(ValueError):
        project([row("2"), row("1")])
