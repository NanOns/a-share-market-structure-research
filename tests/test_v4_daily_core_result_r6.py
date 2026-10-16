import hashlib
import json

import pytest

from workbench_db.v4_daily_core_result_r6 import CoreResultError, build_daily_core_result_plan


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _input():
    producer_sha = "a" * 64
    source_sha = "b" * 64
    receipt = {
        "trade_date": "2026-10-16", "producer_contract_id": "V4_OPERATIONAL_DAILY_OWNER_R1",
        "producer_sha256": producer_sha, "publication_id": "pub-20261016-r1",
        "publication_revision": 1, "source_manifest_sha256": source_sha,
    }
    receipt["receipt_sha256"] = _sha(receipt)
    rows = [{
        "trade_date": "2026-10-16", "security_id": "SH.600000", "security_type": "STOCK",
        "trade_status": "TRADING", "open": 9.8, "high": 10.2, "low": 9.7,
        "close": 10.0, "volume": 1000, "amount": 1_000_000,
        "turnover_rate": None, "turnover_status": "TURNOVER_UNAVAILABLE",
        "ma5": None, "ma20": None, "ma60": None,
        "history_status": "INSUFFICIENT_NEW_LISTING_HISTORY",
        "price_basis": "TDX_GBBQ_UNCHANGED", "source_revision_id": "v4sr-tdx-r1",
        "profile_payload": {"label": "CORE"}, "quality_status": "ACTUAL_PRODUCER_ROW",
    }]
    return receipt, rows, source_sha, producer_sha


def test_core_result_plan_binds_actual_rows_and_keeps_unresolved_gate_closed():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-16", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    assert plan["row_count"] == 1
    assert plan["missing_price_rows"] == 0
    assert plan["rows"][0]["turnover_status"] == "TURNOVER_UNAVAILABLE"
    assert plan["rows"][0]["history_status"] == "INSUFFICIENT_NEW_LISTING_HISTORY"
    assert plan["publishability_status"] == "BLOCKED_COMPLETENESS_CONTRACT_UNRESOLVED"
    assert plan["write_mode"] == "PLAN_ONLY_NO_DATABASE_IO"


def test_core_result_rejects_wrong_receipt_t0_and_price_basis():
    receipt, rows, source_sha, producer_sha = _input()
    receipt["trade_date"] = "2026-10-15"
    receipt["receipt_sha256"] = _sha({key: value for key, value in receipt.items() if key != "receipt_sha256"})
    with pytest.raises(CoreResultError, match="CORE_RESULT_PRODUCER_RECEIPT_BINDING_MISMATCH"):
        build_daily_core_result_plan(
            publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-16", source_manifest_sha256=source_sha,
            producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
            producer_receipt=receipt, rows=rows,
        )
    receipt, rows, source_sha, producer_sha = _input()
    rows[0]["price_basis"] = "BAOSTOCK_ADJUSTED"
    with pytest.raises(CoreResultError, match="CORE_RESULT_PRICE_BASIS_UNSUPPORTED"):
        build_daily_core_result_plan(
            publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-16", source_manifest_sha256=source_sha,
            producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
            producer_receipt=receipt, rows=rows,
        )
