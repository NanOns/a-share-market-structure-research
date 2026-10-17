from types import SimpleNamespace
from contextlib import contextmanager
import hashlib
import json

import pytest

from workbench_service.candidate_research_read_v2 import capture_calendar_contract


CONTRACT = {
    "contract_id": "V4_DM01_OFFICIAL_CALENDAR_BRIDGE_V1",
    "version": "1.0.0",
    "runtime": {"timezone": "Asia/Shanghai", "market_close_local": "15:00:00"},
}


def test_candidate_bff_loads_calendar_cutoff_from_approved_pg_contract(monkeypatch, tmp_path):
    import workbench_analysis.contract_registry_pg_v1 as registry
    import workbench_db.v4_publication_reader as publication_reader

    class Connection:
        def __enter__(self):
            return object()

        def __exit__(self, *_):
            return False

    monkeypatch.setenv("V4_DAILY_CONTRACT_SOURCE", "PG")
    monkeypatch.setenv("V4_PG_MODEL_NAMESPACE_ID", "v4-main")
    monkeypatch.setenv("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", '{"database":"market_research"}')
    monkeypatch.setattr(publication_reader, "readonly_connection", lambda: Connection())
    monkeypatch.setattr(registry, "load_current_approved_contract", lambda *args, **kwargs: SimpleNamespace(
        parsed_json=CONTRACT, raw_content=b'{"approved":"pg"}'))

    close, binding = capture_calendar_contract(tmp_path)

    assert close == "15:00:00"
    assert binding["source"] == "PG_APPROVED_REGISTRY"
    assert binding["contract_id"] == CONTRACT["contract_id"]
    assert "path" not in binding


def test_candidate_bff_does_not_fall_back_to_file_without_pg_namespace(monkeypatch, tmp_path):
    monkeypatch.delenv("V4_DAILY_CONTRACT_SOURCE", raising=False)
    monkeypatch.delenv("V4_PG_MODEL_NAMESPACE_ID", raising=False)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/v4_dm01_bridge_calendar_v1.json").write_text(
        '{"contract_id":"V4_DM01_OFFICIAL_CALENDAR_BRIDGE_V1",'
        '"version":"1.0.0","runtime":{"timezone":"Asia/Shanghai",'
        '"market_close_local":"15:00:00"}}', encoding="utf-8")

    with pytest.raises(ValueError, match="PG_MODEL_NAMESPACE_REQUIRED_FOR_DAILY_CONTRACT"):
        capture_calendar_contract(tmp_path)


def test_candidate_bff_file_contract_mode_must_be_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("V4_DAILY_CONTRACT_SOURCE", "FILE")
    path = tmp_path / "config/v4_dm01_bridge_calendar_v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"contract_id":"V4_DM01_OFFICIAL_CALENDAR_BRIDGE_V1",'
        '"version":"1.0.0","runtime":{"timezone":"Asia/Shanghai",'
        '"market_close_local":"15:00:00"}}', encoding="utf-8")

    close, binding = capture_calendar_contract(tmp_path)

    assert close == "15:00:00"
    assert binding["source"] == "EXPLICIT_FILE"
    assert binding["path"] == "config/v4_dm01_bridge_calendar_v1.json"


@pytest.mark.parametrize("approval_action", ["APPROVED", "REVOKED"])
def test_candidate_bff_calls_real_registry_reader_on_pg_shaped_snapshot(
    monkeypatch, tmp_path, approval_action
):
    from workbench_db import v4_publication_reader as publication_reader

    raw = json.dumps(CONTRACT, sort_keys=True, separators=(",", ":")).encode()
    sha = hashlib.sha256(raw).hexdigest()
    identity = {"database": "market_research", "database_oid": 16384,
                "host": "127.0.0.1", "port": 5432}
    contract_row = (raw, sha, "JSON", "1", "v4-main", "source-r1",
                    approval_action, "owner", "approval-r1", "2026-10-17T00:00:00Z",
                    "source-r1", sha, "2026-10-17T00:00:01Z")

    class Result:
        def __init__(self, value): self.value = value
        def fetchone(self): return self.value

    class ReadOnlySnapshot:
        def execute(self, query, params=()):
            if "current_database()" in query and "transaction_isolation" in query:
                return Result(("market_research", "v4_reader", "repeatable read", "on"))
            if "inet_server_addr()" in query:
                return Result(("market_research", 16384, "127.0.0.1", 5432))
            if "FROM pg_roles" in query:
                return Result(("v4_reader",) + (False,) * 14)
            if "FROM v4.contract_versions c" in query:
                return Result(contract_row)
            raise AssertionError("unexpected PG query: " + query)

    @contextmanager
    def readonly_connection():
        yield ReadOnlySnapshot()

    monkeypatch.setattr(publication_reader, "readonly_connection", readonly_connection)
    monkeypatch.setenv("V4_DAILY_CONTRACT_SOURCE", "PG")
    monkeypatch.setenv("V4_PG_MODEL_NAMESPACE_ID", "v4-main")
    monkeypatch.setenv("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", json.dumps(identity))
    (tmp_path / "config").mkdir()
    (tmp_path / "config/v4_dm01_bridge_calendar_v1.json").write_bytes(raw)

    if approval_action == "APPROVED":
        close, binding = capture_calendar_contract(tmp_path)
        assert close == "15:00:00"
        assert binding["source"] == "PG_APPROVED_REGISTRY"
        assert binding["sha256"] == sha
    else:
        with pytest.raises(ValueError, match="V4_PG_CONTRACT_APPROVAL_OR_DIGEST_INVALID"):
            capture_calendar_contract(tmp_path)
