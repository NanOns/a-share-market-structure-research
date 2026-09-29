"""Guard G08 against accidental reversion to pre-canonical R4 artifact identities."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_v4_05_r4_1_postgres_ledger import (  # noqa: E402
    R4_1_EXACT_IDENTITIES,
    R4_1_MANIFEST_REL,
    candidate_inputs,
    canonical_json_file_sha,
    file_sha,
    source_specs,
)


OLD_R4_BASELINE_FILES = (
    "V4_05_R4_CORE_PROFILE_REPLAY.json",
    "V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json",
    "V4_05_R4_MARKET_REFERENCE.json",
    "V4_05_R4_PERIOD_ASOF.json",
)


def test_g08_baseline_binds_exact_r4_1_candidate_artifacts() -> None:
    bundle = candidate_inputs()
    specs = source_specs()
    manifest = bundle["manifest"]

    assert bundle["manifest_path"].relative_to(ROOT).as_posix() == R4_1_MANIFEST_REL
    assert bundle["manifest_sha256"] == file_sha(ROOT / R4_1_MANIFEST_REL)
    assert manifest["external_acceptance"] == "PENDING"

    for source_key in ("CORE_PROFILE", "FULL_SCOPE_FACTORS", "PERIOD_ASOF"):
        expected = R4_1_EXACT_IDENTITIES[source_key]
        row = specs[source_key]
        assert row["digest"] == expected["artifact_sha256"]
        assert row["payload"]["artifact_path"] == expected["artifact_path"]
        assert row["payload"]["logical_digest"] == expected["logical_digest"] if "logical_digest" in expected else True

    market = specs["MARKET_REFERENCE"]
    assert market["payload"]["artifact_path"] == R4_1_EXACT_IDENTITIES["MARKET_REFERENCE"]["artifact_path"]
    assert market["digest"] == canonical_json_file_sha(ROOT / market["payload"]["artifact_path"])
    assert market["payload"]["output_digests"]["1"] == R4_1_EXACT_IDENTITIES["MARKET_REFERENCE"]["one_session_output_digest"]

    for source_key in ("MARKET_REGIME", "MARKET_SNAPSHOT_IDENTITY"):
        expected_path = R4_1_EXACT_IDENTITIES[source_key]["artifact_path"]
        assert specs[source_key]["payload"]["artifact_path"] == expected_path
        assert specs[source_key]["digest"] == canonical_json_file_sha(ROOT / expected_path)

    assert specs["CORE_PROFILE"]["payload"]["logical_digest"] == R4_1_EXACT_IDENTITIES["CORE_PROFILE"]["logical_digest"]
    formal_paths = "\n".join(str(spec["payload"]) for spec in specs.values())
    assert not any(old_name in formal_paths for old_name in OLD_R4_BASELINE_FILES)


def test_r4_1_candidate_manifest_binds_all_exact_receipts_and_artifacts() -> None:
    bundle = candidate_inputs()
    manifest = bundle["manifest"]["artifact_and_evidence_hashes"]
    for source_key, expected in R4_1_EXACT_IDENTITIES.items():
        artifact_path = expected["artifact_path"]
        path = ROOT / artifact_path
        assert manifest[artifact_path] == {"sha256": file_sha(path), "byte_count": path.stat().st_size}
        receipt_path = bundle["sources"][source_key]["receipt_path"].relative_to(ROOT).as_posix()
        receipt = ROOT / receipt_path
        assert manifest[receipt_path] == {"sha256": file_sha(receipt), "byte_count": receipt.stat().st_size}
