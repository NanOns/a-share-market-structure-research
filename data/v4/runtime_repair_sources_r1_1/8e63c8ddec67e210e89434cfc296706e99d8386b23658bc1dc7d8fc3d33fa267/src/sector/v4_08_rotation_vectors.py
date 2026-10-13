"""Pure, input-explicit checks for the frozen V4-08 R1/R2/R3 synthetic vectors."""
from __future__ import annotations

from typing import Any, Mapping


def _tri(value: Any) -> bool | None:
    if value is True or value == "TRUE":
        return True
    if value is False or value == "FALSE":
        return False
    return None


def _and(values: list[Any]) -> bool | None:
    normalized = [_tri(value) for value in values]
    if False in normalized:
        return False
    if None in normalized:
        return None
    return True


def _or_not_applicable(values: list[Any]) -> bool | None:
    normalized = [None if value == "NOT_APPLICABLE" else _tri(value) for value in values]
    if True in normalized:
        return True
    usable = [value for value in normalized if value is not None]
    if not usable:
        return None
    if None in normalized:
        return None
    return False


def evaluate_rotation_vector(scenario: Mapping[str, Any]) -> dict[str, Any]:
    early_retention_or = _or_not_applicable([
        scenario.get("seed_retention_pass"), scenario.get("breadth_retention_pass")
    ])
    early_retained = _and([
        scenario.get("basket_return_positive"), early_retention_or,
        scenario.get("breadth_delta_pass"), scenario.get("top1_concentration_pass"),
    ])
    strong_prev = int(scenario.get("strong_prev", 0))
    mature_retention = "NOT_APPLICABLE" if strong_prev == 0 else bool(scenario.get("strong_member_retention_pass", scenario.get("seed_retention_pass", False)))
    mature_retained = "NOT_APPLICABLE" if mature_retention == "NOT_APPLICABLE" else _and([early_retained, mature_retention])
    pulse_age = int(scenario.get("pulse_age_sessions", 0))
    in_allowed = bool(scenario.get("pulse") is True and pulse_age >= 1 and early_retained is True)
    accepted_allowed = bool(scenario.get("pulse") is True and pulse_age >= 2 and early_retained is True
                            and scenario.get("acceptance_breadth_floor_pass", True) is True)
    diffusion = bool(scenario.get("diffusion_pass"))
    expanding_allowed = bool(
        mature_retained is True and diffusion
        and scenario.get("prior_state") in {"ROTATION_ACCEPTED", "ROTATION_EXPANDING"}
        and pulse_age >= 2
    )
    reaccelerating_allowed = bool(
        mature_retained is True and scenario.get("pulse") is True
        and scenario.get("prior_state") in {"WARM", "CONFIRMED"}
        and scenario.get("yesterday_dq5_nonpositive")
    )
    return {
        "early_retention_or": "UNKNOWN" if early_retention_or is None else early_retention_or,
        "early_retained": "UNKNOWN" if early_retained is None else early_retained,
        "mature_strong_retention": mature_retention,
        "mature_retained": "UNKNOWN" if mature_retained is None else mature_retained,
        "rotation_in_possible": in_allowed,
        "rotation_accepted_possible": accepted_allowed,
        "rotation_expanding_allowed": expanding_allowed,
        "rotation_reaccelerating_allowed": reaccelerating_allowed,
        "production_authorized": False,
    }
