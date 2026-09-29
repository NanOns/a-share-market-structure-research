import json
from pathlib import Path

from src.v4.profile_core import P


ROOT = Path(__file__).resolve().parents[2]


def test_machine_registry_and_parameter_references_complete():
    registry = json.loads((ROOT / "config/v4_04_field_registry_v1.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "config/v4_04_output_schema_v1.json").read_text(encoding="utf-8"))
    algorithm = json.loads((ROOT / "config/v4_04_algorithm_contracts_v1.json").read_text(encoding="utf-8"))
    parameter_file = json.loads((ROOT / "config/v4_04_parameter_set_v1.json").read_text(encoding="utf-8"))
    required_metadata = {"field_id", "data_type", "unit", "producer", "producer_contract_id",
                         "parameter_set_id", "required", "time_semantics", "window_semantics",
                         "price_basis", "source_identity", "unknown_policy", "quality_propagation",
                         "output_digest_semantics", "consumer_stage"}
    assert len(registry["fields"]) == len({x["field_id"] for x in registry["fields"]})
    assert all(required_metadata <= set(x) for x in registry["fields"])
    assert set(schema["required_boards"]) == {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}
    params = {x["parameter_id"]: x["value"] for x in parameter_file["parameters"]}
    assert {key.removeprefix("V4_04_"): value for key, value in params.items()} == P
    refs = set()

    def walk(node):
        if isinstance(node, dict):
            if "parameter_id" in node and isinstance(node["parameter_id"], str):
                refs.add(node["parameter_id"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(algorithm["rules"])
    assert refs <= set(params)
    assert len(algorithm["rules"]) >= 12


def test_no_turnover_or_sector_contract_leakage():
    registry = json.loads((ROOT / "config/v4_04_field_registry_v1.json").read_text(encoding="utf-8"))
    ids = {x["field_id"] for x in registry["fields"]}
    assert "turnover_state" not in ids
    assert "relative_sector_state" not in ids
    assert {"weekly_trend_state", "monthly_trend_state", "pos250", "ma10", "minimum_liquidity", "severe_extension"} <= ids
