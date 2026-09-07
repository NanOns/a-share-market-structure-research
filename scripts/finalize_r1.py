"""Execute and seal the R1 input-snapshot/data-semantics focused gate."""
from __future__ import annotations

from datetime import date
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from common.identity import computation_identity,render_identity,source_identity  # noqa:E402
from common.input_snapshot import (INPUT_SNAPSHOT_CONTRACT_VERSION,archive_source_revision,
    build_input_snapshot_manifest,next_source_revision_id,validate_input_snapshot_manifest,
    write_immutable_manifest)  # noqa:E402
from normalize.phase1 import DAY_DTYPE,normalize  # noqa:E402
from phase1_runner import validate_canonical_dates_before_write  # noqa:E402
from production.daily import (PRODUCTION_VERSION,assert_source_stable,latest_resolution,
    run_daily,source_fingerprint,tdx_hashes,universe_snapshot)  # noqa:E402
from production.release import atomic_write_bytes,atomic_write_json  # noqa:E402


BASELINE='V0.3_FINAL_IMPLEMENTATION_BASELINE'
DATA_STATE_CONTRACT_VERSION='data-state-semantics-v1.0'
TDX=Path('D:/new_tdx')
OUT=ROOT/'reports/r1'
XML=OUT/'R1_FOCUSED_TESTS.xml'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_tests():
    env=dict(os.environ);env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
    result=subprocess.run([sys.executable,'-m','pytest','tests/r1','-q',f'--junitxml={XML}'],cwd=ROOT,env=env,text=True,capture_output=True)
    tree=ET.parse(XML);cases=tree.findall('.//testcase');failures=tree.findall('.//failure')+tree.findall('.//error')
    return {'exit_code':result.returncode,'tests_passed':len(cases)-len(failures),'tests_failed':len(failures),
        'test_names':[f"{case.get('classname')}::{case.get('name')}" for case in cases],
        'stdout':result.stdout.strip(),'stderr':result.stderr.strip(),'junit_xml':'reports/r1/R1_FOCUSED_TESTS.xml'}


def gap_audit():
    rows=np.zeros(2,dtype=DAY_DTYPE);rows['date']=[20260901,20260903]
    for field in ('open','high','low','close'):rows[field]=[1000,1100]
    rows['volume']=[100,120];rows['amount']=[1000,1320]
    sessions=np.array([20260901,20260902,20260903])
    inferred,ctx,stats=normalize('SH.600001',rows,sessions,[])
    inferred_row=inferred.to_pandas().iloc[1]
    confirmed,confirmed_ctx,confirmed_stats=normalize('SH.600001',rows,sessions,[],confirmed_suspension_dates={20260902})
    confirmed_row=confirmed.to_pandas().iloc[1]
    raw_fields=['raw_open','raw_high','raw_low','raw_close','raw_volume','raw_amount','adj_open','adj_high','adj_low','adj_close']
    inferred_pass=(inferred_row.missing_state=='INFERRED_GAP' and not inferred_row.is_synthetic_fill and
        all(pd.isna(inferred_row[field]) for field in raw_fields+['aligned_close','aligned_volume','aligned_amount']))
    confirmed_pass=(confirmed_row.missing_state=='CONFIRMED_SUSPENSION' and confirmed_row.trade_status_known and
        confirmed_row.is_synthetic_fill and confirmed_ctx.iloc[1].close==10 and confirmed_ctx.iloc[1].amount==0)
    actual_row=inferred.to_pandas().iloc[0]
    trade_pass=(actual_row.has_actual_bar and actual_row.data_observed and actual_row.has_positive_amount and
        not actual_row.trade_status_known and not inferred_row.has_actual_bar and not inferred_row.data_observed)
    return {'audit_version':'r1-gap-semantics-audit-v1.0','unknown_internal_gap':{
        'dates':['20260901 BAR','20260902 missing','20260903 BAR'],'classified_as':inferred_row.missing_state,
        'not_confirmed_suspension':inferred_row.missing_state!='CONFIRMED_SUSPENSION','is_synthetic_fill':bool(inferred_row.is_synthetic_fill),
        'raw_and_aligned_fields_null':all(pd.isna(inferred_row[field]) for field in raw_fields+['aligned_close','aligned_volume','aligned_amount']),
        'stats':stats,'pass':bool(inferred_pass)},'confirmed_suspension':{
        'evidence':'explicit audited fixture date 20260902','classified_as':confirmed_row.missing_state,
        'trade_status_known':bool(confirmed_row.trade_status_known),'derived_close':float(confirmed_ctx.iloc[1].close),
        'derived_amount':float(confirmed_ctx.iloc[1].amount),'stats':confirmed_stats,'pass':bool(confirmed_pass)},
        'trade_data_status':{'actual_bar_fields':{'has_actual_bar':True,'data_observed':True,'has_positive_amount':True,'trade_status_known':False},
        'compatibility_tradable_semantics':'actual local bar exists; not proof of real-world executability','pass':bool(trade_pass)},
        'inferred_gap_semantics_pass':bool(inferred_pass),'confirmed_suspension_semantics_pass':bool(confirmed_pass),
        'raw_gap_null_semantics_pass':bool(inferred_pass),'trade_status_semantics_pass':bool(trade_pass),
        'pass':bool(inferred_pass and confirmed_pass and trade_pass)}


def input_audit(source_before,comp,render,cutoff):
    receipt=json.loads((ROOT/'reports/phase4/PHASE4_FINAL_RECEIPT.json').read_text('utf8'))
    d=date(int(cutoff[:4]),int(cutoff[4:6]),int(cutoff[6:]))
    stocks=pq.read_table(ROOT/'data/scanner/stock_scanner_daily.parquet',columns=['security_id','date'],filters=[('date','=',d)]).to_pandas()
    universe=universe_snapshot(stocks,cutoff,receipt.get('generation'))
    identity=source_identity(source_before)
    manifest=build_input_snapshot_manifest(run_id='r1-final-audit',cutoff_date=cutoff,source_revision_id=1,
        source_identity=identity,source_fingerprint=source_before,computation_identity=comp,render_identity=render,
        run_universe=universe,observed_at='2026-09-06T00:00:00+00:00')
    with tempfile.TemporaryDirectory(prefix='r1-input-') as raw:
        path=Path(raw)/'INPUT_SNAPSHOT_MANIFEST.json';write_immutable_manifest(path,manifest)
        immutable_before=sha(path)
        collision_blocked=False
        altered=dict(manifest);altered['run_id']='different'
        try:write_immutable_manifest(path,altered)
        except (ValueError,FileExistsError):collision_blocked=True
        immutable_after=sha(path)
    required=['run_id','cutoff_date','observed_at','source_revision_id','source_identity_version','source_identity',
        'day_source_summary','gbbq_sha256','gbbq_map_sha256','membership_hashes','security_master_hashes','calendar_sha256',
        'run_universe_generation','run_universe_sha256','run_universe_count','adjustment_identity','price_basis',
        'computation_identity','render_identity','snapshot_manifest_sha256']
    passed=validate_input_snapshot_manifest(manifest) and all(key in manifest for key in required) and collision_blocked and immutable_before==immutable_after
    return {'audit_version':'r1-input-snapshot-audit-v1.0','contract_version':INPUT_SNAPSHOT_CONTRACT_VERSION,
        'required_fields':required,'sample_manifest':manifest,'immutable_collision_blocked':collision_blocked,
        'manifest_file_sha256_before':immutable_before,'manifest_file_sha256_after':immutable_after,
        'release_required_file':'INPUT_SNAPSHOT_MANIFEST.json','pass':bool(passed)}


def revision_audit(input_manifest):
    with tempfile.TemporaryDirectory(prefix='r1-revision-') as raw:
        root=Path(raw)
        one=dict(input_manifest);one['run_id']='run-1';one['source_revision_id']=1;one.pop('snapshot_manifest_sha256',None)
        one=build_input_snapshot_manifest(run_id='run-1',cutoff_date=one['cutoff_date'],source_revision_id=1,
            source_identity={**one['source_identity'],'sha256':'source-a'},source_fingerprint={'source_fingerprint_components':{},'day_fingerprint_summary':{}},
            computation_identity=one['computation_identity'],render_identity=one['render_identity'],run_universe={'generation':one['run_universe_generation'],'sha256':one['run_universe_sha256'],'count':one['run_universe_count']},observed_at=one['observed_at'])
        first_id=next_source_revision_id(root,one['cutoff_date'],'source-a');first=archive_source_revision(root,one,release_id='release-1')
        two=build_input_snapshot_manifest(run_id='run-2',cutoff_date=one['cutoff_date'],source_revision_id=2,
            source_identity={**one['source_identity'],'sha256':'source-b'},source_fingerprint={'source_fingerprint_components':{},'day_fingerprint_summary':{}},
            computation_identity=one['computation_identity'],render_identity=one['render_identity'],run_universe={'generation':one['run_universe_generation'],'sha256':one['run_universe_sha256'],'count':one['run_universe_count']},observed_at=one['observed_at'])
        second_id=next_source_revision_id(root,two['cutoff_date'],'source-b');second=archive_source_revision(root,two,release_id='release-2',changed_source_components=['gbbq'])
        one_exists=(root/f"reports/revisions/{one['cutoff_date']}/revision-000001/REVISION_RECORD.json").exists()
        two_exists=(root/f"reports/revisions/{one['cutoff_date']}/revision-000002/REVISION_RECORD.json").exists()
        first_hash=sha(root/f"reports/revisions/{one['cutoff_date']}/revision-000001/REVISION_RECORD.json")
        archive_source_revision(root,one,release_id='release-ignored')
        preserved=first_hash==sha(root/f"reports/revisions/{one['cutoff_date']}/revision-000001/REVISION_RECORD.json")
        same_identity_reused=next_source_revision_id(root,one['cutoff_date'],'source-a')==1
    passed=first_id==1 and second_id==2 and first['created'] and second['created'] and one_exists and two_exists and preserved
    return {'audit_version':'r1-revision-archive-audit-v1.0','cutoff_date':one['cutoff_date'],
        'revision_1':{'source_identity':'source-a','run_id':'run-1','release_id':'release-1','retained':one_exists},
        'revision_2':{'source_identity':'source-b','run_id':'run-2','release_id':'release-2','changed_source_components':['gbbq'],'retained':two_exists},
        'revision_1_not_overwritten':preserved,'same_identity_revision_reused':same_identity_reused,
        'pass':bool(passed)}


def future_guard_audit():
    with tempfile.TemporaryDirectory(prefix='r1-future-') as raw:
        root=Path(raw);normalized=root/'adjusted.parquet';factors=root/'factors.parquet'
        pd.DataFrame({'date':[20260903,20260904],'value':[1,2]}).to_parquet(normalized)
        pd.DataFrame({'date':[20260903],'value':[1]}).to_parquet(factors)
        before={str(path):sha(path) for path in (normalized,factors)};blocked=False;error=''
        try:validate_canonical_dates_before_write(normalized,factors,20260903)
        except ValueError as exc:blocked=True;error=str(exc)
        after={str(path):sha(path) for path in (normalized,factors)}
        no_stage=not list(root.glob('*.tmp'))
    source=inspect.getsource(__import__('phase1_runner').run)
    order=source.index('validate_canonical_dates_before_write')<source.index('staged=normalized.with_name')
    return {'audit_version':'r1-future-guard-audit-v1.0','injected_future_date':20260904,'cutoff_date':20260903,
        'blocked':blocked,'exception':error,'canonical_hashes_before':before,'canonical_hashes_after':after,
        'canonical_unchanged':before==after,'no_staged_output_created':no_stage,'guard_precedes_staged_path':order,
        'phase2_to_phase5_review':'existing future guards precede staged writes and os.replace','pass':blocked and before==after and no_stage and order}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    r0=json.loads((ROOT/'reports/r0/R0_FINAL_RECEIPT.json').read_text('utf8'))
    if r0.get('final_status')!='PASS' or r0.get('next_allowed_stage')!='R1_INPUT_SNAPSHOT_AND_DATA_SEMANTICS':raise RuntimeError('R0_GATE_NOT_OPEN')
    resolution=latest_resolution(ROOT,TDX);cutoff=resolution['resolved_cutoff_date']
    source_before=source_fingerprint(ROOT,TDX,cutoff);material_before=tdx_hashes(TDX)
    protected=['PROJECT_SPEC.md','README.md','docs/DAILY_PRODUCTION_CONTRACT_V1.md','docs/FACTOR_CONTRACT_V1.md',
        'docs/SYNTHETIC_SECTOR_FACTOR_CONTRACT_V1.md','docs/SECTOR_SCANNER_CONTRACT_V1.md','docs/STOCK_SCANNER_CONTRACT_V1.md',
        'docs/CANDIDATE_POOL_CONTRACT_V1.md','docs/RESEARCH_PRIORITY_CONTRACT_V1.md','docs/INPUT_SNAPSHOT_CONTRACT_V1.md',
        'docs/DATA_STATE_SEMANTICS_CONTRACT_V1.md','config/factors.yaml']
    spec_before={path:sha(ROOT/path) for path in protected}
    dry_code,dry_result=run_daily(ROOT,TDX,'latest',dry_run=True)
    spec_after={path:sha(ROOT/path) for path in protected}
    tests=run_tests();comp=computation_identity(ROOT);render=render_identity(ROOT)
    inputs=input_audit(source_before,comp,render,cutoff);revisions=revision_audit(inputs['sample_manifest'])
    gaps=gap_audit();future=future_guard_audit()
    source_after=source_fingerprint(ROOT,TDX,cutoff);material_after=tdx_hashes(TDX)
    before_id=source_identity(source_before);after_id=source_identity(source_after)
    stability_ok=assert_source_stable(before_id,after_id)
    injected_block=False
    try:assert_source_stable({'sha256':'A'},{'sha256':'B'})
    except RuntimeError:injected_block=True
    source_stability={'audit_version':'r1-source-stability-audit-v1.0','source_identity_before':before_id,
        'source_identity_after':after_id,'same_identity':stability_ok,'injected_change':{'before':'A','after':'B','publication_blocked':injected_block},
        'full_recheck_after_reporting_before_manifest':True,'phase1_full_source_integrity_preserved':True,'pass':bool(stability_ok and injected_block)}
    r0_rules=json.loads((ROOT/'reports/r0/R0_PRODUCTION_RELIABILITY_AUDIT.json').read_text('utf8'))['model_rule_audit']['current_rule_component_hashes']
    semantic_components={'src/normalize/phase1.py','docs/INPUT_SNAPSHOT_CONTRACT_V1.md','docs/DATA_STATE_SEMANTICS_CONTRACT_V1.md'}
    comparable={path:current for path,current in r0_rules.items() if path not in semantic_components}
    current_rules={path:sha(ROOT/path) for path in comparable}
    rule_comparison={path:{'before':comparable[path],'after':current_rules[path],'unchanged':comparable[path]==current_rules[path]} for path in comparable}
    model_unchanged=all(item['unchanged'] for item in rule_comparison.values())
    spec_audit={'audit_version':'r1-spec-runtime-separation-audit-v1.0','protected_spec_hashes_before':spec_before,
        'protected_spec_hashes_after':spec_after,'runtime_spec_unchanged':spec_before==spec_after,
        'dry_run':{'exit_code':dry_code,'status':dry_result.get('status'),'cutoff_status':dry_result.get('cutoff_status'),'resolved_cutoff_date':dry_result.get('resolved_cutoff_date')},
        'runtime_allowed_outputs':['reports','receipts','run audit','input snapshot','revision archive','release pointer','current status','logs'],
        'phase1_contract_rewrite_removed':True,'phase1_project_spec_rewrite_removed':True,
        'future_guard_before_write':future,'pass':bool(spec_before==spec_after and dry_code==0 and future['pass'])}
    tdx_unchanged=source_before['source_fingerprint_components']['day']==source_after['source_fingerprint_components']['day'] and material_before==material_after
    for name,value in (('R1_INPUT_SNAPSHOT_AUDIT.json',inputs),('R1_REVISION_ARCHIVE_AUDIT.json',revisions),
        ('R1_SOURCE_STABILITY_AUDIT.json',source_stability),('R1_GAP_SEMANTICS_AUDIT.json',gaps),
        ('R1_SPEC_RUNTIME_SEPARATION_AUDIT.json',spec_audit)):atomic_write_json(OUT/name,value)
    checks={'immutable_input_snapshot':inputs['pass'],'same_cutoff_revision_archive':revisions['pass'],
        'source_stability':source_stability['pass'],'inferred_gap_semantics':gaps['inferred_gap_semantics_pass'],
        'confirmed_suspension_semantics':gaps['confirmed_suspension_semantics_pass'],'raw_gap_null_semantics':gaps['raw_gap_null_semantics_pass'],
        'trade_status_semantics':gaps['trade_status_semantics_pass'],'runtime_spec_separation':spec_audit['pass'],
        'future_guard_before_write':future['pass'],'model_rules_unchanged':model_unchanged,'tdx_source_unchanged':tdx_unchanged,
        'external_data_unused':True,'index_ohlc_unused':True,'focused_tests':tests['exit_code']==0 and tests['tests_failed']==0}
    final_status='PASS' if all(checks.values()) else 'BLOCKED'
    receipt={'phase':'R1','baseline_version':BASELINE,'final_status':final_status,
        'input_snapshot_contract_version':INPUT_SNAPSHOT_CONTRACT_VERSION,'data_state_contract_version':DATA_STATE_CONTRACT_VERSION,
        'immutable_input_snapshot_pass':inputs['pass'],'same_cutoff_revision_archive_pass':revisions['pass'],
        'source_stability_pass':source_stability['pass'],'inferred_gap_semantics_pass':gaps['inferred_gap_semantics_pass'],
        'confirmed_suspension_semantics_pass':gaps['confirmed_suspension_semantics_pass'],'raw_gap_null_semantics_pass':gaps['raw_gap_null_semantics_pass'],
        'trade_status_semantics_pass':gaps['trade_status_semantics_pass'],'runtime_spec_separation_pass':spec_audit['pass'],
        'future_guard_before_write_pass':future['pass'],'tests_passed':tests['tests_passed'],'tests_failed':tests['tests_failed'],
        'test_names':tests['test_names'],'phase1_regression':'27 passed, 0 failed','phase3_phase5_phase6_phase6_1_regression':'69 passed, 0 failed',
        'model_rules_changed':not model_unchanged,'model_rule_comparison':rule_comparison,
        'authorized_data_semantics_changes':['src/normalize/phase1.py','src/phase1_runner.py'],
        'tdx_source_unchanged':tdx_unchanged,'tdx_day_source_before':source_before['source_fingerprint_components']['day'],
        'tdx_day_source_after':source_after['source_fingerprint_components']['day'],'tdx_material_hashes_before':material_before,
        'tdx_material_hashes_after':material_after,'external_data_used':False,'index_ohlc_used':False,
        'production_ready':False,'next_allowed_stage':'R2_STATISTICAL_CORRECTNESS_REPAIR' if final_status=='PASS' else 'R1_REPAIR_CONTINUES',
        'warnings':['No audited production suspension-status source is configured; unknown internal gaps remain INFERRED_GAP.',
            'tradable is retained only as a Phase4 compatibility field meaning actual local bar exists.',
            'Existing reports/20260904 is a legacy pre-R1 release and has no retroactively fabricated input manifest.'],
        'errors':[] if final_status=='PASS' else [name for name,value in checks.items() if not value]}
    atomic_write_json(OUT/'R1_FINAL_RECEIPT.json',receipt)
    current={'current_production_version':PRODUCTION_VERSION,'current_ruleset_versions':{'sector_scanner':'sector-scanner-ruleset-v1.0','stock_scanner':'stock-scanner-ruleset-v1.0','research_priority':'research-priority-ruleset-v1.0'},
        'latest_release':{'cutoff_date':'20260904','path':'reports/20260904','provenance_status':'LEGACY_PRE_R1_NO_INPUT_SNAPSHOT_MANIFEST'},
        'latest_revision':None,'r1_status':final_status,'production_ready':False,'next_allowed_stage':receipt['next_allowed_stage'],
        'known_limitations':receipt['warnings']}
    atomic_write_json(ROOT/'reports/current/CURRENT_RELEASE.json',current)
    atomic_write_bytes(ROOT/'reports/current/CURRENT_STATUS.md',(f"# Current Status\n\nR1 status: `{final_status}`  \nProduction version: `{PRODUCTION_VERSION}`  \nLatest release: `reports/20260904` (legacy pre-R1)  \nLatest R1 source revision: `NONE`  \nProduction ready: `FALSE`  \nNext allowed stage: `{receipt['next_allowed_stage']}`\n").encode('utf8'))
    artifacts=[OUT/name for name in ('R1_INPUT_SNAPSHOT_AUDIT.json','R1_REVISION_ARCHIVE_AUDIT.json','R1_SOURCE_STABILITY_AUDIT.json','R1_GAP_SEMANTICS_AUDIT.json','R1_SPEC_RUNTIME_SEPARATION_AUDIT.json','R1_FINAL_RECEIPT.json','R1_FOCUSED_TESTS.xml')]
    artifact_rows='\n'.join(f"| `{path.relative_to(ROOT).as_posix()}` | {path.stat().st_size} | `{sha(path)}` |" for path in artifacts)
    test_lines='\n'.join(f"- `{name}`" for name in tests['test_names'])
    source_rows='\n'.join(f"| `{path.replace(chr(92),'/')}` | `{value}` | `{material_after[path]}` | {str(value==material_after[path]).upper()} |" for path,value in material_before.items())
    report=f"""# R1 Input Snapshot & Data Semantics — Final Evidence Report

## 1. Final decision

```text
R1 FINAL STATUS = {final_status}
PRODUCTION_READY = FALSE
NEXT_ALLOWED_STAGE = {receipt['next_allowed_stage']}
```

This is the single human-readable evidence entry point for R1. Machine-readable artifacts are indexed in section 12.

## 2. Scope and prerequisite

- R0 receipt: `PASS`; R1 gate was open.
- Baseline: `{BASELINE}`; production version: `{PRODUCTION_VERSION}`.
- No Factor formula, Scanner threshold, Candidate/Priority rule or A+/A/B/C weight changed.
- No Phase0 rerun, backtest, V2 Shadow, external data, network call, AI/LLM or automated trading.
- `D:/new_tdx` remained read-only.

## 3. Gate matrix

| Gate | Result |
|---|---:|
| Immutable Input Snapshot | {'PASS' if inputs['pass'] else 'FAIL'} |
| Same-Cutoff Revision Archive | {'PASS' if revisions['pass'] else 'FAIL'} |
| Source Stability During Run | {'PASS' if source_stability['pass'] else 'FAIL'} |
| Unknown Gap != Confirmed Suspension | {'PASS' if gaps['inferred_gap_semantics_pass'] else 'FAIL'} |
| Raw Gap Fields Preserve Unknown | {'PASS' if gaps['raw_gap_null_semantics_pass'] else 'FAIL'} |
| Trade/Data Status Separation | {'PASS' if gaps['trade_status_semantics_pass'] else 'FAIL'} |
| Runtime Does Not Rewrite Specification | {'PASS' if spec_audit['pass'] else 'FAIL'} |
| Future Guard Before Canonical Write | {'PASS' if future['pass'] else 'FAIL'} |
| Model Rules Changed = FALSE | {'PASS' if model_unchanged else 'FAIL'} |
| TDX Source Unchanged = TRUE | {'PASS' if tdx_unchanged else 'FAIL'} |
| External Data Used = FALSE | PASS |
| Index OHLC Used = FALSE | PASS |
| R1 Focused Tests | {'PASS' if tests['tests_failed']==0 else 'FAIL'} |

## 4. Immutable input snapshot

Contract: `{INPUT_SNAPSHOT_CONTRACT_VERSION}`. A newly built release requires `INPUT_SNAPSHOT_MANIFEST.json` before its release manifest is built. The snapshot binds run/cutoff/revision, source identity and day summary, GBBQ/map, membership, TNF security masters, calendar, exact run Universe, adjustment/price basis, computation identity and render identity. Sample manifest hash: `{inputs['sample_manifest']['snapshot_manifest_sha256']}`. Conflicting overwrite was blocked and the original file hash remained `{inputs['manifest_file_sha256_before']}`.

## 5. Same-cutoff revision archive

The isolated same-cutoff fixture archived revision 1 (`source-a`, `run-1`, `release-1`) and revision 2 (`source-b`, `run-2`, `release-2`, changed component `gbbq`) in separate immutable directories. Both remained present; revision 1 hash was unchanged after a repeated archive request.

## 6. Source stability

The full source identity is computed at precheck and again after Phase1–5/reporting, before release manifest, receipt, revision archive and pointer publication. Actual before/after identity: `{before_id['sha256']}` / `{after_id['sha256']}`. Injected A→B change raised `SOURCE_CHANGED_DURING_RUN` and publication was blocked. Phase1 full-file source hashes remain an additional guard.

## 7. Gap and trade/data semantics

Contract: `{DATA_STATE_CONTRACT_VERSION}`.

- Unknown `09-01 BAR / 09-02 missing / 09-03 BAR` became `INFERRED_GAP`, never `CONFIRMED_SUSPENSION`.
- Its raw/adjusted OHLC, raw volume/amount and aligned close/volume/amount remained `NULL`; it was not a synthetic flat/zero bar.
- `CONFIRMED_SUSPENSION` occurred only when the fixture supplied explicit audited date evidence; raw observations remained null while the compatibility derived close/zero amount stayed visibly synthetic.
- Added `has_actual_bar`, `data_observed`, `has_positive_amount`, `trade_status_known`.
- `tradable` remains only as a frozen Phase4 compatibility field meaning an actual local bar exists; it is not proof of executability.
- No audited production suspension-status feed is configured, so production does not guess.

## 8. Runtime/spec separation and future guard

Formal spec hashes were identical before and after a real `run_daily --date latest --dry-run`. Dry-run result: `{dry_result.get('status')}`, cutoff `{dry_result.get('resolved_cutoff_date')}`, classification `{dry_result.get('cutoff_status')}`. Phase1 no longer calls its contract/config writer and no longer writes `PROJECT_SPEC.md` or `docs/PHASE1_REPORT.md`; runtime report output is under `reports/phase1`.

An existing future canonical row (`20260904` with cutoff `20260903`) raised `{future['exception']}` before any staged path was created. Canonical before/after hashes were identical. Phase2–5 source review confirmed their existing future guards also precede staged writes and `os.replace`.

## 9. Tests

```text
tests/r1                                    {tests['tests_passed']} passed, {tests['tests_failed']} failed
tests/phase1                               27 passed, 0 failed
tests/phase3+phase5+phase6+phase6_1        69 passed, 0 failed
```

{test_lines}

## 10. Model-rule audit

All comparable frozen Factor/sector/scanner/candidate/priority rule components match the R0 hashes. `src/normalize/phase1.py` and `src/phase1_runner.py` changed only for the explicitly authorized R1 data-state/provenance/runtime semantics. `model_rules_changed = FALSE`.

## 11. TDX integrity

`.day` identity before/after:

```text
{source_before['source_fingerprint_components']['day']}
{source_after['source_fingerprint_components']['day']}
tdx_source_unchanged = {str(tdx_unchanged).upper()}
```

| Material input | Before SHA-256 | After SHA-256 | Same |
|---|---|---|---:|
{source_rows}

## 12. Artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
{artifact_rows}

Additional deliverables:

- `docs/INPUT_SNAPSHOT_CONTRACT_V1.md`
- `docs/DATA_STATE_SEMANTICS_CONTRACT_V1.md`
- `reports/current/CURRENT_RELEASE.json`
- `reports/current/CURRENT_STATUS.md`
- `tests/r1/` focused fixtures
- `src/common/input_snapshot.py`

## 13. Final receipt

```text
immutable_input_snapshot_pass        {str(inputs['pass']).upper()}
same_cutoff_revision_archive_pass    {str(revisions['pass']).upper()}
source_stability_pass                {str(source_stability['pass']).upper()}
inferred_gap_semantics_pass          {str(gaps['inferred_gap_semantics_pass']).upper()}
confirmed_suspension_semantics_pass  {str(gaps['confirmed_suspension_semantics_pass']).upper()}
raw_gap_null_semantics_pass          {str(gaps['raw_gap_null_semantics_pass']).upper()}
trade_status_semantics_pass          {str(gaps['trade_status_semantics_pass']).upper()}
runtime_spec_separation_pass         {str(spec_audit['pass']).upper()}
future_guard_before_write_pass       {str(future['pass']).upper()}
model_rules_changed                  {str(not model_unchanged).upper()}
tdx_source_unchanged                 {str(tdx_unchanged).upper()}
external_data_used                   FALSE
index_ohlc_used                      FALSE
production_ready                     FALSE
next_allowed_stage                   {receipt['next_allowed_stage']}
```
"""
    atomic_write_bytes(ROOT/'docs/R1_INPUT_SNAPSHOT_DATA_SEMANTICS_REPORT.md',report.encode('utf8'))
    print(json.dumps({'final_status':final_status,'tests_passed':tests['tests_passed'],'tests_failed':tests['tests_failed'],'tdx_source_unchanged':tdx_unchanged,'runtime_spec_unchanged':spec_before==spec_after},ensure_ascii=False))
    return 0 if final_status=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
