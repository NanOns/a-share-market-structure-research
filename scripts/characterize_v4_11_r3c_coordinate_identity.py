"""Bound actual R3A slot-domain characterization; never changes price sources."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.state_identity import digest

SEAL = ROOT / "reports/v4_11_r3a/R3A_SEALED_PRODUCER_SET_R2.json"
OUT = ROOT / "reports/v4_11_r3/V4_11_R3C_COORDINATE_SOURCE_CHARACTERIZATION_R1.json"


def binding(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def bound(ref):
    path = (ROOT / ref["path"]).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("CHARACTERIZATION_SOURCE_OUTSIDE_WORKSPACE")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != ref["sha256"] or len(data) != ref.get("bytes", ref.get("byte_count")):
        raise ValueError("CHARACTERIZATION_SOURCE_BINDING_MISMATCH")
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def coordinate_probe(mul, add):
    try:
        numbers = [Decimal(str(mul)), Decimal(str(add))]
        if any(not number.is_finite() for number in numbers):
            raise InvalidOperation("nonfinite coordinate")
        normalized = [str(number.normalize()) for number in numbers]
    except (InvalidOperation, ValueError, TypeError) as exc:
        return dict(valid=False, reason=type(exc).__name__, safe_exact_numeric_domain=False)
    exact_identity = digest(numbers)
    current_identity = digest(normalized)
    precision_loss = any(number != Decimal(text) for number,text in zip(numbers,normalized))
    signed_zero = any(number.is_zero() and number.is_signed() for number in numbers)
    return dict(valid=True, current_identity=current_identity, exact_numeric_identity=exact_identity,
        normalized_text=normalized, precision_loss=precision_loss, signed_zero=signed_zero,
        safe_exact_numeric_domain=not precision_loss and not signed_zero)


def characterize(rows):
    current_to_exact, exact_to_current = defaultdict(set), defaultdict(set)
    counts = dict(entities=len(rows), total_slots=0, price_ready_slots=0, invalid_ready_coordinates=0,
        signed_zero_ready_slots=0, normalize_precision_loss_ready_slots=0,
        current_mixed_exact_same_windows=0, current_same_exact_mixed_windows=0,
        equivalent_window_partitions=0, exact_mixed_windows=0, current_mixed_windows=0)
    examples = {key:[] for key in ("invalid", "signed_zero", "precision_loss", "partition_difference")}
    partitions = []
    for row in rows:
        current_ids, exact_ids = set(), set()
        ready_slots = []
        for slot in row["window"]:
            counts["total_slots"] += 1
            if slot.get("has_actual_bar") is not True:
                continue
            counts["price_ready_slots"] += 1
            probe = coordinate_probe(slot.get("mul"),slot.get("add"))
            example = dict(security_id=row["security_id"], date=slot["date"], mul=str(slot.get("mul")), add=str(slot.get("add")))
            if not probe["valid"]:
                counts["invalid_ready_coordinates"] += 1
                if len(examples["invalid"]) < 5:
                    examples["invalid"].append(example)
                continue
            if probe["signed_zero"]:
                counts["signed_zero_ready_slots"] += 1
                if len(examples["signed_zero"]) < 5:
                    examples["signed_zero"].append(example)
            if probe["precision_loss"]:
                counts["normalize_precision_loss_ready_slots"] += 1
                if len(examples["precision_loss"]) < 5:
                    examples["precision_loss"].append(example)
            current, exact = probe["current_identity"], probe["exact_numeric_identity"]
            current_to_exact[current].add(exact)
            exact_to_current[exact].add(current)
            current_ids.add(current)
            exact_ids.add(exact)
            ready_slots.append((slot["date"],current,exact))
        same_partition = all((left[1] == right[1]) == (left[2] == right[2]) for left in ready_slots for right in ready_slots)
        counts["equivalent_window_partitions"] += same_partition
        counts["current_mixed_windows"] += len(current_ids) > 1
        counts["exact_mixed_windows"] += len(exact_ids) > 1
        counts["current_mixed_exact_same_windows"] += len(current_ids) > 1 and len(exact_ids) == 1
        counts["current_same_exact_mixed_windows"] += len(current_ids) == 1 and len(exact_ids) > 1
        if not same_partition and len(examples["partition_difference"]) < 5:
            examples["partition_difference"].append(dict(security_id=row["security_id"], ready_slots=ready_slots))
        partitions.append(dict(security_id=row["security_id"], ready_slots=len(ready_slots),
            current_class_count=len(current_ids), exact_class_count=len(exact_ids), same_partition=same_partition))
    counts["global_current_identity_collision_groups"] = sum(len(v)>1 for v in current_to_exact.values())
    counts["global_exact_identity_fragmentation_groups"] = sum(len(v)>1 for v in exact_to_current.values())
    valid = (counts["invalid_ready_coordinates"] == counts["normalize_precision_loss_ready_slots"] ==
        counts["signed_zero_ready_slots"] == counts["global_current_identity_collision_groups"] ==
        counts["global_exact_identity_fragmentation_groups"] == 0 and counts["equivalent_window_partitions"] == counts["entities"])
    return dict(counts=counts, safe_actual_ready_coordinate_domain=valid, examples=examples,
        per_entity_partition_evidence_digest=digest(partitions),
        note="Compare equality partitions, not SHA strings: string-coordinate and numeric-coordinate digests intentionally use different encodings.")


def atomic(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary = tempfile.mkstemp(prefix=".coordinate-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    seal_ref = binding(SEAL)
    seal = bound(seal_ref)
    if seal["status"] != "V4_11_R3A_TARGET_FACT_PRODUCERS_CANDIDATE_READY" or seal.get("sealed") is not True:
        raise ValueError("SEALED_R3A_REQUIRED_FOR_CHARACTERIZATION")
    by_date = {}
    for day,ref in sorted(seal["calculations"].items()):
        rows = bound(ref)
        by_date[day] = dict(source=ref, **characterize(rows))
    safe = all(item["safe_actual_ready_coordinate_domain"] for item in by_date.values())
    regression_cases = dict(signed_zero=dict(current=coordinate_probe(1,"-0.000"),positive_zero=coordinate_probe(1,"0.000")),
        precision_collision=dict(left=coordinate_probe("1.00000000000000000000000000001",0),
            right=coordinate_probe("1.00000000000000000000000000002",0)))
    report = dict(contract_id="V4_11_R3C_COORDINATE_ACTUAL_SOURCE_CHARACTERIZATION_V1",
        scope="ENGINEERING_CHARACTERIZATION_ONLY_NOT_EXTERNAL_ACCEPTANCE", captured_at_utc=datetime.now(timezone.utc).isoformat(),
        stage_task=binding(ROOT/"docs/evidence/next_round_r3/V4_11_R3C_REAL_FULL_MARKET_DAG_REPLAY_TASK_20261002.md"),
        R3A_seal=seal_ref, script=binding(Path(__file__)), by_date=by_date,
        actual_ready_domain_result="PASS_EXACT_NUMERIC_EQUIVALENCE" if safe else "ACTUAL_SOURCE_CANONICALIZATION_REVIEW_REQUIRED",
        candidate_only=True, accepted=False, AS_RECORDED=False,
        exotic_coordinate_regression_probes=regression_cases,
        audit_item=dict(audit_id="AUD-R3C-ADJUSTMENT-COORDINATE-EXACTNESS-R1",
            scope="Decimal.normalize precision and signed-zero adjustment-coordinate identity; independent of AMR20/Amount-A",
            evidence="Two targeted tests expose signed-zero fragmentation and >28-digit precision collision",
            actual_current_source_scope_affected=not safe,
            disposition="Actual slot equivalence proven; exact numeric identity repair requires separate runtime authority and readback" if safe else "Review actual source differences before candidate replay acceptance",
            acceptance="ENGINEERING_EVIDENCE_ONLY_NOT_STAGE_ACCEPTANCE"),
        source_files_modified=False, producer_module_modified=False, main_heads_changed=False,
        permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False))
    atomic(OUT,report)
    print(json.dumps(dict(report=OUT.relative_to(ROOT).as_posix(),actual_ready_domain_result=report["actual_ready_domain_result"],
        counts={day:item["counts"] for day,item in by_date.items()})))


if __name__ == "__main__":
    main()
