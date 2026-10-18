"""Go-forward first-observed freeze; never backdate corrected history to PIT."""
import json
from datetime import datetime, timezone
from pathlib import Path

from .current_v4_context import canonical, digest, SourceInvalid


def _pg_source_bytes(root, binding):
    from workbench_db.v4_historical_source_ingress_pg_r1 import admit_source_binding_bytes

    raw = admit_source_binding_bytes(
        root,
        binding,
        source_origin="R2_FIRST_OBSERVED_FREEZE_HEAD_BOUND_SOURCE_R1",
    )
    if len(raw) != binding.get("bytes", len(raw)) or digest(raw) != binding["sha256"]:
        raise SourceInvalid("PIT_FREEZE_SOURCE_DIGEST_MISMATCH")
    return raw


def _pg_read_receipt(root, relative_path):
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path

    try:
        return read_path(root, relative_path)["raw"]
    except ValueError as exc:
        if str(exc) != "HISTORICAL_SOURCE_INGRESS_NOT_FOUND":
            raise

    # Import an older local receipt once so its original first-observed time is
    # preserved. Future reads resolve the exact bytes from PostgreSQL only.
    legacy = (Path(root).resolve() / relative_path).resolve()
    if not legacy.is_relative_to(Path(root).resolve()) or not legacy.is_file():
        return None
    raw = legacy.read_bytes()
    _pg_write_receipt(root, relative_path, raw, "LEGACY_FIRST_OBSERVED_RECEIPT_IMPORT")
    return raw


def _pg_write_receipt(root, relative_path, raw, source_revision):
    from workbench_db.v4_historical_source_ingress_pg_r1 import ingest_captured_bytes, read_bound

    ingested = ingest_captured_bytes(
        root,
        relative_path,
        raw,
        source_revision=source_revision,
        source_origin="R2_FIRST_OBSERVED_FREEZE_RECEIPT_R1",
    )
    exact = read_bound(root, relative_path, ingested["source_sha256"])["raw"]
    if exact != raw:
        raise SourceInvalid("PIT_FREEZE_RECEIPT_PG_READBACK_MISMATCH")
    return exact


def freeze(reader, now=None, *, source_reader=None, receipt_reader=None, receipt_writer=None):
    captured = datetime.now(timezone.utc)
    stamp = datetime.fromisoformat(now) if now else captured
    if stamp.tzinfo is None:
        raise SourceInvalid("PIT_OBSERVATION_TIMEZONE_REQUIRED")
    if stamp.astimezone(timezone.utc) > captured:
        raise SourceInvalid("FUTURE_OBSERVATION_TIME")
    if (captured - stamp.astimezone(timezone.utc)).total_seconds() > 5:
        raise SourceInvalid("BACKDATED_OBSERVATION_TIME")

    # Caller time is a freshness assertion only; the stored clock comes from
    # this process after the source bytes have been read.
    observed = captured.isoformat()
    day = reader.context["trade_date"]
    sources = {
        key: value
        for key, value in reader.manifest["sources"].items()
        if key in ("membership", "states", "advanced", "stock_factors", "sector_operational")
    }
    identity = digest(canonical(sources))
    relative_path = f"data/v4/pit_first_observed/{day}/{identity}/observation.json"
    load_source = source_reader or _pg_source_bytes
    load_receipt = receipt_reader or _pg_read_receipt
    store_receipt = receipt_writer or _pg_write_receipt

    def checked(binding):
        raw = load_source(reader.root, binding)
        if len(raw) != binding.get("bytes", len(raw)) or digest(raw) != binding["sha256"]:
            raise SourceInvalid("PIT_FREEZE_SOURCE_DIGEST_MISMATCH")
        return raw

    existing = load_receipt(reader.root, relative_path)
    if existing is not None:
        try:
            receipt = json.loads(existing)
        except (UnicodeDecodeError, ValueError) as exc:
            raise SourceInvalid("PIT_EXISTING_RECEIPT_INVALID") from exc
        if (
            receipt.get("contract_id") != "R2_FIRST_OBSERVED_FREEZE_V1"
            or receipt.get("source_identity") != identity
            or receipt.get("trade_date") != day
            or receipt.get("strict_t0_pit_ready") is not False
            or receipt.get("AS_RECORDED") is not False
        ):
            raise SourceInvalid("PIT_EXISTING_RECEIPT_CONFLICT")
        original = datetime.fromisoformat(receipt["first_observed_at"])
        if original.tzinfo is None or original.astimezone(timezone.utc) > captured:
            raise SourceInvalid("PIT_EXISTING_RECEIPT_TIME_INVALID")
        if set(receipt.get("sources", {})) != set(sources):
            raise SourceInvalid("PIT_EXISTING_SOURCE_SET_CONFLICT")
        for name, binding in receipt["sources"].items():
            if binding.get("sha256") != sources[name].get("sha256"):
                raise SourceInvalid("PIT_EXISTING_SOURCE_IDENTITY_CONFLICT")
            checked(binding)
        return receipt

    bindings = {}
    for name, binding in sources.items():
        raw = checked(binding)
        bindings[name] = dict(
            path=binding["path"],
            sha256=binding["sha256"],
            bytes=len(raw),
        )
    receipt = dict(
        contract_id="R2_FIRST_OBSERVED_FREEZE_V1",
        trade_date=day,
        first_observed_at=observed,
        sources=bindings,
        source_identity=identity,
        strict_t0_pit_ready=False,
        reason="FIRST_OBSERVED_TIME_IS_NOT_PROOF_OF_HISTORICAL_FIRST_AVAILABLE",
        knowledge_lineage="RECONSTRUCTED_CORRECTED",
        AS_RECORDED=False,
    )
    store_receipt(reader.root, relative_path, canonical(receipt), identity)
    return receipt
