import json
from pathlib import Path

from scripts.verify_v4_03_ast_golden_vectors_r3 import mutate
from src.v4.contracts.algorithm_contract_numeric_v12 import NumericContext


ROOT = Path(__file__).resolve().parents[2]


def test_r3_named_case_boundaries_and_tamper_detection():
    fixture = json.loads((ROOT / "config/v4_03_ast_numeric_fixture_v1.json").read_text(encoding="utf-8"))
    contracts = json.loads((ROOT / "config/v4_03_algorithm_contracts_v1.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "config/v4_03_ast_golden_cases_r3.json").read_text(encoding="utf-8"))["cases"]
    params = {x["parameter_id"]: x["value"] for x in json.loads((ROOT / "config/v4_03_parameter_registry_v1.json").read_text(encoding="utf-8"))["entries"]}
    by_field = {x["outputs"][0]["field_id"]: x for x in contracts["contracts"]}
    assert len(cases) >= 30
    assert len({x["category"] for x in cases}) >= 30
    case = next(x for x in cases if x["case_id"] == "RANK_FULL_TIE")
    contract = by_field[case["field_id"]]
    ctx = NumericContext(mutate(fixture, case["operations"]), params)
    actual = ctx.eval(contract["ast"], len(ctx.history) - 1, contract["window_refs"][0]["contract_id"])
    assert actual == 50
    tampered = dict(case, expected=51)
    assert actual != tampered["expected"]


def test_source_identity_change_rejects_technical_window():
    fixture = json.loads((ROOT / "config/v4_03_ast_numeric_fixture_v1.json").read_text(encoding="utf-8"))
    params = {x["parameter_id"]: x["value"] for x in json.loads((ROOT / "config/v4_03_parameter_registry_v1.json").read_text(encoding="utf-8"))["entries"]}
    ast = {"type": "WINDOW_AGGREGATE", "operator": "MEAN", "window_contract_id": "TECHNICAL_BAR_WINDOW_V1",
           "window_size": {"type": "PARAM_REF", "parameter_id": "V4_03_WINDOW_SIZE_5"}, "include_current": True,
           "source": {"type": "FIELD_REF", "field_id": "close"}}
    ctx = NumericContext(mutate(fixture, [["set_bar", -2, "source", "e" * 64]]), params)
    assert ctx.eval(ast, len(ctx.history) - 1, "TECHNICAL_BAR_WINDOW_V1") is None
