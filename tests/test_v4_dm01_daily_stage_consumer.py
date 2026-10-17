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
