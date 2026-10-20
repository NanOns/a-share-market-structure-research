"""R6 source consumers resolve authority from PG and fail closed on absence."""
import pytest


def test_r43_json_source_uses_only_pg_ingress(monkeypatch, tmp_path):
    from workbench_analysis import r43_owner_replay
    calls = []

    def read_path(root, path):
        calls.append((root, path))
        return {"value": {"contract_id": "BOUND"}}

    monkeypatch.setattr(
        "workbench_db.v4_historical_source_ingress_pg_r1.read_path", read_path
    )
    monkeypatch.setattr(
        "pathlib.Path.read_bytes",
        lambda _path: (_ for _ in ()).throw(AssertionError("workspace read")),
    )

    assert r43_owner_replay.pg_json_source(tmp_path, "config/authority.json") == {
        "contract_id": "BOUND"
    }
    assert calls == [(tmp_path, "config/authority.json")]


@pytest.mark.parametrize("module_name", [
    "workbench_analysis.r43_owner_replay",
    "workbench_analysis.corrected_owner_replay",
])
def test_owner_protected_state_rechecks_pg_bindings_without_workspace_reads(monkeypatch, tmp_path, module_name):
    import hashlib
    import importlib
    from pathlib import Path

    module=importlib.import_module(module_name)
    authority=b'{"contract_id":"JOINT_AUTHORITY"}'
    authority_sha=hashlib.sha256(authority).hexdigest()
    head_sha="a"*64
    monkeypatch.setattr(module,"checked_pg",lambda _root,binding: authority if binding["path"]=="config/v4_joint_release_authority_v1.json" else b"")
    monkeypatch.setattr(
        "workbench_db.dm01_data_accepted_head_pg_r1.read_current",
        lambda _root: {"head_sha256":head_sha},
    )
    monkeypatch.setattr(Path,"read_bytes",lambda *_: (_ for _ in ()).throw(AssertionError("workspace read")))

    protected={"config/v4_joint_release_authority_v1.json":authority_sha,
               "data/v4/V4_DATA_ACCEPTED_HEAD.json":head_sha}
    assert module.protected_state_unchanged(tmp_path,protected)


def test_corrected_owner_exact_input_never_admits_missing_file(monkeypatch, tmp_path):
    from workbench_analysis import corrected_owner_replay

    def missing(*_args, **_kwargs):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_NOT_FOUND")

    monkeypatch.setattr(
        "workbench_db.v4_historical_source_ingress_pg_r1.bound_bytes", missing
    )
    monkeypatch.setattr(
        "workbench_db.v4_historical_source_ingress_pg_r1.read_package_bytes", missing
    )
    monkeypatch.setattr(
        "pathlib.Path.read_bytes",
        lambda _path: (_ for _ in ()).throw(AssertionError("workspace read")),
    )

    with pytest.raises(ValueError, match="CORRECTED_PG_INPUT_UNAVAILABLE.*HISTORICAL_SOURCE_INGRESS_NOT_FOUND"):
        corrected_owner_replay.checked_pg(
            tmp_path, {"path": "data/input.json", "sha256": "a" * 64}
        )


def test_historical_exact_resolves_verified_pg_package_after_inline_not_found(monkeypatch,tmp_path):
    import hashlib
    from pathlib import Path
    from workbench_analysis import historical_stage_governance_r17 as governance

    raw=b'package-only-pg-bytes';sha=hashlib.sha256(raw).hexdigest();calls=[]
    def missing(_root,_path,_sha):raise ValueError('HISTORICAL_SOURCE_INGRESS_NOT_FOUND')
    def package(root,path,expected):
        calls.append((root,path,expected));return {'raw':raw}
    monkeypatch.setattr(governance,'read_bound',missing)
    monkeypatch.setattr(governance,'read_package_bytes',package)
    monkeypatch.setattr(Path,'read_bytes',lambda *_: (_ for _ in ()).throw(AssertionError('workspace fallback')))
    bound=governance.exact(tmp_path,dict(path='reports/large.jsonl',sha256=sha,bytes=len(raw)))
    assert bound.read_bytes()==raw
    assert calls==[(tmp_path.resolve(),'reports/large.jsonl',sha)]


def test_corrected_owner_candidate_json_is_registered_in_pg(monkeypatch, tmp_path):
    import json
    from pathlib import Path
    from workbench_analysis import corrected_owner_replay

    ingested = []

    def write(path, value, *, project_root):
        assert project_root == tmp_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text('{"candidate":"DEV"}\n', encoding="utf8")

    monkeypatch.setattr(corrected_owner_replay, "write", write)
    monkeypatch.setattr(
        corrected_owner_replay,
        "_ingress_candidate_bytes",
        lambda root, path, raw: ingested.append((root, Path(path).relative_to(root).as_posix(), raw)),
    )
    monkeypatch.setattr(
        corrected_owner_replay,
        "ref",
        lambda root, path: {"path": Path(path).relative_to(root).as_posix()},
    )

    receipt = corrected_owner_replay.write_candidate_json(
        tmp_path, tmp_path / "data/v4/candidate/OWNER.json", {"candidate": "DEV"}
    )

    assert receipt == {"path": "data/v4/candidate/OWNER.json"}
    assert len(ingested) == 1
    assert ingested[0][:2] == (tmp_path, "data/v4/candidate/OWNER.json")
    assert json.loads(ingested[0][2]) == {"candidate": "DEV"}


def test_corrected_owner_json_ambiguity_fails_closed_without_exact_identity(monkeypatch, tmp_path):
    from workbench_analysis import corrected_owner_replay

    def ambiguous(*_args, **_kwargs):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE")

    monkeypatch.setattr(
        "workbench_db.v4_historical_source_ingress_pg_r1.read_path", ambiguous
    )
    with pytest.raises(ValueError, match="PG_JSON_SOURCE_EXACT_BINDING_REQUIRED"):
        corrected_owner_replay.pg_json_source(tmp_path, "data/candidate.json")


def test_r43_candidate_binding_ambiguity_fails_closed_without_exact_identity(monkeypatch, tmp_path):
    from workbench_analysis import r43_owner_replay

    def ambiguous(*_args, **_kwargs):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE")

    monkeypatch.setattr(
        "workbench_db.v4_historical_source_ingress_pg_r1.read_path", ambiguous
    )
    with pytest.raises(ValueError, match="PG_SOURCE_EXACT_BINDING_REQUIRED"):
        r43_owner_replay.pg_source_binding(tmp_path, "data/candidate.json")


def test_corrected_profile_history_is_consumed_in_core_order():
    from workbench_analysis.corrected_structure_replay import OrderedHistoryBySecurity

    history = OrderedHistoryBySecurity(iter([
        {"security_id": "S1", "bars": [{"trade_date": "2026-09-29", "close": 10}]},
        {"security_id": "S2", "bars": [{"trade_date": "2026-09-30", "close": 11}]},
    ]))

    assert history.get("S1") == {"2026-09-29": {"trade_date": "2026-09-29", "close": 10}}
    assert history.get("S2") == {"2026-09-30": {"trade_date": "2026-09-30", "close": 11}}
    assert history.get("S3") is None


def test_focus_contract_uses_json_compatible_pg_text_without_yaml(monkeypatch, tmp_path):
    from workbench_analysis import r43_focus_replay

    calls = []
    monkeypatch.setattr(
        r43_focus_replay,
        "pg_text_source",
        lambda root, path: calls.append((root, path)) or '{"format":"JSON_COMPATIBLE_YAML"}',
    )
    monkeypatch.setattr(
        "pathlib.Path.read_bytes",
        lambda _path: (_ for _ in ()).throw(AssertionError("workspace read")),
    )

    assert r43_focus_replay.research_attention_config(tmp_path) == {
        "format": "JSON_COMPATIBLE_YAML"
    }
    assert calls == [(tmp_path, "config/research_attention_v3.yaml")]


def test_corrected_focus_replay_inputs_are_pg_only(monkeypatch, tmp_path):
    from workbench_analysis import corrected_focus_replay

    calls = []

    def source(root, path):
        calls.append((root, path))
        if path.endswith("PROFILE_STRUCTURE_REPLAY.json"):
            return {"owners": []}
        if path.endswith("SECTOR_REPLAY.json"):
            return {"owners": []}
        if path.endswith("SOURCE_BINDINGS.json"):
            return {"sources": {"identity": {"path": "id", "sha256": "a" * 64}}}
        return {"thresholds": {}}

    monkeypatch.setattr(corrected_focus_replay, "pg_json_source", source)
    monkeypatch.setattr(
        "pathlib.Path.read_bytes",
        lambda _path: (_ for _ in ()).throw(AssertionError("workspace read")),
    )

    result = corrected_focus_replay.pg_focus_inputs(tmp_path, "input", "sector")
    assert result[0] == {"owners": []}
    assert result[1] == {"owners": []}
    assert result[2]["identity"]["path"] == "id"
    assert result[3] == {"thresholds": {}}
    assert calls == [
        (tmp_path, "input/PROFILE_STRUCTURE_REPLAY.json"),
        (tmp_path, "sector/SECTOR_REPLAY.json"),
        (tmp_path, "input/SOURCE_BINDINGS.json"),
        (tmp_path, "config/research_attention_v3.yaml"),
    ]


def test_corrected_owner_pipeline_rejects_workspace_only_receipt(monkeypatch, tmp_path):
    from workbench_analysis import corrected_owner_pipeline

    monkeypatch.setattr(
        corrected_owner_pipeline,
        "pg_json_source",
        lambda *_args: (_ for _ in ()).throw(
            ValueError("HISTORICAL_SOURCE_INGRESS_NOT_FOUND")
        ),
    )
    with pytest.raises(ValueError, match="UNINGRESSED_WORKSPACE_CANDIDATE_NOT_CONSUMABLE"):
        relative = "data/v4/workspaces/candidate/receipt.json"
        target = tmp_path / relative
        target.parent.mkdir(parents=True)
        target.write_text("{}", encoding="utf8")
        corrected_owner_pipeline._candidate_json(tmp_path, relative)


def test_corrected_owner_pipeline_rejects_stale_stage_dates_and_bindings():
    from workbench_analysis.corrected_owner_pipeline import (
        _health_profile_matches, _profile_core_matches, _require_candidate_days,
    )

    days = ["2026-09-28", "2026-09-29"]
    core = {"owners": [
        {"trade_date": day, "core": {"path": f"core/{day}", "sha256": day, "bytes": 10}}
        for day in days
    ]}
    profiles = {"owners": [
        {"owner": {"trade_date": day, "core": dict(core["owners"][i]["core"])},
         "advanced_projection": {"path": f"projection/{day}", "sha256": f"p-{day}", "bytes": 20}}
        for i, day in enumerate(days)
    ]}
    health = {"owners": [
        {"trade_date": day, "original_projection": dict(profiles["owners"][i]["advanced_projection"])}
        for i, day in enumerate(days)
    ]}

    assert _require_candidate_days(core, days, "core")
    assert not _require_candidate_days({"owners": core["owners"][:1]}, days, "core")
    assert _profile_core_matches(profiles, core)
    stale_profile = {"owners": [dict(profiles["owners"][0], owner=dict(profiles["owners"][0]["owner"],
                    core={"path": "core/old", "sha256": "old", "bytes": 10}))] + profiles["owners"][1:]}
    assert not _profile_core_matches(stale_profile, core)
    assert _health_profile_matches(health, profiles)
    stale_health = {"owners": [dict(health["owners"][0], original_projection={
        "path": "projection/old", "sha256": "old", "bytes": 20})] + health["owners"][1:]}
    assert not _health_profile_matches(stale_health, profiles)
