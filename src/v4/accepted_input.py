"""Fail-closed resolver for the accepted V4-04 input chain."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path


CUTOFF = "2026-09-24"
BOARDS = ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")


@dataclass(frozen=True)
class AcceptedInput:
    path: Path
    sha256: str
    contract_id: str


def _verify(root: Path, relative: str, digest: str) -> Path:
    from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_bound
    path = materialize_bound(root, {"path": relative, "sha256": digest})
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != digest:
        raise ValueError(f"accepted input hash mismatch: {relative}")
    return path


def _json(root: Path, relative: str, digest: str | None = None) -> dict:
    if digest:
        path = _verify(root, relative, digest)
    else:
        from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_path
        path = materialize_path(root, relative)
    return json.loads(path.read_text(encoding="utf-8"))


def _find_bound_document(root: Path, bindings: dict, contract_id: str) -> tuple[dict, dict]:
    """Resolve one receipt by its typed PG-ingressed identity, never by a report path."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
    matches = []
    for binding in bindings.values():
        if not isinstance(binding, dict) or not binding.get("path") or not binding.get("sha256"):
            continue
        try:
            raw = read_bound(root, binding["path"], binding["sha256"])["raw"]
            value = json.loads(raw)
        except (OSError, UnicodeDecodeError, ValueError, TypeError):
            continue
        if isinstance(value, dict) and value.get("contract_id") == contract_id:
            matches.append((binding, value))
    if len(matches) != 1:
        raise ValueError("ACCEPTED_TYPED_EVIDENCE_NOT_UNIQUE:" + contract_id)
    return matches[0]


def _artifact_binding(artifacts: dict, filename: str) -> dict:
    matches = [(path, digest) for path, digest in artifacts.items()
               if Path(path).name == filename]
    if len(matches) != 1:
        raise ValueError("ACCEPTED_ARTIFACT_NOT_UNIQUE:" + filename)
    path, digest = matches[0]
    return {"path": path, "sha256": digest}


def resolve(root: Path) -> dict[str, AcceptedInput]:
    """Resolve only paths named by accepted heads and their hash-bound receipts."""
    root = root.resolve()
    stage = _json(root, "data/v4/V4_STAGE_ACCEPTED_HEAD.json")
    if (stage.get("status") != "FOUNDATION_FULL_PASS" or
            stage.get("v4_04_entry") not in {"AUTHORIZED_FULL_CHAIN", "COMPLETED_EXTERNALLY_ACCEPTED"} or
            stage.get("v4_03_status") != "FULL_PASS_AMENDED_SCOPE"):
        raise ValueError("V4-04 accepted entry authority missing")
    bindings = stage["bindings"]
    v401 = _json(root, bindings["v4_01_accepted_head"]["path"], bindings["v4_01_accepted_head"]["sha256"])
    v402 = _json(root, bindings["v4_02_accepted_head"]["path"], bindings["v4_02_accepted_head"]["sha256"])
    v403_ref = stage["v4_03_binding"]
    v403 = _json(root, v403_ref["path"], v403_ref["sha256"])
    expected_contracts = (
        (v401, "V4_01_ACCEPTED_HEAD_V1"),
        (v402, "V4_02_ACCEPTED_HEAD_V1"),
        (v403, "V4_03_ACCEPTED_HEAD_AMENDED_V1"),
    )
    if any(head.get("contract_id") != contract for head, contract in expected_contracts):
        raise ValueError("accepted upstream contract mismatch")
    if any(x.get("source_cutoff") != CUTOFF for x in (v401, v402, v403)):
        raise ValueError("accepted source cutoff mismatch")
    if v403.get("external_acceptance") != "EXTERNALLY_ACCEPTED" or v402.get("external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise ValueError("upstream external acceptance missing")
    if v401.get("external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise ValueError("V4-01 external acceptance missing")
    manifest = _json(root, v402["manifest_path"], v402["manifest_sha256"])
    receipt_ref = manifest["components"]["R4_ACCEPTANCE"]
    r4_receipt = _json(root, receipt_ref["path"], receipt_ref["sha256"])
    r4_manifest_ref = r4_receipt["evidence"]["manifest"]
    r4_manifest = _json(root, r4_manifest_ref["path"], r4_manifest_ref["sha256"])
    v403_receipt_ref, v403_receipt = _find_bound_document(
        root, v403["evidence_bindings"], "V4_03_FINAL_STAGE_RECEIPT_R1")
    if v403_receipt["capabilities"]["STOCK_CORE"] != "PASS":
        raise ValueError("V4-03 stock core not accepted")
    items = {
        "daily": (manifest["components"]["DAILY_R7"], "V4_02_CANONICAL_DAILY"),
        "weekly": (r4_manifest["components"]["FORMAL_WEEKLY_R7"], "V4_02_FORMAL_WEEKLY"),
        "monthly": (r4_manifest["components"]["FORMAL_MONTHLY_R7"], "V4_02_FORMAL_MONTHLY"),
        "calendar": (manifest["components"]["CALENDAR"], "V4_02_CALENDAR"),
        "calendar_szse": (r4_manifest["components"]["FORMAL_CALENDAR_SZSE"], "V4_02_CALENDAR_SZSE"),
        "trading_status": (r4_manifest["components"]["DATED_TRADING_STATUS_R7"], "V4_02_TRADING_STATUS"),
        "universe": (bindings["v4_01_universe"], "V4_01_HISTORICAL_UNIVERSE"),
    }
    items["factors"] = (_artifact_binding(v403_receipt["hashes"]["artifacts"],
        "V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz"), "V4_03_STOCK_CORE")
    items["market_regime"] = (_artifact_binding(v403_receipt["hashes"]["artifacts"],
        "V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"), "MARKET_REGIME_V1_PRIMITIVES")
    return {name: AcceptedInput(_verify(root, ref["path"], ref["sha256"]), ref["sha256"], contract)
            for name, (ref, contract) in items.items()}
