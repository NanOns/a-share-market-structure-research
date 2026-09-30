import json
from pathlib import Path

from src.sector.v4_08_rotation_vectors import evaluate_rotation_vector


ROOT = Path(__file__).resolve().parents[2]


def test_rotation_r1_strong_previous_zero_keeps_early_path_open():
    vector = json.loads((ROOT / "config/v4_08_algorithm_machine_vectors_v1.json").read_text(encoding="utf-8"))["vectors"][0]
    result = evaluate_rotation_vector(vector["scenario"])
    assert result["rotation_in_possible"] is True
    assert result["mature_strong_retention"] == "NOT_APPLICABLE"
    assert result["production_authorized"] is False


def test_rotation_r2_retention_and_breadth_deterioration_block_mature_upgrade():
    vector = json.loads((ROOT / "config/v4_08_algorithm_machine_vectors_v1.json").read_text(encoding="utf-8"))["vectors"][1]
    result = evaluate_rotation_vector(vector["scenario"])
    assert result["mature_retained"] is False
    assert result["rotation_expanding_allowed"] is False
    assert result["rotation_reaccelerating_allowed"] is False


def test_rotation_r3_concentrated_single_leader_blocks_acceptance_and_expansion():
    vector = json.loads((ROOT / "config/v4_08_algorithm_machine_vectors_v1.json").read_text(encoding="utf-8"))["vectors"][2]
    result = evaluate_rotation_vector(vector["scenario"])
    assert result["early_retained"] is False
    assert result["rotation_accepted_possible"] is False
    assert result["rotation_expanding_allowed"] is False


def test_rotation_unknown_seed_fields_are_not_coerced_to_zero_or_false():
    result = evaluate_rotation_vector({
        "pulse": True, "strong_prev": 0, "basket_return_positive": True,
        "seed_retention_pass": None, "breadth_retention_pass": None,
        "breadth_delta_pass": True, "top1_concentration_pass": True,
        "pulse_age_sessions": 1,
    })
    assert result["early_retained"] == "UNKNOWN"
    assert result["rotation_in_possible"] is False


def test_contracts_have_no_full_market_permission_and_preserve_forbidden_inputs():
    paths = [
        "config/v4_08_sector_native_contract_v1.json",
        "config/v4_08_sector_prewatch_contract_v1.json",
        "config/v4_08_rotation_core_contract_v1.json",
        "config/v4_08_sector_legacy_adapter_contract_v1.json",
    ]
    for path in paths:
        contract = json.loads((ROOT / path).read_text(encoding="utf-8"))
        assert contract.get("formal_consumer_enabled", contract.get("scope", {}).get("formal_consumer_enabled")) is False
    rotation = json.loads((ROOT / paths[2]).read_text(encoding="utf-8"))
    assert "same-day final stock PREWATCH" in rotation["inputs"]["forbidden"]
    assert "V4-06" in rotation["inputs"]["forbidden"]
    parameters = json.loads((ROOT / "config/v4_08_algorithm_parameter_set_v1.json").read_text(encoding="utf-8"))
    unresolved = {row["parameter_id"] for row in parameters["parameters"] if row["value"] is None}
    assert unresolved == {
        "V4_08_EARLY_SEED_RETENTION_MIN", "V4_08_EARLY_BREADTH_RETENTION_MIN",
        "V4_08_EARLY_BREADTH_DELTA_MIN", "V4_08_EARLY_TOP1_CONCENTRATION_MAX",
        "V4_08_MATURE_STRONG_RETENTION_MIN",
    }
