from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from workbench_service.app import Api
from workbench_service.quotes import CONTRACT_ID, QuoteService, build_quote


def bar(**overrides):
    value = {
        "security_id": "SH.600000",
        "date": date(2026, 9, 8),
        "raw_open": 10.0,
        "raw_high": 11.0,
        "raw_low": 9.5,
        "raw_close": 10.5,
        "raw_amount": 1000.0,
        "qfq_mul": 1.0,
        "qfq_add": 0.0,
        "adjustment_status": "VERIFIED_REPRODUCIBLE_TDX_NATIVE",
        "adjustment_version": "tdx-affine-qfq-v0.2",
        "tradable": True,
        "has_actual_bar": True,
        "data_observed": True,
        "is_synthetic_fill": False,
        "missing_state": "BAR",
    }
    value.update(overrides)
    return value


def test_reference_prev_close_has_priority_and_raw_close_is_displayed() -> None:
    result = build_quote(
        bar(raw_close=10.5, reference_prev_close=10.0),
        bar(date=date(2026, 9, 7), raw_close=8.0),
        publication_id="pub-1",
        source_identity_sha256="source-1",
    )
    assert result["raw_close"] == 10.5
    assert result["latest_price"] == 10.5
    assert result["quote_prev_close"] == 10.0
    assert result["quote_ret1"] == pytest.approx(0.05)
    assert result["quote_ret1_basis"] == "REFERENCE_PREV_CLOSE"
    assert result["quote_state"] == "VALID"
    assert result["source_identity_sha256"] == "source-1"
    assert result["quote_contract_id"] == CONTRACT_ID


def test_raw_close_fallback_is_marked_and_adjustment_change_is_not_calculated() -> None:
    result = build_quote(bar(raw_close=11.0), bar(date=date(2026, 9, 7), raw_close=10.0), publication_id="pub-1")
    assert result["quote_ret1"] == pytest.approx(0.1)
    assert result["quote_ret1_basis"] == "RAW_CLOSE_PREVIOUS_TRADING_DAY"
    assert result["quote_state"] == "VALID_DEGRADED"

    unsafe = build_quote(
        bar(raw_close=11.0, qfq_mul=2.0),
        bar(date=date(2026, 9, 7), raw_close=10.0, qfq_mul=1.0),
        publication_id="pub-1",
    )
    assert unsafe["quote_ret1"] is None
    assert unsafe["quote_state"] == "UNKNOWN_CORPORATE_ACTION"
    assert unsafe["quote_ret1_basis"] == "CORPORATE_ACTION_UNSAFE"


def test_missing_previous_close_is_explicitly_unavailable() -> None:
    result = build_quote(bar(), None, publication_id="pub-1")
    assert result["raw_close"] == 10.5
    assert result["quote_ret1"] is None
    assert result["quote_state"] == "MISSING_PREVIOUS_CLOSE"
    assert result["quote_ret1_basis"] == "NO_VERIFIED_PREVIOUS_CLOSE"


def test_real_service_uses_previous_market_session_not_previous_publication() -> None:
    service = QuoteService(Path("data/normalized/adjusted_daily.parquet"))
    quotes = service.load(
        trade_date=date(2026, 9, 4),
        publication_id="695c7ae5affd4abbb3d86eddb4b154e0",
        source_identity_sha256="source-1",
    )
    result = quotes["SH.600000"]
    assert result["quote_prev_close"] == 9.27
    assert result["raw_close"] == 9.43
    assert result["quote_ret1_basis"] == "RAW_CLOSE_PREVIOUS_TRADING_DAY"


def test_api_quotes_bind_source_and_use_raw_close() -> None:
    api = Api(Path("data/database/market_research.duckdb"))
    publication_id = "452811b8e0c54c029560aae46c6d3081"
    result = api._quotes(publication_id)["SH.600000"]
    assert result["raw_close"] == 9.23
    assert result["latest_price"] == 9.23
    assert result["quote_prev_close"] == 9.43
    assert result["quote_ret1_basis"] == "RAW_CLOSE_PREVIOUS_TRADING_DAY"
    assert result["publication_id"] == publication_id
    assert "data/normalized/adjusted_daily.parquet#security_id=SH.600000" in result["source_ref"]


def test_api_refuses_publication_without_a_matching_quote_manifest() -> None:
    api = Api(Path("data/database/market_research.duckdb"))
    assert api._quotes("m4-44e401cad4337d38105b496077a4f36e") == {}


def test_quote_contract_is_versioned_and_preserves_legacy_fields() -> None:
    contract = Path("docs/M7A_QUOTE_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "workbench-quote-v2.1" in contract
    assert "REFERENCE_PREV_CLOSE" in contract
    assert "RAW_CLOSE_PREVIOUS_TRADING_DAY" in contract
    assert "UNKNOWN_CORPORATE_ACTION" in contract
