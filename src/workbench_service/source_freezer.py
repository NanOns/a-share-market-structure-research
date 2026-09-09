"""Immutable local source manifest and verification for M7B-03."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import duckdb

from common.input_snapshot import validate_input_snapshot_manifest


CONTRACT_VERSION = "history-source-manifest-v1.0"


class SourceFreezeError(RuntimeError):
    pass


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_hash(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("manifest_sha256", None)
    return _sha_bytes(_canonical(payload))


def build_source_manifest(
    *,
    publication_id: str,
    cutoff_date: str,
    source_revision_id: int,
    source_identity_sha256: str,
    source_snapshot_manifest_sha256: str,
    source_bundle_id: str,
    observed_at: str,
    window_plan: dict[str, Any],
    inputs: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Build a content-addressed manifest without copying or modifying inputs."""
    value = {
        "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id,
        "cutoff_date": str(cutoff_date),
        "source_revision_id": int(source_revision_id),
        "source_identity_sha256": source_identity_sha256,
        "source_snapshot_manifest_sha256": source_snapshot_manifest_sha256,
        "source_bundle_id": source_bundle_id,
        "observed_at": observed_at,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "effective_date": str(cutoff_date),
        "window": {
            "output_start": window_plan["output_start"],
            "output_end": window_plan["output_end"],
            "read_start": window_plan["read_start"],
            "read_end": window_plan["read_end"],
            "output_days": window_plan["output_days"],
            "required_history": window_plan["required_history"],
            "missing_dates": list(window_plan.get("missing_dates", [])),
        },
        "membership_policy": {
            "observed_sequence": "逐日封存快照优先",
            "current_snapshot_fallback": "CURRENT_SNAPSHOT_ONLY",
            "pit_safe": False,
            "note": "当前成员快照可用于固定成员回算，但不宣称历史PIT成员身份",
        },
        "inputs": sorted(list(inputs), key=lambda item: (item["role"], item["path"])),
    }
    value["manifest_sha256"] = _manifest_hash(value)
    return value


def validate_source_manifest(value: dict[str, Any]) -> bool:
    if value.get("contract_version") != CONTRACT_VERSION:
        raise SourceFreezeError("SOURCE_MANIFEST_CONTRACT_MISMATCH")
    if value.get("manifest_sha256") != _manifest_hash(value):
        raise SourceFreezeError("SOURCE_MANIFEST_HASH_MISMATCH")
    required = ("publication_id", "cutoff_date", "source_revision_id", "source_identity_sha256", "source_bundle_id", "observed_at", "window", "inputs")
    if any(key not in value for key in required):
        raise SourceFreezeError("SOURCE_MANIFEST_FIELD_MISSING")
    if value["window"].get("read_start") > value["window"].get("read_end"):
        raise SourceFreezeError("SOURCE_MANIFEST_WINDOW_INVALID")
    if not value["inputs"]:
        raise SourceFreezeError("SOURCE_MANIFEST_INPUTS_EMPTY")
    return True


def atomic_write_manifest(path: str | Path, value: dict[str, Any]) -> Path:
    validate_source_manifest(value)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing != value:
            raise SourceFreezeError("SOURCE_MANIFEST_IMMUTABLE_CONFLICT")
        return target
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(_canonical(value))
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def _safe_local_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    if Path(relative_path).is_absolute() or root not in candidate.parents:
        raise SourceFreezeError(f"SOURCE_PATH_OUTSIDE_WORKSPACE:{relative_path}")
    return candidate


def verify_source_manifest(root: str | Path, value: dict[str, Any]) -> dict[str, Any]:
    validate_source_manifest(value)
    root = Path(root).resolve()
    checked = 0
    mismatches = []
    for item in value["inputs"]:
        path = _safe_local_path(root, item["path"])
        if item["kind"] == "file":
            if not path.is_file():
                mismatches.append({"path": item["path"], "reason": "FILE_MISSING"})
            elif sha256_file(path) != item["sha256"]:
                mismatches.append({"path": item["path"], "reason": "SHA256_MISMATCH"})
            checked += 1
        elif item["kind"] == "directory":
            if not path.is_dir():
                mismatches.append({"path": item["path"], "reason": "DIRECTORY_MISSING"})
            elif "entry_count" in item and sum(1 for candidate in path.rglob("*") if candidate.is_file()) != item["entry_count"]:
                mismatches.append({"path": item["path"], "reason": "ENTRY_COUNT_MISMATCH"})
            checked += 1
        else:
            raise SourceFreezeError(f"SOURCE_INPUT_KIND_UNSUPPORTED:{item['kind']}")
    return {"status": "PASS" if not mismatches else "FAIL", "checked": checked, "mismatches": mismatches, "manifest_sha256": value["manifest_sha256"]}


def _file_input(root: Path, relative_path: str, role: str, observed_at: str, effective_date: str, date_scope: dict[str, Any], **extra: Any) -> dict[str, Any]:
    path = _safe_local_path(root, relative_path)
    if not path.is_file():
        raise SourceFreezeError(f"SOURCE_FILE_MISSING:{relative_path}")
    return {"path": relative_path, "kind": "file", "role": role, "sha256": sha256_file(path), "observed_at": observed_at, "effective_date": effective_date, "date_scope": date_scope, **extra}


class SourceFreezer:
    """Resolve a successful publication to already sealed local inputs."""

    METADATA_FILES = {
        "gbbq": "corporate_actions",
        "gbbq.map": "corporate_actions_map",
        "tdxhy.cfg": "sector_membership_source",
        "tdxzs.cfg": "sector_membership_source",
        "infoharbor_block.dat": "sector_membership_source",
        "shs.tnf": "security_metadata",
        "szs.tnf": "security_metadata",
        "bjs.tnf": "security_metadata",
    }

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else self.root / "data/database/market_research.duckdb"

    def _publication(self, publication_id: str) -> tuple[str, int, str]:
        with duckdb.connect(str(self.database_path)) as connection:
            row = connection.execute("select cast(trade_date as varchar),source_revision_id,source_identity_sha256 from publications where publication_id=? and status='SUCCESS'", [publication_id]).fetchone()
            if not row:
                raise SourceFreezeError("PUBLICATION_NOT_FOUND")
        cutoff, revision, identity = row
        if revision is None or not identity or len(str(identity)) != 64:
            raise SourceFreezeError("PUBLICATION_SOURCE_REVISION_MISSING")
        return cutoff, int(revision), identity

    def _snapshot(self, cutoff: str, revision: int, identity: str) -> dict[str, Any]:
        matches = []
        for path in (self.root / "reports/revisions" / cutoff.replace("-", "")).glob("revision-*/INPUT_SNAPSHOT_MANIFEST.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            if int(value.get("source_revision_id", -1)) == revision and value.get("source_identity", {}).get("sha256") == identity:
                matches.append(value)
        if not matches:
            raise SourceFreezeError("INPUT_SNAPSHOT_NOT_FOUND")
        value = sorted(matches, key=lambda item: item["snapshot_manifest_sha256"])[-1]
        validate_input_snapshot_manifest(value)
        return value

    def _bundle(self, bundle_id: str) -> dict[str, Any]:
        path = self.root / "data/source_bundles" / bundle_id / "source_bundle.json"
        if not path.is_file():
            raise SourceFreezeError("SOURCE_BUNDLE_RECEIPT_MISSING")
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("source_bundle_id") != bundle_id or value.get("read_only") is not True:
            raise SourceFreezeError("SOURCE_BUNDLE_NOT_READ_ONLY")
        return value

    def _matching_bundle(self, cutoff: str, snapshot: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        expected = snapshot.get("source_identity", {}).get("components", {})
        with duckdb.connect(str(self.database_path)) as connection:
            rows = connection.execute("select source_bundle_id,payload_json from source_bundles").fetchall()
        matches = []
        for bundle_id, raw in rows:
            value = json.loads(raw)
            files = value.get("metadata", {}).get("files", {})
            if value.get("target_trade_date") != cutoff:
                continue
            if all(files.get(f"T0002/hq_cache/{name}", {}).get("sha256") == expected.get(component) for name, component in (("gbbq", "gbbq"), ("gbbq.map", "gbbq_map"), ("shs.tnf", "sh_tnf"), ("szs.tnf", "sz_tnf"), ("bjs.tnf", "bj_tnf"))):
                matches.append((bundle_id, value))
        if not matches:
            raise SourceFreezeError("SOURCE_BUNDLE_IDENTITY_NOT_FOUND")
        return sorted(matches, key=lambda item: item[0])[-1]

    def freeze(self, publication_id: str, window_plan: dict[str, Any], *, output_path: str | Path | None = None) -> dict[str, Any]:
        cutoff, revision, identity = self._publication(publication_id)
        snapshot = self._snapshot(cutoff, revision, identity)
        bundle_id, bundle = self._matching_bundle(cutoff, snapshot)
        observed_at = snapshot["observed_at"]
        effective_date = cutoff
        scope = {"from": window_plan["read_start"], "to": window_plan["read_end"]}
        inputs = [
            _file_input(self.root, "data/source_bundles/" + bundle_id + "/source_bundle.json", "source_bundle_receipt", observed_at, effective_date, {"as_of": cutoff}),
            _file_input(self.root, "data/normalized/adjusted_daily.parquet", "normalized_raw_price", observed_at, effective_date, scope, price_basis="FORWARD_ADJUSTED / TDX_NATIVE_QFQ"),
            _file_input(self.root, "data/sectors/sector_membership_daily.parquet", "current_membership_snapshot", observed_at, effective_date, {"as_of": cutoff, "mode": "CURRENT_SNAPSHOT_ONLY"}, pit_safe=False),
            _file_input(self.root, "config/trading_calendar.yaml", "master_calendar", observed_at, effective_date, scope),
        ]
        metadata_root = Path(bundle["metadata"]["root"])
        for filename, role in self.METADATA_FILES.items():
            relative = str(metadata_root / "T0002/hq_cache" / filename).replace("\\", "/")
            inputs.append(_file_input(self.root, relative, role, observed_at, effective_date, {"as_of": cutoff}, source_bundle_id=bundle_id))
        extracted_root = str(Path(bundle["extraction"]["root"])).replace("\\", "/")
        extracted_path = _safe_local_path(self.root, extracted_root)
        if not extracted_path.is_dir():
            raise SourceFreezeError("SOURCE_EXTRACTION_ROOT_MISSING")
        inputs.append({"path": extracted_root, "kind": "directory", "role": "raw_day_source", "entry_count": int(bundle["extraction"]["entry_count"]), "source_bundle_id": bundle_id, "source_bundle_sha256": bundle["package"]["sha256"], "observed_at": observed_at, "effective_date": effective_date, "date_scope": scope})
        result = build_source_manifest(
            publication_id=publication_id,
            cutoff_date=cutoff,
            source_revision_id=revision,
            source_identity_sha256=identity,
            source_snapshot_manifest_sha256=snapshot["snapshot_manifest_sha256"],
            source_bundle_id=bundle_id,
            observed_at=observed_at,
            window_plan=window_plan,
            inputs=inputs,
        )
        if output_path is not None:
            atomic_write_manifest(output_path, result)
        return result
