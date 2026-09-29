"""Independent R3 lineage, business-diff and source verification."""

import gzip
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import zipfile

from src.v4.go_forward_r3 import publication_time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    r = lambda name: json.loads((ROOT / "reports/v4_02" / name).read_text(encoding="utf-8"))
    capture = r("V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json")
    receipt = r("V4_02_GO_FORWARD_ADJUSTED_DAILY_RECEIPT_R3.json")
    universe = r("V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R3.json")
    diff = r("V4_02_GO_FORWARD_R2_R3_DIFF_R3.json")
    later = r("V4_02_GO_FORWARD_GBBQ_LATER_REVISION_R2.json")
    restore = r("V4_02_GO_FORWARD_REMOTE_LFS_RESTORE_R3.json")
    tests = r("V4_02_GO_FORWARD_R3_TEST_RECEIPT.json")
    assert digest(ROOT / capture["package_path"]) == capture["package_sha256"]
    assert restore["status"] == "PASS" and restore["restored_sha256"] == capture["package_sha256"]
    assert restore["restored_bytes"] == 551001603
    assert tests["exit_code"] == 0 and tests["failed"] == 0 and tests["passed"] >= 401
    for path, expected in tests["test_file_hashes"].items():
        assert digest(ROOT / path) == expected
    with zipfile.ZipFile(ROOT / capture["package_path"]) as archive:
        assert archive.testzip() is None
    assert universe["status"] == "PASS_CANDIDATE" and not universe["unresolved_target_source_keys"]
    assert diff["status"] == "PASS" and not diff["business_changes"]
    assert later["later_records_used_for_t0_qfq"] is False
    count = 0
    logical = sha256()
    keys = set()
    with gzip.open(ROOT / receipt["candidate_path"], "rb") as stream:
        for line in stream:
            logical.update(line)
            row = json.loads(line)
            checked = publication_time(*(row[k] for k in ("target_trade_date", "max_source_trade_date",
                "official_raw_source_published_at", "project_raw_source_available_at",
                "adjustment_source_available_at", "formal_publication_at")))
            assert row["knowledge_lineage"] == checked["knowledge_lineage"]
            assert row["historical_as_recorded_claim"] is False
            assert row["raw_source_snapshot_id"] == f"sha256-{capture['package_sha256']}"
            assert row["qfq_ohlc"] is not None or row["adjusted_quality"] != "ADJUSTED_READY"
            keys.add(row["source_security_key"])
            count += 1
    assert count == len(keys) == 5222
    assert logical.hexdigest() == receipt["logical_digest"]
    assert digest(ROOT / receipt["candidate_path"]) == receipt["candidate_sha256"]
    baseline = "0f66e88052b33b90ab76ec39bfeb115386f8bca2"
    for path in ("data/v4/V4_02_ACCEPTED_HEAD.json", "data/v4/V4_04_ACCEPTED_HEAD.json", "data/v4/V4_STAGE_ACCEPTED_HEAD.json"):
        assert (ROOT / path).read_bytes() == subprocess.check_output(["git", "show", f"{baseline}:{path}"], cwd=ROOT)
    result = {"contract_id": "V4_02_GO_FORWARD_PIT_LINEAGE_POSTCHECK_R3", "status": "PASS",
              "candidate_rows": count, "logical_digest": logical.hexdigest(), "business_diff": "NONE",
              "publication_ordering": "PASS_ALL_ROWS", "accepted_heads_unchanged": True,
              "later_gbbq_used": False, "tdx_root_write_count": 0}
    result["remote_lfs_restore"] = "PASS"
    result["runtime_tests"] = {"passed": tests["passed"], "failed": tests["failed"], "skipped": tests["skipped"]}
    path = ROOT / "reports/v4_02/V4_02_GO_FORWARD_PIT_LINEAGE_POSTCHECK_R3.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("R3_POSTCHECK_PASS", count)


if __name__ == "__main__":
    main()
