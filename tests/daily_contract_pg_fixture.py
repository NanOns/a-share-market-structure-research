"""Controlled registry-return fixture for daily executor tests."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "V4_DAILY_TDX_READONLY_SOURCE_R1": "config/v4_daily_tdx_readonly_source_v1.json",
    "BAOSTOCK_DM01_SDK_SCHEMA_ADAPTER_V2": "config/baostock_dm01_sdk_schema_adapter_v2.json",
}


def install(monkeypatch, executor):
    """Stub the registry result; the production helper still enforces PG-only mode."""
    def load(contract_id, version):
        try:
            path = ROOT / CONTRACTS[contract_id]
        except KeyError as exc:
            raise AssertionError(f"unexpected daily contract: {contract_id}") from exc
        contract = json.loads(path.read_bytes())
        version_field = "version" if contract_id == "BAOSTOCK_DM01_SDK_SCHEMA_ADAPTER_V2" else "contract_version"
        assert contract.get(version_field) == version
        return contract

    monkeypatch.setattr(executor, "_load_daily_contract_from_pg", load)


def install_calendar(monkeypatch, accepted_trade_date):
    """Supply one accepted PG publication calendar for controlled executor tests."""
    from types import SimpleNamespace
    from workbench_db import v4_market_calendar_reader_r1 as calendar_reader

    calendar={"status":"ACCEPTED","source":"PG_ACCEPTED_PUBLICATION_HEAD",
              "accepted_trade_date":accepted_trade_date}
    monkeypatch.setenv("V4_MARKET_CALENDAR_SOURCE","PG")
    monkeypatch.setattr(calendar_reader,"from_environment",
                        lambda:SimpleNamespace(calendar=lambda:calendar))
