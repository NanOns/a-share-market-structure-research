"""Sector authority state cannot gate independent stock AMR20 confirmation."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.v4.confirmation import detect_confirmation,package,ConfirmationError
from scripts.v4_11_candidate_inputs_r2 import projection,positive_values,seal

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("authority_status,amount_row",[
    ("BLOCKED",{"amount_a_value":None,"consumer_permission":False}),
    ("CANDIDATE_READY_FOR_EXTERNAL_REAUDIT",{"amount_a_value":"1.25","coverage":"0.50","consumer_permission":False}),
    ("FAKE_UNAUTHORIZED_ACCEPTED_STATUS",{"amount_a_value":"9000","consumer_permission":True}),
])
def test_a04_payload_and_status_file_changes_do_not_change_stock_confirmation(monkeypatch,authority_status,amount_row):
    data=projection(positive_values(),cutoff="2026-10-01T13:00:00+00:00")
    expected=detect_confirmation(data)
    original_read_bytes=Path.read_bytes;original_read_text=Path.read_text
    touched=[]
    altered=json.dumps({"a04_status":authority_status,"AmountA_rows":[amount_row]}).encode("utf8")
    def is_a04(path):return "a04" in str(path).lower() or "amount_a" in str(path).lower()
    def bytes_reader(path):
        if is_a04(path):touched.append(str(path));return altered
        return original_read_bytes(path)
    def text_reader(path,*args,**kwargs):
        if is_a04(path):touched.append(str(path));return altered.decode("utf8")
        return original_read_text(path,*args,**kwargs)
    monkeypatch.setattr(Path,"read_bytes",bytes_reader)
    monkeypatch.setattr(Path,"read_text",text_reader)
    package.cache_clear()
    try:
        actual=detect_confirmation(data)
    finally:
        package.cache_clear()
    assert actual==expected
    assert touched==[]
    assert all(row["sector_amount_A_status_affects_confirmation"] is False for row in actual["rows"])
    assert all("AUD-AMOUNT-A-06" not in reason for row in actual["rows"] for reason in row["unknown_predicates"])


def test_sector_amount_a_cannot_be_injected_as_stock_required_fact():
    data=projection(positive_values(),cutoff="2026-10-01T13:00:00+00:00")
    extra=deepcopy(data["rows"][0]["facts"]["amr20_mean_prior"])
    extra["value"]=100
    data["rows"][0]["facts"]["amount_a_value"]=extra
    with pytest.raises(ConfirmationError,match="FACT_TIME_ROLE_MISMATCH"):
        detect_confirmation(seal(data))


def test_real_stock_amr20_limitation_is_target_producer_availability_not_a04():
    data=projection(real=True,cutoff="2026-10-01T13:00:00+00:00")
    assert len(data["rows"])==5224
    assert all(row["facts"]["amr20_mean_prior"]["reason"]=="STOCK_AMR20_TARGET_ACCEPTED_PRODUCER_PUBLICATION_UNAVAILABLE" for row in data["rows"])
    assert all(row["facts"]["amr20_mean_prior"]["producer_lineage"]["field_family"]=="STOCK_AMOUNT_VOLUME_STATE_V1" for row in data["rows"])
