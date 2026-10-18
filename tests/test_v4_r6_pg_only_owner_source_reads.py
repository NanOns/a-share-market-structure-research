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
