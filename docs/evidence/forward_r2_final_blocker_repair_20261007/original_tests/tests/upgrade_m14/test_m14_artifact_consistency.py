import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
REPORTS = ROOT / "reports/upgrade_m14"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m14_contract_hashes_and_view_hashes_are_current():
    for receipt_path in REPORTS.glob("m14_*.json"):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("contract_sha256") and receipt.get("contract"):
            assert sha256(ROOT / receipt["contract"]) == receipt["contract_sha256"], receipt_path.name
        evidence = receipt.get("evidence", {})
        if evidence.get("view_path") and evidence.get("view_sha256"):
            assert sha256(Path(evidence["view_path"])) == evidence["view_sha256"], receipt_path.name


def test_m14_source_bound_hashes_are_current():
    for receipt_name in ("m14_01_source_validation_receipt_20260911.json", "m14_01_review_receipt_20260911.json"):
        receipt = json.loads((REPORTS / receipt_name).read_text(encoding="utf-8"))
        for name, expected in receipt.get("bound_hashes", {}).items():
            if "/" in name or "\\" in name:
                assert sha256(ROOT / name) == expected, f"{receipt_name}:{name}"


def test_m14_personal_branch_reopen_is_bound_to_batch_foundation():
    reopen = REPORTS / "m14_01_personal_reopen_receipt_20260911.json"
    foundation = json.loads((REPORTS / "m14_02_batch_foundation_receipt_20260911.json").read_text(encoding="utf-8"))
    assert json.loads(reopen.read_text(encoding="utf-8"))["status"] == "DEGRADED_PASS"
    assert foundation["precondition_receipt"] == "reports/upgrade_m14/m14_01_personal_reopen_receipt_20260911.json"
    assert foundation["precondition_contract"] == "docs/M14_PERSONAL_RESEARCH_REOPEN_CONTRACT_V1.md"


def test_m14_online_migration_covers_evidence_and_quotes():
    migration = (ROOT / "src/workbench_db/migrations/024_m14_online.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS online_evidence" in migration
    assert "CREATE TABLE IF NOT EXISTS online_quote_entries" in migration
