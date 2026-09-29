import pytest

from src.v4.profile_status import component_status


@pytest.mark.parametrize("observed,required,degraded,expected", [
    (3, 3, False, "READY"), (2, 3, False, "PARTIAL"),
    (0, 3, False, "UNKNOWN_DATA"), (2, 3, True, "DEGRADED")])
def test_component_status_mapping(observed, required, degraded, expected):
    assert component_status(observed, required, degraded) == expected


def test_component_status_rejects_invalid_availability():
    with pytest.raises(ValueError):
        component_status(4, 3)
