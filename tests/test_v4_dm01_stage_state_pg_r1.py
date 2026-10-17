from __future__ import annotations

import json
from contextlib import contextmanager

import pytest


class MemoryFactStore:
    database_identity = {"database": "market_research", "database_oid": 42, "host": "127.0.0.1", "port": 5432}
    records = {}

    def __init__(self, root, folder):
        self.root = root
        self.folder = folder

    def append(self, kind, key, value, *, migration_timeout_seconds):
        assert kind == "stage_state"
        assert migration_timeout_seconds == 120
        old = self.records.get(key)
        if old is not None and old != value:
            raise ValueError("identity conflict")
        self.records[key] = value
        return {"fact_key": key}

    def read(self, binding):
        return self.records[binding["fact_key"]]

    @staticmethod
    def _database_identity(pg):
        return MemoryFactStore.database_identity


@pytest.fixture(autouse=True)
def isolated_memory_store(monkeypatch):
    from workbench_db import v4_dm01_stage_state_pg_r1 as state

    MemoryFactStore.records = {}
    monkeypatch.setattr(state, "ForwardFactStore", MemoryFactStore)
    real_read_fact = state._read_fact

    def read_fact(root, binding):
        if "fact_key" in binding:
            return MemoryFactStore.records[binding["fact_key"]]
        return real_read_fact(root, binding)

    monkeypatch.setattr(state, "_read_fact", read_fact)
    monkeypatch.setenv("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", json.dumps(MemoryFactStore.database_identity))


def test_stage_fact_round_trips_exact_date_stage_and_payload(tmp_path):
    from workbench_db.v4_dm01_stage_state_pg_r1 import append_stage, read_stage

    payload = {"contract_id": "GBBQ_SOURCE_REVISION_PROBE_V1", "trade_date": "2026-10-16",
               "status": "REUSE_ACCEPTED_GBBQ_SNAPSHOT", "accepted_snapshot_id": "sha256-example"}
    binding = append_stage(tmp_path, "2026-10-16", "gbbq_revision_probe", payload)

    assert read_stage(tmp_path, binding["binding"], trade_date="2026-10-16",
                      stage="gbbq_revision_probe") == payload


@pytest.mark.parametrize("trade_date,stage", [("2026-10-17", "gbbq_revision_probe"),
                                                ("2026-10-16", "lifecycle_snapshot")])
def test_stage_fact_read_rejects_wrong_date_or_stage(tmp_path, trade_date, stage):
    from workbench_db.v4_dm01_stage_state_pg_r1 import append_stage, read_stage

    payload = {"contract_id": "GBBQ_SOURCE_REVISION_PROBE_V1", "trade_date": "2026-10-16",
               "status": "REUSE_ACCEPTED_GBBQ_SNAPSHOT"}
    binding = append_stage(tmp_path, "2026-10-16", "gbbq_revision_probe", payload)

    with pytest.raises(ValueError, match="DM01_STAGE_STATE_BINDING_MISMATCH"):
        read_stage(tmp_path, binding["binding"], trade_date=trade_date, stage=stage)


def test_stage_fact_append_rejects_database_identity_drift(tmp_path, monkeypatch):
    from workbench_db import v4_dm01_stage_state_pg_r1 as state

    monkeypatch.setenv("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", json.dumps(
        {**MemoryFactStore.database_identity, "database": "other"}))
    with pytest.raises(ValueError, match="DM01_STAGE_STATE_DATABASE_IDENTITY_MISMATCH"):
        state.append_stage(tmp_path, "2026-10-16", "gbbq_revision_probe",
                           {"contract_id": "GBBQ_SOURCE_REVISION_PROBE_V1", "trade_date": "2026-10-16"})


def test_stage_fact_reader_uses_readonly_dsn_and_verifies_pg_payload(tmp_path, monkeypatch):
    from workbench_db import v4_dm01_stage_state_pg_r1 as state
    from workbench_db.v4_forward_pg_r1 import canonical, digest
    from workbench_db.v4_native import workspace_schema

    identity = MemoryFactStore.database_identity
    payload = {"contract_id": "GBBQ_SOURCE_REVISION_PROBE_V1", "trade_date": "2026-10-16",
               "status": "WAIT_MARKET_CLOSE"}
    record = {"contract_id": state.CONTRACT, "contract_version": state.VERSION,
              "trade_date": "2026-10-16", "stage": "gbbq_revision_probe",
              "payload_sha256": digest(canonical(payload)), "payload": payload}
    key = digest(canonical(record))
    schema = workspace_schema(tmp_path / state.FOLDER, "forward")
    descriptor = {"contract_id": "V4_FORWARD_PG_FACT_STORE_R1", "engine": "postgresql",
                  "database_identity": identity, "schema": schema, "kind": state.KIND,
                  "fact_key": key, "payload_sha256": digest(canonical(record))}
    descriptor_raw = canonical(descriptor)
    descriptor_path = tmp_path / state.FOLDER / state.KIND / (digest(key.encode()) + ".pg.json")
    descriptor_path.parent.mkdir(parents=True)
    descriptor_path.write_bytes(descriptor_raw)
    binding = {"path": descriptor_path.relative_to(tmp_path).as_posix(),
               "sha256": digest(descriptor_raw), "bytes": len(descriptor_raw)}
    calls = []

    class Result:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    class PG:
        def execute(self, statement, params=()):
            calls.append((statement, params))
            if "current_database()" in statement:
                return Result((identity["database"], identity["database_oid"], identity["host"], identity["port"]))
            return Result((canonical(record).decode(), digest(canonical(record))))

    @contextmanager
    def connection(received_schema, *, read_only=False, dsn=None):
        assert received_schema == schema
        assert read_only is True
        assert dsn == "reader-dsn"
        yield PG()

    monkeypatch.setenv("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", json.dumps(identity))
    monkeypatch.setattr(state.v4_native, "configured_reader_dsn", lambda: "reader-dsn")
    monkeypatch.setattr(state.v4_native, "connection", connection)

    assert state.read_stage(tmp_path, binding, trade_date="2026-10-16",
                            stage="gbbq_revision_probe") == payload
    assert calls[-1][1] == (state.KIND, key)


def test_gbbq_probe_entrypoint_appends_exact_result_to_pg_stage(monkeypatch, tmp_path, capsys):
    import sys
    from scripts import probe_v4_dm01_gbbq_revision as probe
    from workbench_analysis import dm01_runtime_r4
    from workbench_db import v4_dm01_stage_state_pg_r1 as state

    monkeypatch.setattr(probe, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["probe_v4_dm01_gbbq_revision", "--target-date", "2026-10-16"])
    monkeypatch.setattr(probe, "resolve_tdx_root", lambda root: tmp_path / "tdx")
    monkeypatch.setattr(dm01_runtime_r4, "session_gate", lambda *a, **k: {"status": "WAIT_MARKET_CLOSE"})
    calls = []

    binding = {"contract_id": state.CONTRACT, "trade_date": "2026-10-16",
               "stage": "gbbq_revision_probe",
               "binding": {"path": "data/v4/fact.pg.json", "sha256": "a" * 64, "bytes": 1}}

    def append(root, day, stage, payload):
        calls.append((root, day, stage, payload))
        return {**binding, "trade_date": day}

    monkeypatch.setattr(state, "append_stage", append)
    monkeypatch.setattr(probe, "write_json_atomic", lambda *a, **k: "b" * 64)

    assert probe.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert calls[0][1:3] == (output["target_date"], "gbbq_revision_probe")
    assert calls[0][3]["status"] == "WAIT_MARKET_CLOSE"
    assert output["pg_stage_state"] == {**binding, "trade_date": output["target_date"]}
