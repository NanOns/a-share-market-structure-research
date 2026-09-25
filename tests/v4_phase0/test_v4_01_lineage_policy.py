import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_v4_01_lineage_policy_never_fabricates_pre_v4_as_recorded_history():
    contract = json.loads((ROOT / "config/v4_01_history_lineage_policy_v1.json").read_text("utf-8"))
    assert contract["history_before_v4"]["lineage"] == "RECONSTRUCTED_CORRECTED"
    assert contract["history_before_v4"]["as_recorded_claim_allowed"] is False
    assert contract["history_from_v4_go_forward"]["lineage"] == "PIT_OBSERVED_AS_RECORDED_APPEND_ONLY"
    assert contract["acceptance_meaning"].startswith("PASS means the lineage boundary is explicit")
    assert "overwrite_prior_source_revision" in contract["prohibited"]
