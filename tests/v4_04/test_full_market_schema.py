import json
from pathlib import Path

from scripts.run_v4_04_full_market_candidate import build_row
from src.v4.market_regime_ui import RegimeUI


ROOT = Path(__file__).resolve().parents[2]


def test_full_market_row_schema_and_unknown_propagation():
    schema = json.loads((ROOT / "config/v4_04_output_schema_v1.json").read_text(encoding="utf-8"))
    factor = {"security_id": "SEC-TEST", "board_scope": "STAR", "trade_date": "2026-09-24",
              "fields": {"ma20": {"value": None, "quality_state": "UNKNOWN", "unknown_reason": "INSUFFICIENT_HISTORY", "output_digest": "x"}}}
    regime = RegimeUI("UNKNOWN", "UNKNOWN", None, 0, {}, "REQUIRED_MARKET_AXIS_UNKNOWN")
    row = build_row(factor, [], [], [], [], {"source_security_key": "SH.688000"}, "source-digest", "contract-digest", ["2026-09-24"], regime)
    assert set(schema["required_row_identity"]) <= row.keys()
    assert set(schema["required_envelopes"]) <= row.keys()
    assert set(schema["state_envelope"]) <= row["states"]["trend_state"].keys()
    assert set(schema["derived_envelope"]) <= row["derived_fields"]["ma10"].keys()
    assert row["profile_component_status"] == "UNKNOWN_DATA"
    assert row["states"]["trend_state"]["value"] == "UNKNOWN"
    assert row["states"]["severe_extension"]["value"] is None
    assert row["board"] in schema["required_boards"]
