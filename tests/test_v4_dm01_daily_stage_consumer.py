def test_daily_orchestrator_loads_gbbq_probe_from_bound_pg_stage(monkeypatch, tmp_path):
    import hashlib
    from scripts import run_v4_dm01_daily_increment as daily
    from workbench_db import v4_dm01_stage_state_pg_r1 as state

    snapshot = tmp_path / "data/v4/accepted_gbbq_manifest.json"
    snapshot.parent.mkdir(parents=True)
    raw = b'{"snapshot_id":"sha256-accepted"}'
    snapshot.write_bytes(raw)
    payload = {"contract_id": "GBBQ_SOURCE_REVISION_PROBE_V1", "trade_date": "2026-10-16",
               "status": "REUSE_ACCEPTED_GBBQ_SNAPSHOT", "accepted_manifest_path": str(snapshot),
               "accepted_manifest_sha256": hashlib.sha256(raw).hexdigest(),
               "accepted_snapshot_id": "sha256-accepted"}
    monkeypatch.setattr(daily, "ROOT", tmp_path)
    monkeypatch.setattr(state, "read_stage", lambda root, binding, **scope: payload)
    state_binding = {"contract_id": state.CONTRACT, "trade_date": "2026-10-16",
                     "stage": "gbbq_revision_probe", "binding": {"fact_key": "stage-key"}}

    actual = daily._accepted_gbbq_snapshot("2026-10-16", state_binding)

    assert actual["status"] == "REUSE_ACCEPTED_GBBQ_SNAPSHOT"
    assert actual["accepted_snapshot_id"] == "sha256-accepted"


def test_continuous_reader_resolves_one_date_stage_directly_from_pg(monkeypatch, tmp_path):
    import json
    from contextlib import contextmanager
    from scripts import run_v4_continuous_data_maintenance as maintenance
    from workbench_db import v4_dm01_stage_state_pg_r1 as state
    from workbench_db.v4_forward_pg_r1 import canonical, digest

    day = "2026-10-16"
    payload = {"contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1", "trade_date": day, "status": "READY"}
    record = {"contract_id": state.CONTRACT, "contract_version": state.VERSION,
              "trade_date": day, "stage": "lifecycle_snapshot",
              "payload_sha256": digest(canonical(payload)), "payload": payload}
    raw = canonical(record).decode("utf-8")
    identity = {"database": "market_research", "database_oid": 42, "host": "127.0.0.1", "port": 5432}

    class Cursor:
        def __init__(self, rows): self.rows = rows
        def fetchone(self): return self.rows[0] if self.rows else None
        def fetchall(self): return self.rows

    class FakePg:
        def execute(self, query, params=None):
            if "current_database()" in query: return Cursor([(identity["database"], identity["database_oid"], identity["host"], identity["port"])])
            assert params == (state.KIND, day, "lifecycle_snapshot")
            return Cursor([(raw, digest(raw.encode("utf-8")))])

    @contextmanager
    def connection(*_args, **_kwargs): yield FakePg()

    monkeypatch.setattr(state, "_expected_identity", lambda: identity)
    monkeypatch.setattr(state.v4_native, "configured_reader_dsn", lambda: "controlled-test-dsn")
    monkeypatch.setattr(state.v4_native, "connection", connection)
    monkeypatch.setattr(maintenance, "ROOT", tmp_path)

    assert maintenance.discover_lifecycle_snapshot(day) == payload


def test_continuous_pg_stage_reader_fails_closed_on_duplicate_facts(monkeypatch, tmp_path):
    import json
    from contextlib import contextmanager
    import pytest
    from workbench_db import v4_dm01_stage_state_pg_r1 as state
    from workbench_db.v4_forward_pg_r1 import canonical, digest

    day = "2026-10-16"
    payload = {"trade_date": day, "stage": "lifecycle_snapshot"}
    record = {"contract_id": state.CONTRACT, "contract_version": state.VERSION,
              "trade_date": day, "stage": "lifecycle_snapshot",
              "payload_sha256": digest(canonical(payload)), "payload": payload}
    raw = canonical(record).decode("utf-8")
    identity = {"database": "market_research", "database_oid": 42, "host": "127.0.0.1", "port": 5432}

    class Cursor:
        def __init__(self, rows): self.rows = rows
        def fetchone(self): return self.rows[0] if self.rows else None
        def fetchall(self): return self.rows

    class FakePg:
        def execute(self, query, params=None):
            if "current_database()" in query:
                return Cursor([(identity["database"], identity["database_oid"], identity["host"], identity["port"])])
            return Cursor([(raw, digest(raw.encode("utf-8"))), (raw, digest(raw.encode("utf-8")))])

    @contextmanager
    def connection(*_args, **_kwargs): yield FakePg()

    monkeypatch.setattr(state, "_expected_identity", lambda: identity)
    monkeypatch.setattr(state.v4_native, "configured_reader_dsn", lambda: "controlled-test-dsn")
    monkeypatch.setattr(state.v4_native, "connection", connection)
    with pytest.raises(ValueError, match="DM01_STAGE_STATE_NOT_UNIQUE"):
        state.read_unique_stage(tmp_path, trade_date=day, stage="lifecycle_snapshot")


def test_continuous_bootstrap_baselines_are_loaded_from_pg_stage_facts(monkeypatch):
    from scripts import run_v4_continuous_data_maintenance as maintenance
    facts = {
        "phase0_acceptance": {"phase0_status": "FULL_PASS"},
        "v401_acceptance": {"required_scope_status": "PASS", "status": "PASS"},
        "v401_postcheck": {"status": "PASS"},
        "v402_acceptance": {"external_acceptance": "EXTERNALLY_ACCEPTED", "required_scope_result": "PASS"},
    }
    calls = []

    def read_stage(root, *, trade_date, stage):
        calls.append((trade_date, stage))
        return facts[stage]

    monkeypatch.setattr(maintenance, "sha", lambda _path: maintenance.TDX_ARCHIVE_SHA256)
    monkeypatch.setattr("workbench_db.v4_dm01_stage_state_pg_r1.read_unique_stage", read_stage)
    result = maintenance.accepted_stage_bindings()

    assert calls == [(maintenance.BASE_CUTOFF, name) for name in facts]
    assert result["phase0"]["authority"] == "PG_FORWARD_FACT"
    assert result["v4_02_accepted_head"]["external_acceptance"] == "EXTERNALLY_ACCEPTED"
    assert result["accepted_stage_facts"]["v402_acceptance"]["payload"] == facts["v402_acceptance"]


def test_continuous_bootstrap_does_not_fallback_when_baseline_stage_fact_is_missing(monkeypatch):
    import pytest
    from scripts import run_v4_continuous_data_maintenance as maintenance

    def read_stage(_root, *, trade_date, stage):
        if stage == "v402_acceptance":
            raise ValueError("DM01_STAGE_STATE_NOT_UNIQUE")
        return {"phase0_status": "FULL_PASS", "required_scope_status": "PASS", "status": "PASS"}

    monkeypatch.setattr("workbench_db.v4_dm01_stage_state_pg_r1.read_unique_stage", read_stage)
    with pytest.raises(ValueError, match="DM01_STAGE_STATE_NOT_UNIQUE"):
        maintenance.accepted_stage_bindings()


def test_continuous_data_head_bootstrap_uses_pg_without_local_head_fallback(monkeypatch, tmp_path):
    import json
    import pytest
    import hashlib
    from scripts import run_v4_continuous_data_maintenance as maintenance
    from workbench_db import v4_dm01_stage_state_pg_r1 as state

    head = {"contract_id": "V4_DATA_ACCEPTED_HEAD_V2", "version": "2.0.0",
            "accepted_trade_date": "2026-10-16", "PIT_ELIGIBLE": False, "AS_RECORDED": False}
    raw = json.dumps(head, separators=(",", ":")).encode("utf-8")
    binding = {"path": "data/v4/V4_DATA_ACCEPTED_HEAD.json",
               "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    authority_bindings = {
        "data": binding,
        "stage": {"path": "data/v4/V4_STAGE_ACCEPTED_HEAD.json", "sha256": "a" * 64, "bytes": 10},
        "current_stage_head": {"path": "data/v4/V4_15_ACCEPTED_HEAD.json", "sha256": "b" * 64, "bytes": 10},
        "current_authority_contract": {"path": "config/v4_current_stage_authority_v2.json", "sha256": "c" * 64, "bytes": 10},
    }
    payload = {"contract_id": state.DATA_HEAD_IMPORT_CONTRACT, "contract_version": state.VERSION,
               "trade_date": "2026-10-16", "accepted_trade_date": "2026-10-16",
               "source_binding": binding, "source_raw_utf8": raw.decode("utf-8"),
               "source_raw_sha256": binding["sha256"], "source_raw_bytes": len(raw),
               "accepted_authority_bindings": authority_bindings, "head": head}
    monkeypatch.setattr(maintenance, "ROOT", tmp_path)
    monkeypatch.setattr(state, "read_latest_stage", lambda root, *, stage: payload)
    monkeypatch.setattr(maintenance, "read", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("LOCAL_HEAD_READ_FORBIDDEN")))
    monkeypatch.setattr(maintenance, "atomic", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("LOCAL_HEAD_WRITE_FORBIDDEN")))

    result = maintenance.initialize_bootstrap({})

    assert result["status"] == "PG_DATA_HEAD_READY"
    assert result["data_head"] == head
    assert result["data_head_sha256"] == binding["sha256"]
    assert result["data_head_source_binding"] == binding
    assert result["authority"] == "PG_FORWARD_FACT"

    monkeypatch.setattr(state, "read_latest_stage", lambda *_a, **_k: (_ for _ in ()).throw(ValueError("DM01_STAGE_STATE_NOT_FOUND")))
    local_pointer = tmp_path / "data/v4/V4_DATA_ACCEPTED_HEAD.json"
    local_pointer.parent.mkdir(parents=True)
    local_pointer.write_text(json.dumps(head), encoding="utf-8")
    with pytest.raises(SystemExit, match="DM01_PG_DATA_HEAD_MIGRATION_REQUIRED:DM01_STAGE_STATE_NOT_FOUND"):
        maintenance.initialize_bootstrap({})
