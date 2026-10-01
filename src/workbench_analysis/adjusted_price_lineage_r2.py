"""Historical adjusted-price knowledge gate; capture cannot prove earlier knowledge."""
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from .forward_pit_ledger_r2 import atomic, bound, canonical, digest, instant, reference

CONTRACT = "A07_ADJUSTED_PRICE_KNOWLEDGE_LINEAGE_R2"


def classify_lineage(root, record, *, knowledge_time):
    at = instant(knowledge_time)
    source = record.get("source_bytes")
    missing = [k for k in ("first_available_at", "source_revision", "knowledge_time", "source_bytes") if not record.get(k)]
    if source:
        bound(root, source)
    capture_proved = False
    if record.get("capture_id") and source:
        receipt = Path(root)/"data/v4/source_evidence/a07_r2/captures"/(record["capture_id"]+".json")
        without_id = dict(record)
        without_id.pop("capture_id")
        capture_proved = (receipt.exists() and receipt.read_bytes() == canonical(record)
                          and digest(canonical(without_id)) == record["capture_id"]
                          and record.get("source_revision") == "sha256:" + source["sha256"])
    if record.get("recomputed_now"):
        lineage = "CURRENT_RECOMPUTED"
    elif not missing and capture_proved and instant(record["first_available_at"]) <= instant(record["knowledge_time"]) <= at and record.get("capture_attested") is True:
        lineage = "AS_RECORDED"
    else:
        lineage = "RECONSTRUCTED_CORRECTED"
    return {"contract_id": CONTRACT, "lineage": lineage, "knowledge_time_requested": knowledge_time,
            "missing_as_recorded_requirements": missing,
            "immutable_capture_receipt_verified": capture_proved,
            "historical_capability": "PROVED_AT_CAPTURE_OR_LATER" if lineage == "AS_RECORDED" else "PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED",
            "formal_consumer_enabled": False, "reconstructed_allowed_only_by_consumer_contract": True}


def capture_source(root, source_path, *, source_kind, source_identity, observed_at=None):
    if source_kind not in {"GBBQ", "PROVIDER_FACTOR", "MANUAL_RECORD"}:
        raise ValueError("SOURCE_KIND_UNKNOWN")
    if not source_identity:
        raise ValueError("SOURCE_IDENTITY_REQUIRED")
    start = observed_at or datetime.now().astimezone().isoformat()
    instant(start)
    raw = Path(source_path).read_bytes()
    received = datetime.now().astimezone().isoformat()
    if instant(start) > instant(received):
        raise ValueError("FUTURE_CAPTURE_ATTESTATION")
    target = Path(root)/"data/v4/source_evidence/a07_r2"/digest(raw)/"source.bin"
    atomic(target, raw, immutable=True)
    record = {"contract_id": CONTRACT, "source_kind": source_kind, "source_identity": source_identity,
              "source_revision": "sha256:"+digest(raw), "source_bytes": reference(root, target),
              "observed_at": start, "received_at": received, "first_available_at": received,
              "knowledge_time": received, "capture_attested": True,
              "history_before_capture_as_recorded": False, "future_observations_required": True,
              "formal_consumer_enabled": False}
    record["capture_id"] = digest(canonical(record))
    receipt = Path(root)/"data/v4/source_evidence/a07_r2/captures"/(record["capture_id"]+".json")
    atomic(receipt, canonical(record), immutable=True)
    return record


def independent_ex_right_reference(close, *, cash_per10=0, bonus_per10=0, rights_per10=0, rights_price=0):
    """Only explanatory price-event arithmetic; no accepted QFQ history emitted."""
    close, cash, bonus, rights, price = map(lambda x: Decimal(str(x)), (close, cash_per10, bonus_per10, rights_per10, rights_price))
    if close <= 0 or any(x < 0 for x in (cash, bonus, rights, price)):
        raise ValueError("INVALID_PRICE_EVENT")
    return (close-cash/10+price*rights/10)/(1+bonus/10+rights/10)
