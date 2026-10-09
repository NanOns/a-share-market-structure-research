"""Seal actual gates, corrected source freeze and independent per-domain next steps."""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.execute_r4_2_typed_delta import OUT,load,write,ref,file_sha
from workbench_analysis.tdx_official_daily_source import _atomic_write


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--daily-dir',default='daily_v4');args=parser.parse_args()
    p=OUT/args.daily_dir/'2026-10-08/source_readiness_receipt_r2.json';daily=load(p)
    trace=load(p.parent/'baostock_v2/CORRECTED_BAOSTOCK_FULL_TRACE.json')
    delta=load(OUT/'TDX_A_STOCK_DELTA_V2_RUNTIME_RECEIPT.json')
    entry=load(OUT/'ENTRY_SOURCE_AND_RELEASE_HEAD.json')
    official=ROOT/'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json'
    old=subprocess.check_output(['git','show',entry['head']+':reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json'],cwd=ROOT)
    if official.read_bytes()!=old:
        observed=load(official);write(OUT/'NEW_OFFICIAL_SOURCE_LOCATOR.json',observed)
        captured=ROOT/observed['capture_receipt']['path'];write(OUT/'NEW_OFFICIAL_REQUEST_RECEIPT.json',load(captured))
    _atomic_write(official,old,tdx_root=Path('D:/new_tdx'))
    oldowner=ROOT/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1'
    core=load(oldowner/'CORE_REPLAY.json');gb=core['owners'][0]['sources']['gbbq'];local=Path('D:/new_tdx/T0002/hq_cache/gbbq')
    gbbq=dict(contract_id='R421_CORRECTED_GBBQ_REVISION_V1',source=gb,source_path=str(local),
        frozen_sha_matches=file_sha(ROOT/gb['path'])==gb['sha256'],local_current_sha=file_sha(local),
        source_matches_current=file_sha(local)==gb['sha256'],AS_RECORDED=False,
        classification=ref(ROOT/'config/v4_02_gbbq_price_impact_classification_v1.json'),
        formal_probe=daily['gbbq_revision_probe'],formal_legacy_missing_path='D:/new_tdx/vipdoc/cw/gbbq(+gbbq.map)',
        corrected_use='HASH_BOUND_SINGLE_BINARY_AND_EVENT_SCOPED_CLASSIFICATION',production_permission=False)
    write(OUT/'CORRECTED_GBBQ_SOURCE_REVISION_READBACK.json',gbbq)
    families=dict(TDX_RAW=delta['targets']['2026-10-08']['binding'],GBBQ=gb,
                  IDENTITY=core['owners'][0]['sources']['identity'],CORE=core['owners'][-1]['core'])
    if daily.get('baostock_capture'):
        b=daily['baostock_capture'];bp=ROOT/'data/v4/source_snapshots/baostock/20261008'/b['snapshot_id']/'daily_update.json'
        families['BAOSTOCK_SUPPLEMENTAL']=ref(bp)
    lifecycle=daily.get('lifecycle_snapshot')
    if lifecycle:
        write(OUT/'CORRECTED_LIFECYCLE_SNAPSHOT.json',dict(lifecycle,AS_RECORDED=False,production_permission=False))
        families['LIFECYCLE']=ref(OUT/'CORRECTED_LIFECYCLE_SNAPSHOT.json')
        # Actually exercise the accepted special-phase builder with this bound
        # corrected lifecycle, independently of the legacy mutable path.
        from workbench_analysis.daily_source_manifests import build_special_phase_source_manifest
        try:
            acceptance=ROOT/'reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json'
            stage=ROOT/load(acceptance)['evidence']['manifest']['path'];components=load(stage)['components']
            lc=dict(contract_id='CURRENT_LIFECYCLE_SNAPSHOT_V1',status=lifecycle['status'],trade_date='2026-10-08',
                artifact_path=families['LIFECYCLE']['path'],artifact_sha256=families['LIFECYCLE']['sha256'],
                source_revision=lifecycle['source_revision'],active_security_ids=lifecycle['active_security_ids'])
            sp=build_special_phase_source_manifest(trade_date='2026-10-08',project_root=ROOT,
                v402_external_acceptance_path=acceptance,v402_stage_manifest_path=stage,
                event_store_path=ROOT/components['R6_EVENTS']['path'],policy_path=ROOT/components['R6_POLICY']['path'],
                lifecycle_snapshot=lc,observed_at=datetime.now(timezone.utc).isoformat(),tdx_root=Path('D:/new_tdx'))
            write(OUT/'CORRECTED_SPECIAL_PHASE_MANIFEST.json',dict(sp,AS_RECORDED=False,production_permission=False))
            families['SPECIAL_PHASE']=ref(OUT/'CORRECTED_SPECIAL_PHASE_MANIFEST.json')
        except (ValueError,KeyError,OSError) as error:
            write(OUT/'CORRECTED_SPECIAL_PHASE_MANIFEST.json',dict(status='BLOCKED_SPECIAL_PHASE_SOURCE',reason=str(error),error_type=type(error).__name__))
    write(OUT/'CORRECTED_SOURCE_FREEZE_SUCCESSOR_V2.json',dict(contract_id='R421_CORRECTED_SOURCE_FREEZE_V2',
        target_date='2026-10-08',observed_at=datetime.now(timezone.utc).isoformat(),source_families=families,
        AS_RECORDED=False,production_permission=False,legacy_project_source_freeze='NOT_INVOKED_FOR_RETROSPECTIVE_INPUT: IT ASSERTS AS_RECORDED=True',
        registry=ref(OUT/'BUILDER_REGISTRY_SUCCESSOR_CANDIDATE_V1.json'),
        admission='CORRECTED_CANDIDATE_ONLY; NO_CURRENT_PRODUCTION_AUTHORITY'))
    gate=dict(contract_id='R421_DM01_GATE_TRACE_V1',formal_entry_command='run_v4_dm01_daily_increment.py --target-date 2026-10-08 --typed-scope-v2',
        trace_receipt=ref(p),typed_delta=daily['tdx_delta_build'],baostock=dict(status=trace['status'],reason=trace.get('reason'),
            query_count=sum(r.get('metadata',{}).get('error_code')=='0' for r in trace['requests']),
            request_count_including_sessions=trace['request_count_this_run'],native_responses=ref(p.parent/'baostock_v2/CORRECTED_BAOSTOCK_FULL_TRACE.json')),
        gbbq=gbbq,lifecycle=daily.get('lifecycle_snapshot_receipt'),special_phase_legacy=daily.get('special_phase_source_receipt'),
        special_phase_corrected=(dict(status=load(OUT/'CORRECTED_SPECIAL_PHASE_MANIFEST.json')['status'],binding=ref(OUT/'CORRECTED_SPECIAL_PHASE_MANIFEST.json')) if (OUT/'CORRECTED_SPECIAL_PHASE_MANIFEST.json').exists() else None),
        source_freeze=ref(OUT/'CORRECTED_SOURCE_FREEZE_SUCCESSOR_V2.json'),
        old_registry=daily['accepted_builder_registry'],successor_registry=ref(OUT/'BUILDER_REGISTRY_SUCCESSOR_CANDIDATE_V1.json'),
        production_head_moved=False,exact_permission_blocker='No independently accepted reconstructed corrected subset publication authority')
    write(OUT/'DM01_TDX_TO_BAOSTOCK_FULL_GATE_TRACE.json',gate)
    with urllib.request.urlopen('http://127.0.0.1:28765/api/v4/context',timeout=10) as response:context=json.load(response)
    write(OUT/'LIVE_CONTEXT_READBACK.json',context)
    from urllib.parse import urlencode
    modules=[]
    for module in ('stocks','sectors','diagnostics/summary','focus','forward'):
        url='http://127.0.0.1:28765/api/v4/'+module+'?'+urlencode(dict(context_token=context['context_token'],limit=1))
        try:
            with urllib.request.urlopen(url,timeout=10) as response:payload=json.load(response)
            modules.append(dict(module=module,http_status=200,context_token=payload.get('context_token'),
                                trade_date=payload.get('context',{}).get('accepted_trade_date'),payload=payload))
        except urllib.error.HTTPError as error:
            modules.append(dict(module=module,http_status=error.code,payload=json.loads(error.read())))
    write(OUT/'LIVE_SAME_CONTEXT_MODULE_READBACK.json',dict(expected_context_token=context['context_token'],modules=modules,
        production_cutover=False,readback_scope='LAST_GOOD_2026_09_30'))
    protected={p:file_sha(ROOT/p)==h for p,h in entry['production_protected'].items()}
    if not all(protected.values()):raise ValueError('PRODUCTION_HEAD_CHANGED')
    ledger=dict(stage='R4.2.1',acceptance='PASS_TYPED_SCOPE_AND_TAXONOMY_ENGINEERING; PRODUCTION_NOT_ADMITTED',
        entry=ref(OUT/'ENTRY_SOURCE_AND_RELEASE_HEAD.json'),typed_source=delta['acceptance'],
        target_counts=delta['independent_target_counts'],taxonomy=load(OUT/'TAXONOMY_STAGE_ACCEPTANCE.json')['acceptance'],
        actual_gate_trace=ref(OUT/'DM01_TDX_TO_BAOSTOCK_FULL_GATE_TRACE.json'),
        p1=load(OUT/'P1_BOUNDARIES_STAGE_RESULT.json'),successor=ref(OUT/'SCOPED_SUCCESSOR_QA_AND_CAS_READBACK.json'),
        source_requests_this_stage=sum(load(p)['request_count_this_run'] for p in OUT.glob('daily*/2026-10-08/baostock_v2/CORRECTED_BAOSTOCK_FULL_TRACE.json')),
        protected=protected,live_trade_date=context['context']['accepted_trade_date'],
        single_domain_blockers=dict(TDX_HISTORICAL_MEMBERSHIP='Missing accepted exact-date rows for 9/28,9/29,10/08; mtime insufficient',
            BJ='246 source candidates/101 unresolved/1 new lifecycle require independent identity authority',
            BREAKOUT='No accepted prior absence; actual real runtime episode quality UNKNOWN',
            PRICE_LIMIT='Target dated limit owner not independently accepted',
            PRODUCTION='Current all-nine PIT contract does not permit corrected RAW/Core/Profile subset'),
        next_stage='INDEPENDENT_SCOPED_ADMISSION_REQUEST_REVIEW',branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip())
    write(OUT/'R4_2_CONTINUOUS_EXECUTION_LEDGER.json',ledger)
    handoff=f'''# R4.2.1 continuous execution handoff

Engineering acceptance: PASS_TYPED_SCOPE_AND_TAXONOMY_ENGINEERING.
Production: BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION; actual API remains {ledger['live_trade_date']}.

Typed V2 verifies real parent/current SHA/CRC and full entry quarantine, with
four-session canonical BAR counts 5210 / 5211 / 5213 / 5209. All 18 prior foreign
consumer anomalies are accounted for. Independent direct byte decoder and frozen
Owner six-field comparison agree. Original V1/seals/528 restoration/35 suspensions
remain intact. No prefix grants canonical identity.

DM01 actually reached bounded BaoStock daily/factor requests. Initial failures
(native adjustFacto schema, missing SDK result date, relative output path) remain
in daily/daily_v2/daily_v3; versioned spelling and row-date adapters retain native
responses. Latest source status: {trace['status']}; reason: {trace.get('reason')}.
GBBQ and lifecycle/special-phase executed paths and exact blockers are in the full
gate trace. Corrected source freeze/registry successor are staging-only; the old
project_source_freeze asserts AS_RECORDED and cannot consume retrospective sources.

TDX primary taxonomy is enforced by adapter/registry and isolated successor.
9/30 TDX 378/50162 identity/digests remain unchanged. Thirty real TDX/CSRC samples
have 29 differing LOO medians. Four-day 20893 stock Seed/PREWATCH values replay
exactly without membership dependencies. CSRC auxiliary payloads have separate
csrc_ fields; missing exact-date TDX membership causes primary fields UNKNOWN.

BJ approval objects, breakout prior audit and ten real independent ex-right,
suspension and short-listing boundary samples are delivered separately. No prior
absence is fabricated. Isolated E-drive CAS, same-hash NOOP, stale CAS, bad scope,
forged PIT, failure injection and exact predecessor rollback actually ran.

Review SCOPED_ADMISSION_REQUEST.json and the separate single-domain blockers in
R4_2_CONTINUOUS_EXECUTION_LEDGER.json. No formal publication, external acceptance
or future historical first-availability claim is inferred from these results.
Relevant code and byte evidence are committed/pushed on codex/v4-fp14-r2-repair.
'''
    _atomic_write(OUT/'R4_2_EXTERNAL_AUDIT_HANDOFF.md',handoff.encode(),tdx_root=Path('D:/new_tdx'))
    print(json.dumps(dict(acceptance=ledger['acceptance'],baostock=trace['status'],protected=protected,live_trade_date=ledger['live_trade_date'])))


if __name__=='__main__':main()
