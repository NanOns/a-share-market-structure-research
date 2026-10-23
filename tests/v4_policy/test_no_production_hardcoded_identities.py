"""Repository-wide admission coverage for fixed business identity literals."""
import json
from pathlib import Path

import pytest

from scripts.check_v4_business_literals import ROOT, scan, tracked_files
from workbench_analysis.market_source_acquisition import earliest_required_factor_session


def test_factor_coverage_starts_at_source_identity_ipo_date():
    calls = []

    def query(_client, method, **params):
        calls.append((method, params))
        return [{"ipoDate": "2012-05-17"}]

    assert earliest_required_factor_session(object(), "sh.600111", query) == "2012-05-17"
    assert calls == [("query_stock_basic", {"code": "sh.600111"})]


@pytest.mark.parametrize("rows,error", [
    ([], "ADJUSTMENT_IDENTITY_SOURCE_MISSING"),
    ([{"ipoDate": None}], "ADJUSTMENT_IDENTITY_LIST_DATE_MISSING"),
    ([{"ipoDate": "not-a-date"}], "ADJUSTMENT_IDENTITY_LIST_DATE_MISSING"),
])
def test_factor_coverage_fails_closed_without_valid_ipo_fact(rows, error):
    with pytest.raises(ValueError, match=error):
        earliest_required_factor_session(object(), "synthetic.security", lambda *_a, **_k: rows)


def test_whole_repository_has_no_new_business_literal_candidates():
    baseline_path = ROOT / "config/v4_business_literal_admission_baseline_v1.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    findings, summary = scan(tracked_files())
    baseline_keys = set(baseline["candidate_keys"])
    current_keys = {item["candidate_key"] for item in findings if item["environment"] != "TEST_ONLY"}
    added = sorted(current_keys - baseline_keys)
    assert not added, (
        "发现未经基线审阅的固定日期/证券/板块字面量候选；请逐条分类，不能通过扩大路径豁免："
        f"{added[:20]}（新增 {len(added)} 条；扫描文件 {summary['files_scanned']}）"
    )
