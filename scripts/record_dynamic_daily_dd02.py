from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.tdx_latest_daily_source_v2 import capture_latest_tdx_package,extract_target_session_bars
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OUT=ROOT/'docs/evidence/dynamic_daily_20261009'
if __name__=='__main__':
    before={p:sha(ROOT/p) for p in ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']}
    try:
        package=capture_latest_tdx_package(snapshot_root=ROOT/'data/v4/dynamic_daily_sources')
        extraction=extract_target_session_bars(package,'2026-10-08',snapshot_root=ROOT/'data/v4/dynamic_daily_sources')
        result=dict(status='REAL_TARGET_EXTRACTION_PASS' if extraction['row_count'] else 'WAIT_TDX',package=package,
            extraction={k:v for k,v in extraction.items() if k not in {'target_bars','excluded_non_stock_entries'}},
            excluded_non_stock_entry_count=len(extraction['excluded_non_stock_entries']),
            evidence_kind='LIVE_OFFICIAL_PACKAGE_ACTUAL_BARS')
    except Exception as exc:
        result=dict(status='BLOCKED',reason=str(exc)[:200],exception_type=type(exc).__name__,evidence_kind='LIVE_CAPTURE_ATTEMPT')
    result['protected_heads_unchanged']=before=={p:sha(ROOT/p) for p in before}
    result['protected_heads']=before
    atomic(OUT/'DD02_REAL_TDX_EXTRACTION.json',canonical(result));print(json.dumps({k:v for k,v in result.items() if k not in {'package','extraction'}},ensure_ascii=False))
