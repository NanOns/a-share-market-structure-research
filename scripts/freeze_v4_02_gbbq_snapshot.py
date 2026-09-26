from __future__ import annotations

"""Freeze the first immutable, hash-bound go-forward TDX GBBQ source snapshot."""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "gbbq": "f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1",
    "gbbq.map": "f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, name)
        with open(name, "rb+") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache")
    parser.add_argument("--source-evidence", default="reports/v4_00d/v4_00d_asset_stratified_postcheck_20260925.json")
    parser.add_argument("--store", default="data/v4/source_snapshot_store/gbbq")
    parser.add_argument("--receipt", default="reports/v4_02/V4_02_GBBQ_FORWARD_SNAPSHOT_FREEZE_20260926.json")
    args = parser.parse_args()
    source_dir = ROOT / args.source_dir
    evidence = json.loads((ROOT / args.source_evidence).read_text(encoding="utf-8"))
    if evidence.get("local_snapshot_identity", {}).get("metadata_sha256") != {
        **evidence["local_snapshot_identity"]["metadata_sha256"], **EXPECTED
    }:
        raise SystemExit("LOCAL_GBBQ_SOURCE_HASH_EVIDENCE_MISMATCH")
    observed = datetime.now(timezone.utc).replace(microsecond=0)
    snapshot_id = "sha256-" + hashlib.sha256((EXPECTED["gbbq"] + EXPECTED["gbbq.map"] + observed.isoformat()).encode()).hexdigest()
    root = ROOT / args.store / snapshot_id
    if root.exists():
        raise SystemExit("IMMUTABLE_SNAPSHOT_ID_ALREADY_EXISTS")
    root.mkdir(parents=True, exist_ok=False)
    try:
        for name in ("gbbq", "gbbq.map"):
            source, destination = source_dir / name, root / name
            if sha256(source) != EXPECTED[name]:
                raise SystemExit("SOURCE_GBBQ_HASH_MISMATCH:" + name)
            copy_atomic(source, destination)
            if sha256(destination) != EXPECTED[name]:
                raise SystemExit("FROZEN_GBBQ_HASH_MISMATCH:" + name)
            destination.chmod(0o444)
        available_at = observed.isoformat().replace("+00:00", "Z")
        manifest = {
            "contract_id": "V4_02_GBBQ_FORWARD_SNAPSHOT_V1",
            "snapshot_id": snapshot_id,
            "publication_id": "V4_02_GBBQ_SNAPSHOT_" + observed.strftime("%Y%m%dT%H%M%SZ"),
            "observed_at": available_at,
            "ingested_at": available_at,
            "system_available_at": available_at,
            "trade_date_eligibility": "ONLY_TRADE_DATES_STRICTLY_AFTER_SYSTEM_AVAILABLE_AT",
            "source_trade_date_cutoff": "2026-09-24",
            "first_eligible_formal_trade_date": "2026-09-28",
            "files": {name: {"path": name, "sha256": EXPECTED[name], "bytes": (root / name).stat().st_size}
                      for name in ("gbbq", "gbbq.map")},
            "source_evidence": {"path": args.source_evidence, "sha256": sha256(ROOT / args.source_evidence)},
            "source_local_snapshot_sha256": evidence["local_snapshot_identity"]["snapshot_sha256"],
            "lineage_permission": "PIT_OBSERVED_ELIGIBLE_FROM_FIRST_FORMAL_PUBLICATION_AFTER_SYSTEM_AVAILABLE_AT",
            "historical_effective_dates_before_availability": "DIAGNOSTIC_NON_PIT_ONLY",
            "immutable": True,
        }
        manifest_path = root / "manifest.json"
        fd, name = tempfile.mkstemp(prefix="manifest.", suffix=".tmp", dir=root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(manifest, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, manifest_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        manifest_path.chmod(0o444)
        receipt = {
            "contract_id": "V4_02_GBBQ_FORWARD_SNAPSHOT_FREEZE_RECEIPT_V1",
            "status": "GO_FORWARD_SNAPSHOT_FROZEN",
            "snapshot_id": snapshot_id,
            "manifest_path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(manifest_path),
            "system_available_at": available_at,
            "first_eligible_formal_trade_date": manifest["first_eligible_formal_trade_date"],
            "file_hashes": EXPECTED,
            "historical_pit_claim": "NOT_CLAIMED",
        }
        receipt_path = ROOT / args.receipt
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=receipt_path.name + ".", suffix=".tmp", dir=receipt_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(receipt, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, receipt_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        print(json.dumps({"status": "GO_FORWARD_SNAPSHOT_FROZEN", "snapshot_id": snapshot_id,
                          "system_available_at": available_at, "manifest": str(manifest_path),
                          "receipt": str(receipt_path)}, ensure_ascii=False))
        return 0
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
