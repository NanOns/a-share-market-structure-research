from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from workbench_online.event_models import (
    EVENT_DTO_CONTRACT_VERSION,
    EXT01_EVENT_ADAPTER_VERSION,
    EventSchemaError,
    adapt_ext01_payload,
)


def _payload() -> dict:
    return {
        "status_code": 0,
        "status_msg": "ok",
        "data": {
            "page": 1,
            "msg": "",
            "trade_status": 1,
            "limit_up_count": {"today": {"num": 42}},
            "limit_down_count": {"today": {"num": 7}},
            "info": [
                {
                    "code": "600000",
                    "name": "浦发银行",
                    "latest": "10.12",
                    "change_rate": "10.02",
                    "amount": "--",
                    "order_amount": "1.2亿",
                    "currency_value": "100亿",
                    "turnover_rate": "3.1",
                    "open_num": "2",
                    "reason_type": "金融",
                    "first_limit_up_time": 1757554260,
                    "last_limit_up_time": 0,
                    "market_id": 17,
                    "high_days_value": "2",
                }
            ],
        },
    }


def test_ext01_adapter_separates_header_and_member_and_fails_closed_on_unresolved_scales():
    header, rows = adapt_ext01_payload(
        _payload(),
        trade_date="20260911",
        observed_at="2026-09-12T17:28:09+00:00",
    )

    assert header.contract_version == EVENT_DTO_CONTRACT_VERSION
    assert header.adapter_version == EXT01_EVENT_ADAPTER_VERSION
    assert header.counts == {"source_limit_count": 42, "source_broken_count": None, "source_down_count": 7}
    assert header.rates == {"seal_rate": None, "broken_rate": None, "source_rate": None}
    assert header.scope["complete_pagination"] is False
    assert len(rows) == 1
    row = rows[0]
    assert row.pool_type == "LIMIT_UP"
    assert row.event_state == "LIMIT_UP"
    assert row.source_code == "SH:600000"
    assert row.security_id == "SH.600000"
    assert row.price == Decimal("10.12")
    assert row.amount is None and row.seal_amount is None and row.ret1 is None
    assert row.first_limit_time is not None and row.first_limit_time.tzinfo is not None
    assert row.last_limit_time is None
    assert row.consecutive_limit_days is None and row.m_days is None and row.n_boards is None
    assert "AMOUNT_SCALE_UNRESOLVED" in row.quality_codes
    assert "RET1_SCALE_UNRESOLVED" in row.quality_codes
    assert "LADDER_HEIGHT_SOURCE_MISSING" in row.quality_codes
    assert row.source_fields["order_amount"] == "1.2亿"
    assert "浦发银行" in row.to_record()["source_fields"]["name"]


def test_ext01_adapter_does_not_treat_header_counts_as_member_rows():
    payload = _payload()
    payload["data"]["info"] = []
    header, rows = adapt_ext01_payload(payload, trade_date="20260911", observed_at=datetime(2026, 9, 12, 17, 28, 9))

    assert rows == ()
    assert header.counts["source_limit_count"] == 42
    assert header.scope["page_row_count"] == 0


def test_ext01_adapter_rejects_schema_drift_and_bad_status():
    bad_status = _payload()
    bad_status["status_code"] = 403
    with pytest.raises(EventSchemaError, match="SOURCE_STATUS_NOT_OK"):
        adapt_ext01_payload(bad_status, trade_date="20260911", observed_at="2026-09-12T17:28:09+00:00")

    missing_field = _payload()
    del missing_field["data"]["info"][0]["change_rate"]
    with pytest.raises(EventSchemaError, match="ROW_FIELDS_MISSING:change_rate"):
        adapt_ext01_payload(missing_field, trade_date="20260911", observed_at="2026-09-12T17:28:09+00:00")


@pytest.mark.parametrize("label,expected", [("首板", (1, 1, 1)), ("2天2板", (2, 2, 2)), ("9天5板", (None, 9, 5))])
def test_ext01_dragon_high_days_distinguishes_consecutive_and_m_days_n_boards(label, expected):
    payload = _payload()
    payload["data"]["info"][0]["high_days"] = label
    _, rows = adapt_ext01_payload(payload, trade_date="20260911", observed_at="2026-09-12T17:28:09+00:00")
    row = rows[0]
    assert (row.consecutive_limit_days, row.m_days, row.n_boards) == expected
