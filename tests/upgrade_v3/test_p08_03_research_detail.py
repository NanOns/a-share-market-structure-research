import duckdb
from pathlib import Path

from workbench_service.research_queries import ResearchQueries
from workbench_service.research_runs import ResearchRunStore


ROOT = Path(__file__).resolve().parents[2]


def test_global_shortlist_and_stock_evidence_are_run_bound_and_sectioned():
    connection = duckdb.connect(":memory:")
    runs = ResearchRunStore(connection)
    started = runs.start({"job_type": "BUILD_RESEARCH_V3", "publication_id": "pub-detail", "trade_date": "2026-09-10", "algorithm_version": "RESEARCH_V3_PREVIEW_1", "parameter_hash": "h", "snapshot_id": "s", "membership_snapshot_id": "m", "dependency_bindings": {}})
    runs.complete(
        started["run_id"],
        stock_states=[{"security_id": "S1", "setup": True, "quality": "READY", "reason_codes": ["SETUP"], "risk_codes": ["EXTENDED"], "evidence": {"selection": {"source": "run"}, "risk": {"code": "EXTENDED"}}}],
        member_roles=[{"sector_id": "A", "security_id": "S1", "role": "CURRENT_RESEARCH", "role_rank": 1}],
        shortlists=[{"list_type": "CURRENT_FOCUS", "security_id": "S1", "rank": 1, "primary_sector_id": "A", "selection_reason": ["CURRENT_RESEARCH"], "waiting_for": ["板块确认"], "invalid_if": ["数据失效"]}],
    )
    queries = ResearchQueries()
    context = queries.contexts.resolve_request("pub-detail", "2026-09-10", connection=connection)
    stock = queries.stock_detail(context["context_id"], "S1", connection=connection)["stock"]
    assert stock["sector_roles"][0]["role"] == "CURRENT_RESEARCH"
    assert stock["shortlists"][0]["list_type"] == "CURRENT_FOCUS"
    evidence = queries.stock_evidence(context["context_id"], "S1", "risk", connection=connection)
    assert evidence["evidence"] == {"code": "EXTENDED"}
    connection.close()


def test_p08_03_ui_has_global_lists_modal_tabs_and_legacy_candidate_label():
    page = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    legacy = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    for marker in ("CURRENT_FOCUS", "EARLY_FOCUS", "page_size=20", "stock-modal", "data-section=\"selection\"", "data-section=\"risk\"", "loadEvidence"):
        assert marker in page
    assert "全部结构候选" in legacy
    assert "/api/candidates" in (ROOT / "src/workbench_service/static/v2/api.js").read_text(encoding="utf-8")
