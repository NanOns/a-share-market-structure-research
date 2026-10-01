from copy import deepcopy
import json
from pathlib import Path
import pytest
from workbench_analysis.forward_pit_ledger_r2 import atomic,bound,canonical,reference
from workbench_analysis.forward_pit_ledger_r2_1 import append_observation
from .test_candidate_boundaries import envelope


@pytest.mark.parametrize("payload,expected", [
    ({"contract_id":"ACTUAL_V2","rows":[],"trade_date":"2026-09-28"},"SCHEMA_DRIFT"),
    ({"contract_id":"RAW_V1","rows":[],"trade_date":"2026-09-29"},"TARGET_DATE_MISMATCH"),
    ({"contract_id":"RAW_V1","rows":[{"trade_date":"2026-09-29"}],"trade_date":"2026-09-28"},"SCHEMA_DRIFT"),
    ({"contract_id":"RAW_V1","trade_date":"2026-09-28"},"SCHEMA_DRIFT"),
    ([],"SCHEMA_DRIFT")])
def test_declared_schema_and_target_cannot_hide_actual_payload(tmp_path,payload,expected):
    e=envelope(tmp_path)
    atomic(tmp_path/"payload.json",canonical(payload))
    e["sources"]["RAW"]["bytes_binding"]=reference(tmp_path,tmp_path/"payload.json")
    value=append_observation(tmp_path,"ledger",e)["publication"]
    assert expected in value["detectors"] and value["completeness"]=="PARTIAL"


def test_real_accepted_baseline_r2_1_replay_retains_original_identity():
    root=Path(__file__).resolve().parents[2]
    e=json.loads((root/"data/v4/a03_forward_pit_r2/accepted_baseline_capture_envelope.json").read_text(encoding="utf8"))
    value=append_observation(root,"data/v4/a03_forward_pit_r2",e)
    assert value["retry"] is True and value["detectors"]==["DUPLICATE_CAPTURE"]
    report=json.loads((root/"reports/audits/A03_FORWARD_PIT_BUILDER_R2_REAL_OBSERVATION.json").read_text(encoding="utf8"))
    assert value["publication"]==json.loads(bound(root,report["publication"]))


def test_undeclared_source_family_rejected(tmp_path):
    e=envelope(tmp_path);e["sources"]["UNDECLARED"]=deepcopy(e["sources"]["RAW"])
    with pytest.raises(ValueError,match="UNDECLARED_CAPTURE_SOURCE_FAMILY"):
        append_observation(tmp_path,"ledger",e)
