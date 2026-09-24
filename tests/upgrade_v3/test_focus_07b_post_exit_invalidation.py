from datetime import date
from types import SimpleNamespace

from src.focus_tracker.materialize import VerifiedNormalizedSlice
from src.focus_tracker.predicate_requirements import plan_predicate_requirements
from src.focus_tracker.predicates import compile_v3_3_invalidation
from src.focus_tracker.v33_invalidation import evaluate_tracked_v33_invalidation


FIRST = date(2026, 9, 23)
TODAY = date(2026, 9, 24)
SECURITY = "SH.600000"


def _bar(day, close):
    return {"date": day, "has_actual_bar": True, "is_synthetic_fill": False,
            "missing_state": None, "trade_status_known": True,
            "adjustment_status": "VERIFIED_REPRODUCIBLE_TDX_NATIVE",
            "adjustment_version": "local-v1", "qfq_mul": "1", "qfq_add": "0",
            "raw_close": str(close)}


def test_post_exit_keeps_evaluating_frozen_price_thesis():
    first_row = SimpleNamespace(source_facts={
        "factor_evidence": {"price_basis": "TDX_NATIVE_AFFINE_QFQ"}})
    ast = compile_v3_3_invalidation("LAUNCH_CONFIRM", {})
    requirements = plan_predicate_requirements(ast)
    normalized = VerifiedNormalizedSlice(
        "a" * 64, (FIRST, TODAY),
        {SECURITY: {FIRST: _bar(FIRST, 9), TODAY: _bar(TODAY, 8)}})

    result, evidence, metadata = evaluate_tracked_v33_invalidation(
        ast=ast, frozen={"frozen_phh20": "10"}, first_row=first_row,
        today_source_row=None, scanner_evidence=None, security_id=SECURITY,
        trade_date=TODAY, first_trade_date=FIRST, sessions=(FIRST, TODAY),
        required_fields=requirements.required_fields, normalized=normalized)

    assert result.value == "TRUE"
    assert metadata["structure_break_v3"] is None
    assert metadata["scanner_source_status"] == "SOURCE_ROW_ABSENT"
    assert evidence["children"][0]["result"] == "UNKNOWN"
    assert evidence["children"][1]["result"] == "TRUE"
