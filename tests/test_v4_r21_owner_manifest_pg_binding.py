import hashlib
import json
from pathlib import Path

import pytest

from workbench_analysis.r43_owner_replay import ref
from workbench_db import v4_operational_owner_authority_v2 as authority_module
from workbench_db import v4_operational_owner_pg_closeout as closeout_module
from workbench_db.v4_forward_pg_r1 import canonical, digest


DAY = "2026-10-16"
SOURCE = {"path": "source.json", "sha256": "a" * 64, "bytes": 1}
OWNER_BINDING = {
    "descriptor": {"path": "owner.pg.json", "sha256": "b" * 64, "bytes": 2,
                    "pg_descriptor": {"kind": "raw", "fact_key": "fact"}},
    "fact_token": "c" * 64,
}


def _candidate():
    return {"owners": {DAY: {"raw": SOURCE}}}


def _authority(candidate):
    return {
        "contract_id": authority_module.CONTRACT,
        "owner_source_digest": digest(canonical(candidate["owners"])),
        "source_owners": candidate["owners"],
        "owners": {DAY: {"raw": OWNER_BINDING}},
        "historical_PIT_permission": False,
        "AS_RECORDED": False,
        "PIT_ELIGIBLE": False,
    }


def test_active_owner_authority_load_reads_pg_manifest_and_never_opens_authority_json(monkeypatch, tmp_path):
    candidate = _candidate()
    candidate[authority_module.KEY] = {"path": "authority.pg.json", "sha256": "d" * 64, "bytes": 3}
    payload = _authority(candidate)
    monkeypatch.setattr(authority_module, "read_authority_manifest", lambda root, binding: payload)
    monkeypatch.setattr(authority_module, "descriptor_metadata", lambda root, binding: {})
    monkeypatch.setattr(authority_module, "checked", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("file authority read")))

    assert authority_module.load(tmp_path, candidate) == payload


def test_owner_authority_prepare_appends_pg_manifest_without_authority_json(monkeypatch, tmp_path):
    source_path = tmp_path / "source.json"
    source_path.write_text('{"rows":[]}', encoding="utf-8")
    candidate = {"owners": {DAY: {"raw": ref(tmp_path, source_path)}}}
    monkeypatch.setattr(authority_module, "append", lambda *args, **kwargs: {"path": "owner.pg.json", "sha256": "a" * 64, "bytes": 4})
    monkeypatch.setattr(authority_module, "read_fact", lambda *args, **kwargs: [{"security_id": "X"}])
    monkeypatch.setattr("workbench_analysis.r43_operational_publication.rows", lambda root, binding: [{"security_id": "X"}])
    written = []

    class Store:
        def __init__(self, root, folder):
            pass

        def append(self, kind, key, payload):
            written.append((kind, key, payload))
            return {"path": "manifest.pg.json", "sha256": "e" * 64, "bytes": 5}

    monkeypatch.setattr(authority_module, "ForwardFactStore", Store)
    monkeypatch.setattr(authority_module, "inline_descriptor", lambda root, binding: {**binding, "pg_descriptor": {"kind": "authority_manifest"}})

    binding, receipt = authority_module.prepare(tmp_path, candidate)

    assert binding["pg_descriptor"]["kind"] == "authority_manifest"
    assert written[0][0] == "authority_manifest"
    assert written[0][1] == hashlib.sha256(canonical(written[0][2])).hexdigest()
    assert receipt["counts"] == {"reused": 0, "created": 1}
    assert not list(tmp_path.rglob("AUTHORITY.json"))


def test_pg_manifest_reader_checks_database_identity_and_payload_digest(monkeypatch, tmp_path):
    raw = json.dumps({"contract_id": authority_module.CONTRACT}, separators=(",", ":"))
    payload_sha = hashlib.sha256(raw.encode()).hexdigest()
    descriptor = {
        "contract_id": closeout_module.CONTRACT,
        "engine": "postgresql",
        "database_identity": {"database": "market_research", "database_oid": 42, "host": "127.0.0.1", "port": 5432},
        "schema": "v4_forward_aaaaaaaaaaaaaaaa",
        "kind": "authority_manifest",
        "fact_key": "key",
        "payload_sha256": payload_sha,
    }
    binding = {"path": "unused", "sha256": "f" * 64, "bytes": 5}
    monkeypatch.setattr(closeout_module, "descriptor_metadata", lambda *args, **kwargs: descriptor)
    monkeypatch.setattr(closeout_module, "read_schema", lambda *args, **kwargs: descriptor["schema"])
    monkeypatch.setattr(closeout_module.ForwardFactStore, "_database_identity", staticmethod(lambda pg: descriptor["database_identity"]))

    class PG:
        def execute(self, query, params):
            assert "forward_facts" in query
            assert params == ("authority_manifest", "key")
            return self

        def fetchone(self):
            return raw, payload_sha

    class Connection:
        def __enter__(self):
            return PG()

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(closeout_module, "connection", lambda *args, **kwargs: Connection())
    assert closeout_module.read_authority_manifest(tmp_path, binding) == {"contract_id": authority_module.CONTRACT}


def test_pg_manifest_reader_rejects_payload_digest_mismatch(monkeypatch, tmp_path):
    descriptor = {
        "contract_id": closeout_module.CONTRACT, "engine": "postgresql",
        "database_identity": {}, "schema": "v4_forward_aaaaaaaaaaaaaaaa",
        "kind": "authority_manifest", "fact_key": "key", "payload_sha256": "0" * 64,
    }
    monkeypatch.setattr(closeout_module, "descriptor_metadata", lambda *args, **kwargs: descriptor)
    monkeypatch.setattr(closeout_module, "read_schema", lambda *args, **kwargs: descriptor["schema"])
    monkeypatch.setattr(closeout_module.ForwardFactStore, "_database_identity", staticmethod(lambda pg: {}))

    class PG:
        def execute(self, query, params):
            return self

        def fetchone(self):
            return "{}", "0" * 64

    class Connection:
        def __enter__(self):
            return PG()

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(closeout_module, "connection", lambda *args, **kwargs: Connection())
    with pytest.raises(ValueError, match="PG_OPERATIONAL_OWNER_AUTHORITY_PAYLOAD_DIGEST_MISMATCH"):
        closeout_module.read_authority_manifest(tmp_path, {"path": "unused"})
