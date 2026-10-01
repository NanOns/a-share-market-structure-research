"""Append-only PIT observations. No accepted consumer or DM01 publication writes."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import uuid

CONTRACT = "A03_FORWARD_PIT_OBSERVATION_LEDGER_R2"
DETECTORS = ("MISSING_EXPECTED_SOURCE", "LATE_SOURCE", "SOURCE_REVISION", "SCHEMA_DRIFT",
             "DUPLICATE_CAPTURE", "TARGET_DATE_MISMATCH", "CALENDAR_GAP", "IDENTITY_GAP")


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def instant(value):
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return t


def atomic(path, raw, *, immutable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        if path.read_bytes() != raw:
            raise ValueError("IMMUTABLE_PUBLICATION_CONFLICT")
        return
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with tmp.open("xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        if immutable:
            # Exclusive publication: no revision race can replace existing bytes.
            try:
                os.link(tmp, path)
            except FileExistsError:
                if path.read_bytes() != raw:
                    raise ValueError("IMMUTABLE_PUBLICATION_CONFLICT")
        else:
            os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def bound(root, ref):
    root = Path(root).resolve()
    path = (root / ref["path"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("SOURCE_OUTSIDE_PROJECT")
    raw = path.read_bytes()
    if digest(raw) != ref["sha256"] or len(raw) != ref.get("bytes", ref.get("byte_count")):
        raise ValueError("SOURCE_BINDING_MISMATCH")
    return raw


def reference(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "sha256": digest(raw), "bytes": len(raw)}


def publications(root, ledger):
    result = []
    for path in sorted((Path(root) / ledger / "publications").glob("*.json")):
        raw = path.read_bytes()
        item = json.loads(raw)
        identity = dict(item)
        identity.pop("publication_id")
        if digest(canonical(identity)) != item["publication_id"] or path.stem != item["publication_id"]:
            raise ValueError("PUBLICATION_IDENTITY_MISMATCH")
        for ref in item["sources"].values():
            bound(root, ref["bytes_binding"])
        bound(root, item["calendar_binding"])
        bound(root, item["identity_binding"])
        result.append(item)
    return result


def append_observation(root, ledger, envelope, *, failure_after_publication=False):
    """Retry identity uses immutable capture_id; latest is an independently rebuilt projection."""
    root = Path(root).resolve()
    destination = (root / ledger).resolve()
    if not destination.is_relative_to(root) or "new_tdx" in destination.parts:
        raise ValueError("LEDGER_DESTINATION_INVALID")
    prior = publications(root, ledger)
    capture_id = envelope["capture_id"]
    matching = [p for p in prior if p["capture_id"] == capture_id]
    if matching:
        if matching[0]["capture_envelope_digest"] != digest(canonical(envelope)):
            raise ValueError("CAPTURE_ID_CONFLICT")
        rebuild_latest(root, ledger)
        return {"publication": matching[0], "detectors": ["DUPLICATE_CAPTURE"], "retry": True}
    observed, received = instant(envelope["observed_at"]), instant(envelope["received_at"])
    if received < observed:
        raise ValueError("RECEIVED_BEFORE_OBSERVED")
    calendar = json.loads(bound(root, envelope["calendar_binding"]))
    bound(root, envelope["identity_binding"])
    sessions = calendar.get("session_dates", [])
    if sessions != sorted(set(sessions)):
        raise ValueError("CALENDAR_NOT_ORDERED_UNIQUE")
    target = envelope["target_trade_date"]
    if target > received.date().isoformat():
        raise ValueError("FUTURE_TARGET")
    detectors = []
    if target not in sessions:
        detectors.append("CALENDAR_GAP")
    if not envelope.get("identity_complete", False):
        detectors.append("IDENTITY_GAP")
    sources = {}
    expected = sorted(set(envelope["expected_source_families"]))
    for family in expected:
        source = envelope["sources"].get(family)
        if source is None:
            detectors.append("MISSING_EXPECTED_SOURCE")
            continue
        raw = bound(root, source["bytes_binding"])
        if not source.get("source_revision"):
            raise ValueError("SOURCE_REVISION_REQUIRED")
        if source["target_trade_date"] != target:
            detectors.append("TARGET_DATE_MISMATCH")
        if source["schema_id"] != envelope["expected_schema_ids"][family]:
            detectors.append("SCHEMA_DRIFT")
        available = instant(source["received_at"])
        if not observed <= available <= received:
            raise ValueError("CAPTURE_SOURCE_TIME_OUTSIDE_OBSERVATION")
        old = [p for p in prior if p["target_trade_date"] == target and family in p["sources"]]
        if old and any(p["sources"][family]["source_revision"] != source["source_revision"] for p in old):
            detectors.append("SOURCE_REVISION")
        if available > instant(envelope["expected_available_by"]):
            detectors.append("LATE_SOURCE")
        prior_same = [p["sources"][family]["first_available_at"] for p in old
                      if p["sources"][family]["source_revision"] == source["source_revision"]
                      and p["sources"][family]["bytes_binding"] == source["bytes_binding"]]
        earliest = min(prior_same + [source["received_at"]], key=instant)
        sources[family] = dict(source, first_available_at=earliest, source_byte_count=len(raw))
    previous_targets = {p["target_trade_date"] for p in prior if p["target_trade_date"] in sessions}
    if target in sessions and previous_targets:
        last = max(previous_targets)
        if target > last and sessions.index(target) > sessions.index(last) + 1:
            detectors.append("CALENDAR_GAP")
    reasons = sorted(set(detectors))
    lineage = "RECONSTRUCTED_CORRECTED" if target < observed.date().isoformat() else "OBSERVED_AT_CAPTURE"
    item = {"contract_id": CONTRACT, "capture_id": capture_id, "capture_envelope_digest": digest(canonical(envelope)),
            "target_trade_date": target, "observed_at": envelope["observed_at"], "received_at": envelope["received_at"],
            "first_available_at": envelope["received_at"], "source_revision": digest(canonical(sources)),
            "sources": sources, "expected_source_families": expected, "calendar_binding": envelope["calendar_binding"],
            "identity_binding": envelope["identity_binding"], "knowledge_lineage": lineage,
            "first_available_at_target_proven": False, "AS_RECORDED": False,
            "detectors": reasons, "completeness": "PARTIAL" if set(reasons) & {"MISSING_EXPECTED_SOURCE", "TARGET_DATE_MISMATCH", "SCHEMA_DRIFT", "CALENDAR_GAP", "IDENTITY_GAP"} else "COMPLETE",
            "permissions": {"production": False, "shadow": False, "focus_cutover": False, "formal_consumer": False},
            "dm01_publication_identity": None}
    item["publication_id"] = digest(canonical(item))
    atomic(destination / "publications" / (item["publication_id"] + ".json"), canonical(item), immutable=True)
    if failure_after_publication:
        raise RuntimeError("INJECTED_FAILURE_AFTER_DURABLE_PUBLICATION")
    rebuild_latest(root, ledger)
    return {"publication": item, "detectors": reasons, "retry": False}


def rebuild_latest(root, ledger):
    latest = {}
    for item in sorted(publications(root, ledger), key=lambda x: (instant(x["received_at"]), x["publication_id"])):
        latest[item["target_trade_date"]] = item["publication_id"]
    result = {"contract_id": CONTRACT, "projection_only": True, "latest_by_target": latest}
    atomic(Path(root) / ledger / "projections" / "latest.json", canonical(result))
    return result
