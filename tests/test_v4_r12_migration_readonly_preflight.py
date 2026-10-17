import json
from pathlib import Path
import tempfile

from scripts.v4_migration_readonly_preflight_r1 import run


def test_static_migration_preflight_reports_all_registered_sql_bytes_and_duplicates(tmp_path):
    out = Path(tempfile.gettempdir()) / "r12-static-preflight-test"
    report = run(out, read_catalog=False)
    assert report["status"] == "READ_ONLY_PREFLIGHT_ONLY_NO_DDL_DML_NO_HEAD"
    assert report["migration_count"] == 43
    assert report["duplicate_sequence_numbers"] == [10]
    assert report["migration_ledger_reconcile"]["ddl_executed"] is False
    assert report["migration_ledger_reconcile"]["dml_executed"] is False
    assert report["migration_ledger_reconcile"]["head_changed"] is False
    rows = {item["filename"]: item for item in report["migration_files"]}
    assert rows["039_tdx_package_row_count_authority_r1.sql"]["raw_sha256"]
    assert "not_valid" in rows["039_tdx_package_row_count_authority_r1.sql"]["static_risk_tags"]
    assert "role_or_grant" in rows["031_fep_roles_v1.sql"]["static_risk_tags"]
    assert rows["040_source_manifest_r3_fact_proof.sql"]["raw_sha256"]
    assert rows["041_r3_effective_date_gate.sql"]["raw_sha256"]
    assert rows["042_market_universe_persistence_r1.sql"]["raw_sha256"]
    saved = json.loads(Path(report["evidence_path"]).read_text(encoding="utf-8"))
    assert saved["status"] == report["status"]


def test_preflight_refuses_outputs_outside_g_temp(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="PREFLIGHT_OUTPUT_MUST_BE_UNDER_TEMP_ROOT"):
        run(Path("C:/codex_tmp/preflight-outside-g"), read_catalog=False)
