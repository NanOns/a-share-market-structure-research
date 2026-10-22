import json
from pathlib import Path

import pytest

from workbench_analysis.r43_owner_replay import ref
from workbench_service import native_product_catalog_v3
from workbench_service.core_product_bff_r1 import CoreProductBFFR1


class _CandidateAPI:
    def __init__(self, root, candidate, scope="DEVELOPMENT_CANDIDATE_PREVIEW"):
        self.root = root
        self.candidate = candidate
        self.cache = {}
        self.token = "candidate-token"
        self._scope = scope

    def context(self):
        return {"read_scope": self._scope}


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _candidate_pack(tmp_path):
    day = "2026-10-21"
    root = tmp_path
    head_path = root / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
    _write(head_path, json.dumps({"accepted_trade_date": day}).encode())
    owner_dir = root / "data/v4/dynamic_daily_owners" / day / "owner-v1"
    core_path = owner_dir / "core.jsonl.gz"
    history_path = owner_dir / "history.jsonl.gz"
    raw_path = owner_dir / "raw.jsonl.gz"
    market_path = owner_dir / "market.json"
    facts_path = root / "data/v4/product/market-facts.json"
    for path, data in ((core_path, b"core"), (history_path, b"history"),
                       (raw_path, b"raw"), (market_path, b"market")):
        _write(path, data)
    _write(facts_path, b"{}")

    owners = {name: ref(root, path) for name, path in {
        "core": core_path, "raw": raw_path, "market": market_path,
    }.items()}
    manifest = {
        "contract_id": "CORE_PRODUCT_DATED_READ_PACK_PG_R1",
        "authority_scope": "DEVELOPMENT_CANDIDATE_EXACT_DATE",
        "T0": day,
        "head": ref(root, head_path),
        "fact_token": "a" * 64,
        "source_bindings": {
            "core": owners["core"], "raw": owners["raw"],
            "market": owners["market"], "history": ref(root, history_path),
        },
        "history_index": {
            "engine": "postgresql", "T0": day, "head_token": "a" * 64,
        },
        "market_facts": ref(root, facts_path),
    }
    manifest_path = root / "data/v4/product/manifest.json"
    _write(manifest_path, json.dumps(manifest).encode())
    authority = {"contract_id": "CORE_PRODUCT_READ_AUTHORITY_R2",
                 "dates": {day: ref(root, manifest_path)}}
    _write(root / "config/core_product_read_authority_r1.json",
           json.dumps(authority).encode())
    candidate = {"exact_daily_adjustment_contract": True,
                 "owners": {day: owners}}
    return root, candidate, day


def test_candidate_pack_accepts_exact_date_and_core_sibling_history(tmp_path, monkeypatch):
    root, candidate, day = _candidate_pack(tmp_path)
    monkeypatch.setattr(native_product_catalog_v3, "load",
                        lambda *_: (_ for _ in ()).throw(
                            ValueError("EMBEDDED_PRODUCT_CATALOG_REQUIRED_NO_FALLBACK")))

    result = CoreProductBFFR1(_CandidateAPI(root, candidate), object()).pack(day)

    assert result[0]["T0"] == day
    assert result[0]["authority_scope"] == "DEVELOPMENT_CANDIDATE_EXACT_DATE"


def test_candidate_pack_rejects_cross_date_history_binding(tmp_path, monkeypatch):
    root, candidate, day = _candidate_pack(tmp_path)
    monkeypatch.setattr(native_product_catalog_v3, "load",
                        lambda *_: (_ for _ in ()).throw(
                            ValueError("EMBEDDED_PRODUCT_CATALOG_REQUIRED_NO_FALLBACK")))
    manifest_path = root / "data/v4/product/manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["source_bindings"]["history"]["path"] = "data/v4/other-date/history.jsonl.gz"
    _write(manifest_path, json.dumps(manifest).encode())
    authority_path = root / "config/core_product_read_authority_r1.json"
    authority = json.loads(authority_path.read_bytes())
    authority["dates"][day] = ref(root, manifest_path)
    _write(authority_path, json.dumps(authority).encode())

    with pytest.raises(ValueError, match="CANDIDATE_PRODUCT_OWNER_BINDING_MISMATCH:history"):
        CoreProductBFFR1(_CandidateAPI(root, candidate), object()).pack(day)


def test_candidate_pack_fallback_is_for_development_scope_only(tmp_path, monkeypatch):
    root, candidate, day = _candidate_pack(tmp_path)
    monkeypatch.setattr(native_product_catalog_v3, "load",
                        lambda *_: (_ for _ in ()).throw(
                            ValueError("EMBEDDED_PRODUCT_CATALOG_REQUIRED_NO_FALLBACK")))

    with pytest.raises(ValueError, match="EMBEDDED_PRODUCT_CATALOG_REQUIRED_NO_FALLBACK"):
        CoreProductBFFR1(_CandidateAPI(root, candidate, "FORMAL"), object()).pack(day)
