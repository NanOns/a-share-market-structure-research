"""Offline boundary tests for PG-only correction authority manifests."""
import json

from workbench_analysis.r43_owner_replay import ref
from workbench_db import v4_profile_dependent_corrections_pg_v1 as dependent
from workbench_db import v4_profile_semantic_corrections_pg_v1 as semantic


def _pg_binding(kind, fact_key):
    return {
        "path": f"data/v4/operational_owner_pg_closeout_r1/{kind}/manifest.pg.json",
        "sha256": "a" * 64,
        "bytes": 1,
        "pg_descriptor": {
            "contract_id": "V4_FORWARD_PG_FACT_STORE_R1",
            "engine": "postgresql",
            "schema": "v4_forward_test",
            "kind": kind,
            "fact_key": fact_key,
            "payload_sha256": "b" * 64,
            "database_identity": {"database": "market_research", "database_oid": 1,
                                  "host": "127.0.0.1", "port": 5432},
        },
    }


def test_semantic_correction_manifest_is_persisted_and_loaded_via_pg(monkeypatch, tmp_path):
    day = "2026-10-12"
    source_path = tmp_path / "source.json"
    source_path.write_text("{}", encoding="utf-8")
    source = ref(tmp_path, source_path)
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(json.dumps({
        "contract_id": semantic.CONTRACT,
        "T0": day,
        "original_profile": {"path": "profile.json"},
        "source": source,
        "rows": [],
        "publication_ready": False,
        "PIT_ELIGIBLE": False,
        "AS_RECORDED": False,
    }), encoding="utf-8")
    patch = ref(tmp_path, patch_path)
    candidate = {"owners": {day: {"profile": {"path": "profile.json"}}}}
    fact_binding = _pg_binding("reference_profile_semantic_corrections", "fact")
    manifest_binding = _pg_binding("authority_manifest", "manifest")
    persisted = {}

    monkeypatch.setattr(semantic, "append", lambda *args, **kwargs: fact_binding)
    monkeypatch.setattr(semantic, "read_fact", lambda *args, **kwargs: [])
    monkeypatch.setattr(semantic, "inline_descriptor", lambda root, binding: binding)
    def append_manifest(root, value):
        persisted.update(value)
        return manifest_binding
    monkeypatch.setattr(semantic, "append_authority_manifest", append_manifest)

    semantic.prepare(tmp_path, candidate, {day: patch})
    assert candidate[semantic.KEY] == manifest_binding
    assert persisted["dates"][day]["descriptor"] == fact_binding
    assert not list(tmp_path.rglob("AUTHORITY.json"))

    monkeypatch.setattr(semantic, "read_authority_manifest",
                        lambda root, binding: persisted if binding == manifest_binding else None)
    monkeypatch.setattr(semantic, "descriptor_metadata", lambda root, binding: binding["pg_descriptor"])
    assert semantic.load(tmp_path, candidate) == persisted


def test_dependent_correction_manifest_is_persisted_and_loaded_via_pg(monkeypatch, tmp_path):
    day = "2026-10-12"
    source_path = tmp_path / "source.json"
    source_path.write_text("{}", encoding="utf-8")
    source = ref(tmp_path, source_path)
    patch_bindings = {}
    patches = {}
    for domain in ("focus", "prewatch"):
        path = tmp_path / f"{domain}.json"
        path.write_text(json.dumps({
            "contract_id": dependent.CONTRACT,
            "T0": day,
            "domain": domain,
            "original": {"path": f"{domain}-owner.json"},
            "source": source,
            "rows": [],
            "publication_ready": False,
        }), encoding="utf-8")
        patches[domain] = ref(tmp_path, path)
        patch_bindings[domain] = _pg_binding(f"reference_profile_dependent_{domain}", domain)
    candidate = {
        "owners": {day: {domain: {"path": f"{domain}-owner.json"}
                         for domain in ("focus", "prewatch")}},
        semantic.KEY: {"path": "profile-authority", "sha256": "c" * 64, "bytes": 1},
    }
    manifest_binding = _pg_binding("authority_manifest", "dependent-manifest")
    persisted = {}

    monkeypatch.setattr(dependent, "append",
                        lambda root, token, trade_day, kind, binding, rows: patch_bindings[kind.rsplit("_", 1)[-1]])
    monkeypatch.setattr(dependent, "read_fact", lambda *args, **kwargs: [])
    monkeypatch.setattr(dependent, "inline_descriptor", lambda root, binding: binding)
    def append_manifest(root, value):
        persisted.update(value)
        return manifest_binding
    monkeypatch.setattr(dependent, "append_authority_manifest", append_manifest)
    dependent.prepare(tmp_path, candidate, {day: patches})

    assert candidate[dependent.KEY] == manifest_binding
    assert not list(tmp_path.rglob("AUTHORITY.json"))
    monkeypatch.setattr(dependent, "read_authority_manifest",
                        lambda root, binding: persisted if binding == manifest_binding else None)
    monkeypatch.setattr(dependent, "descriptor_metadata", lambda root, binding: binding["pg_descriptor"])
    monkeypatch.setattr(semantic, "load", lambda root, value: {})
    assert dependent.load(tmp_path, candidate) == persisted
