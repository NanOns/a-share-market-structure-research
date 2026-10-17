"""Controlled registry-return fixture for daily executor tests."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "V4_DAILY_RUNTIME_ACCEPTANCE_PATH_R1": "config/v4_daily_runtime_acceptance_path_v1.json",
    "V4_DAILY_TDX_READONLY_SOURCE_R1": "config/v4_daily_tdx_readonly_source_v1.json",
}


def install(monkeypatch, executor):
    """Stub the registry result; the production helper still enforces PG-only mode."""
    def load(contract_id, version):
        try:
            path = ROOT / CONTRACTS[contract_id]
        except KeyError as exc:
            raise AssertionError(f"unexpected daily contract: {contract_id}") from exc
        contract = json.loads(path.read_bytes())
        assert contract.get("contract_version") == version
        return contract

    monkeypatch.setattr(executor, "_load_daily_contract_from_pg", load)
