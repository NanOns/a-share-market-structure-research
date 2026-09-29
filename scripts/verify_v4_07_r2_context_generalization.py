from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()
sys.path.insert(0, str(ROOT))

from src.v4.base_seed import _load_accepted_source_context, build_candidate_from_records  # noqa: E402


def file_digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def synthetic_context(
    template: Mapping[str, Any],
    trade_date: str,
    publication_id: str,
    profile_id: str,
    source_digest: str,
    core_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    board_counts: dict[str, int] = {}
    for row in core_rows:
        board = str(row["board"])
        board_counts[board] = board_counts.get(board, 0) + 1
    identity_count = len(core_rows)
    bindings = copy.deepcopy(template["source_bindings"])
    bindings.update({
        "publication_id": publication_id,
        "profile_row_publication_id": profile_id,
        "trade_date": trade_date,
        "core_logical_digest": source_digest,
        "accepted_identity_count": identity_count,
        "expected_board_counts": dict(sorted(board_counts.items())),
        "core_profile_artifact_sha256": hashlib.sha256((source_digest + ":core").encode()).hexdigest(),
        "core_profile_receipt_sha256": hashlib.sha256((source_digest + ":core-receipt").encode()).hexdigest(),
        "full_scope_factors_logical_digest": hashlib.sha256((source_digest + ":factor-logical").encode()).hexdigest(),
        "full_scope_factors_artifact_sha256": hashlib.sha256((source_digest + ":factors").encode()).hexdigest(),
        "full_scope_factors_receipt_sha256": hashlib.sha256((source_digest + ":factor-receipt").encode()).hexdigest(),
        "exact_ledger_binding_sha256": hashlib.sha256((source_digest + ":ledger").encode()).hexdigest(),
    })
    return {
        "source_bindings": bindings,
        "trade_date": trade_date,
        "publication_id": publication_id,
        "profile_row_publication_id": profile_id,
        "core_logical_digest": source_digest,
        "expected_identity_count": identity_count,
        "expected_board_counts": dict(sorted(board_counts.items())),
        "parameter_set": copy.deepcopy(template["parameter_set"]),
        "contract_digest": template["contract_digest"],
        "parameter_set_digest": template["parameter_set_digest"],
    }


def main() -> int:
    template, accepted_core, accepted_factors = _load_accepted_source_context(ROOT, SOURCE_ROOT)
    factor_by_id = {row["security_id"]: row for row in accepted_factors}
    scenarios = (
        ("2026-09-28", "SYNTHETIC-PUBLICATION-T", "SYNTHETIC-PROFILE-T", "a" * 64, accepted_core[:2]),
        ("2026-09-29", "SYNTHETIC-PUBLICATION-T1", "SYNTHETIC-PROFILE-T1", "b" * 64, accepted_core[2:3]),
    )
    contexts = []
    core_records: list[dict[str, Any]] = []
    factor_records: list[dict[str, Any]] = []
    for trade_date, publication_id, profile_id, source_digest, source_rows in scenarios:
        current_core = [dict(copy.deepcopy(row), trade_date=trade_date, publication_id=profile_id) for row in source_rows]
        current_factors = []
        for row in source_rows:
            factor = copy.deepcopy(factor_by_id[row["security_id"]])
            factor["trade_date"] = trade_date
            current_factors.append(factor)
        contexts.append(synthetic_context(template, trade_date, publication_id, profile_id, source_digest, current_core))
        core_records.extend(current_core)
        factor_records.extend(current_factors)

    fixed_stamp = "2026-09-30T00:00:00Z"
    t_result = build_candidate_from_records(core_records, factor_records, contexts[0], created_at=fixed_stamp)
    t1_result = build_candidate_from_records(core_records, factor_records, contexts[1], created_at=fixed_stamp)
    if t_result["row_count"] != contexts[0]["expected_identity_count"]:
        raise AssertionError("T row count was not taken from its accepted run context")
    if t1_result["row_count"] != contexts[1]["expected_identity_count"]:
        raise AssertionError("T+1 row count was not taken from its accepted run context")
    if t_result["row_count"] == t1_result["row_count"]:
        raise AssertionError("synthetic contexts must exercise different row counts")
    if {row["trade_date"] for row in t_result["rows"]} != {contexts[0]["trade_date"]}:
        raise AssertionError("T candidate contains an identity from another date")
    if {row["publication_id"] for row in t_result["rows"]} != {contexts[0]["publication_id"]}:
        raise AssertionError("T candidate contains another publication identity")
    if {row["trade_date"] for row in t1_result["rows"]} != {contexts[1]["trade_date"]}:
        raise AssertionError("T+1 candidate contains an identity from another date")
    if {row["publication_id"] for row in t1_result["rows"]} != {contexts[1]["publication_id"]}:
        raise AssertionError("T+1 candidate contains another publication identity")

    future_changed = [
        dict(row, future_test_payload="ignored") if row["trade_date"] == contexts[1]["trade_date"] else row
        for row in core_records
    ]
    t_replayed = build_candidate_from_records(future_changed, factor_records, contexts[0], created_at=fixed_stamp)
    if t_replayed["logical_digest"] != t_result["logical_digest"]:
        raise AssertionError("future-date mutation changed the T logical result")

    report = {
        "contract_id": "V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION_V1",
        "status": "PASS_CONTEXT_DRIVEN_MULTI_DATE_PRODUCER",
        "producer": "src/v4/base_seed.py::build_candidate_from_records",
        "synthetic_accepted_contexts": [
            {
                "trade_date": context["trade_date"],
                "publication_id": context["publication_id"],
                "profile_row_publication_id": context["profile_row_publication_id"],
                "core_logical_digest": context["core_logical_digest"],
                "factor_logical_digest": context["source_bindings"]["full_scope_factors_logical_digest"],
                "expected_identity_count": context["expected_identity_count"],
                "expected_board_counts": context["expected_board_counts"],
                "output_row_count": result["row_count"],
                "candidate_logical_digest": result["logical_digest"],
            }
            for context, result in zip(contexts, (t_result, t1_result))
        ],
        "different_row_counts_exercised": t_result["row_count"] != t1_result["row_count"],
        "publication_identity_isolation": True,
        "source_digest_isolation": t_result["source_bindings"]["core_logical_digest"] != t1_result["source_bindings"]["core_logical_digest"],
        "future_row_does_not_change_prior_date": True,
        "accepted_source_artifact_sha256": file_digest(SOURCE_ROOT / "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz"),
        "next_stage": "V4_07_R2_INDEPENDENT_POSTCHECK_AND_EXTERNAL_REVIEW",
    }
    atomic_json(ROOT / "reports/v4_07/V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION.json", report)
    print(json.dumps({"status": report["status"], "context_count": len(contexts), "row_counts": [t_result["row_count"], t1_result["row_count"]]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
