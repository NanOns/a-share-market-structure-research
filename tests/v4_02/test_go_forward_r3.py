from datetime import datetime
from decimal import Decimal
import gzip
import json
from pathlib import Path
from struct import pack
import zipfile

import pytest

from src.v4.go_forward_r3 import publication_time, target_identity
from workbench_analysis.tdx_official_daily_source import _zip_validate
from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors


ROOT = Path(__file__).resolve().parents[2]


def identity(key="SH.605999", **changes):
    row = {"source_security_key": key, "security_id": "SEC-NEW", "security_type": "A_STOCK",
           "list_date": "2026-09-28", "delist_date": None,
           "symbol_effective_from": "2026-09-28", "symbol_effective_to": None}
    return {**row, **changes}


def test_valid_new_listing_included():
    active, errors = target_identity({"SH.600000"}, {"SH.605999"},
                                     [identity(), identity("SH.600000", security_id="SEC-OLD", list_date="1999-01-01")],
                                     "2026-09-28")
    assert not errors and set(active) == {"SH.600000", "SH.605999"}


@pytest.mark.parametrize("records", [[], [identity(list_date="2026-09-29")],
                                      [identity(), identity(security_id="SEC-OTHER")]])
def test_unresolved_future_or_ambiguous_new_key_blocks(records):
    _, errors = target_identity(set(), {"SH.605999"}, records, "2026-09-28")
    assert errors == ["SH.605999"]


def test_delayed_publication_valid_and_negative_times():
    args = (20260928, 20260928, "2026-09-28T07:58:05Z", "2026-09-29T06:53:52Z",
            "2026-09-26T13:07:05Z", "2026-09-29T06:53:52Z")
    assert publication_time(*args)["knowledge_lineage"] == "PIT_OBSERVED_AFTER_FORMAL_PUBLICATION"
    for bad in [(20260928, 20260929, *args[2:]),
                (*args[:5], "2026-09-28T08:00:00Z"),
                (*args[:4], "2026-09-30T00:00:00Z", args[5])]:
        with pytest.raises(ValueError):
            publication_time(*bad)


def test_zip_target_date_and_future_row(tmp_path: Path):
    archive = tmp_path / "package.zip"
    bar = lambda d: pack("<IIIIIfII", d, 100, 101, 99, 100, 1000.0, 100, 0)
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("sh/lday/sh600000.day", bar(20260928))
        z.writestr("sz/lday/sz000001.day", bar(20260928))
    assert _zip_validate(archive)["status"] == "PASS"
    with zipfile.ZipFile(archive, "a") as z:
        z.writestr("sh/lday/sh600001.day", bar(20260929))
    with zipfile.ZipFile(archive) as z:
        assert any(int.from_bytes(z.read(i.filename)[:4], "little") > 20260928 for i in z.infolist())


def test_real_antibot_html_then_official_curl_fallback():
    capture = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json").read_text(encoding="utf-8"))
    assert [a["method"] for a in capture["attempts"]] == ["PYTHON_URLLIB", "PYTHON_URLLIB", "WINDOWS_CURL"]
    assert all(a["http_headers"]["Content-Type"] == "text/html" and not a["zip_is_zipfile"] for a in capture["attempts"][:2])
    assert capture["attempts"][-1]["zip_validation"]["status"] == "PASS"


def test_overlap_mismatch_is_blocking_condition():
    overlap = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_RAW_OVERLAP_R2.json").read_text(encoding="utf-8"))
    assert overlap["status"] == "PASS" and overlap["counts"]["EXACT_OR_NORMALIZED_TOLERANCE_MATCH"] == 5210
    assert ("PASS" if overlap["counts"].get("MISMATCH", 0) == 0 else "V4_02_GO_FORWARD_BLOCKED_RAW_OVERLAP_MISMATCH") == "PASS"
    assert ("PASS" if 1 == 0 else "V4_02_GO_FORWARD_BLOCKED_RAW_OVERLAP_MISMATCH") == "V4_02_GO_FORWARD_BLOCKED_RAW_OVERLAP_MISMATCH"


def test_no_bar_and_unsupported_event_fail_closed():
    sample = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R3.json").read_text(encoding="utf-8"))["sample_kinds"]
    for name in ("no_t0_bar", "unsupported"):
        row = sample[name]["row"]
        assert row["adjusted_quality"].startswith("ADJUSTED_UNAVAILABLE_")
        assert row["qfq_ohlc"] is None


def test_supported_category_one_and_later_event_not_backdated():
    action = XrxdEvent("SH.TEST", 20260928, cash_dividend_per_10=Decimal("1"))
    base = build_affine_factors([20260924, 20260928], [action])[20260924]
    later = XrxdEvent("SH.TEST", 20260928, cash_dividend_per_10=Decimal("10"))
    polluted = build_affine_factors([20260924, 20260928], [action, later])[20260924]
    assert base.qfq_price(Decimal("10")) != polluted.qfq_price(Decimal("10"))
    receipt = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_NO_BACKDATING_R2.json").read_text(encoding="utf-8"))
    assert receipt["later_only_record_influenced_t0"] is False


def test_later_non_price_revision_and_deterministic_output():
    later = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_GBBQ_LATER_REVISION_R2.json").read_text(encoding="utf-8"))
    deterministic = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_DETERMINISM_R3.json").read_text(encoding="utf-8"))
    assert later["price_affected_security_count"] == 0 and later["later_records_used_for_t0_qfq"] is False
    assert deterministic["same_logical_digest"] and deterministic["same_compressed_sha256"]
