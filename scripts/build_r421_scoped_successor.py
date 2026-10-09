"""Build immutable successor registry and admission request, never accepted heads."""
import argparse
import math
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from workbench_analysis.scoped_successor_r421 import CONTRACT_ID, atomic, canonical, candidate_cas, rollback, sha

OUT = ROOT / 'docs/evidence/r4_2_1_20261009'
OLD = ROOT / 'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1'

def ref(path):
    path=path.resolve()
    path = Path(path)
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)

def write(name, value):
    atomic(OUT / name, canonical(value))
    return ref(OUT / name)

def verify(binding):
    p = ROOT / binding['path']
    return dict(binding=binding, actual=ref(p), exact=sha(p) == binding['sha256'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delta-receipt', type=Path)
    args = parser.parse_args()
    protected = [ROOT / 'data/v4/V4_DATA_ACCEPTED_HEAD.json', ROOT / 'data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json', ROOT / 'config/dm01_go_forward_runtime_contract_r4r1.json', OLD / 'OWNER_STAGE_SEAL_V1.json']
    before = [ref(p) for p in protected]
    contract = json.loads(protected[2].read_bytes())
    mismatch = [v for v in map(verify, contract['runtime_bindings']) if not v['exact']]
    tracked={b['path']:b for b in contract['runtime_bindings']}
    commits=['fb627cfc23931ff493a1a0f81ed6d081b3382dc4','e5da08e30dbcdf9330f3f9e338393ef02b78b0c7','c010b818811689ed3056c6500ca5caa5cbadde4e','fc40acc4ceb4a41002ee3a0ba8ce75f9d7885bc5']
    attribution=[dict(path=p,commit=commit,git_blob_sha256=hashlib.sha256(subprocess.check_output(['git','show',commit+':'+p],cwd=ROOT)).hexdigest(),seal_expected=tracked[p]['sha256']) for p in ['scripts/run_v4_dm01_daily_increment.py','scripts/build_dm01_r4_tdx_delta.py'] for commit in commits]
    write('REGISTRY_PREDECESSOR_GIT_ATTRIBUTION.json', attribution)
    bindings = [ref(ROOT / b['path']) for b in contract['runtime_bindings']]
    for name in ['scripts/run_v4_current_daily.py','src/workbench_analysis/tdx_snapshot_delta_v2.py', 'config/tdx_a_stock_delta_scope_policy_v2.json', 'src/workbench_analysis/scoped_successor_r421.py', 'scripts/build_r421_scoped_successor.py', 'src/workbench_analysis/sector_taxonomy_v2.py', 'config/v4_primary_sector_taxonomy_v2.json', 'src/workbench_analysis/dm01_corrected_source_capture_v2.py', 'config/dm01_corrected_source_capability_v2.json']:
        if (ROOT / name).is_file(): bindings.append(ref(ROOT / name))
    successor = dict(contract_id='R421_BUILDER_REGISTRY_SUCCESSOR_CANDIDATE_V1', predecessor=ref(protected[2]), predecessor_acceptance=ref(protected[1]), status='CANDIDATE_NOT_EXTERNALLY_ACCEPTED', runtime_bindings=bindings, source_contract='TDX_A_STOCK_PACKAGE_DELTA_V2', source_scope_admission='CORRECTED_STAGING_ONLY', source_mode='RECONSTRUCTED_CORRECTED', AS_RECORDED=False, primary_taxonomy='TDX_INDUSTRY_CONCEPT', production_permission=False, accepted_head_replacement=False, run_window=['2026-09-28','2026-09-29','2026-09-30','2026-10-08'], permissions_required=['INDEPENDENT_TYPED_SOURCE_QA','CORRECTED_CORE_PROFILE_INDEPENDENT_QA','NEW_SCOPED_PUBLICATION_CONTRACT_ACCEPTANCE'])
    seal = write('BUILDER_REGISTRY_SUCCESSOR_CANDIDATE_V1.json', successor)
    write('NEW_BUILDER_SEAL_AND_SOURCE_CONTRACT_MIGRATION.json', dict(contract_id='R421_BUILDER_MIGRATION_V1', old_runtime_contract=ref(protected[2]), old_acceptance=ref(protected[1]), exact_mismatches=mismatch, git_attribution=ref(OUT/'REGISTRY_PREDECESSOR_GIT_ATTRIBUTION.json'), attribution_conclusion='Old seal exactly binds fb627cfc runtime entry and delta script. Entry first changes at e5da08e; delta script changes at fc40acc4. These are code revisions, not newline representation drift.', successor=seal, successor_binding_self_check=all(verify(b)['exact'] for b in bindings), numerical_kernel_changed=False, historical_seal_modified=False, legacy_validation_result='INPUT_DIGEST_MISMATCH_EXPECTED_FAIL_CLOSED', acceptance_matrix=dict(old_PIT_runtime='ACCEPTED_PREDECESSOR_BYTES_ONLY', typed_V2_source='CORRECTED_STAGING_ONLY', new_registry='INDEPENDENT_ADMISSION_REQUIRED', production='NO_EXISTING_PERMISSION_FOR_CORRECTED_SCOPED_SUCCESSOR'), rollback='Original production pointer unchanged; isolated candidate exact predecessor rollback exercised'))
    numeric = ROOT / 'docs/evidence/r4_1_audit_repair_r1_20261009/BYTE_NUMERIC_READBACK.json'
    baseline = json.loads(numeric.read_bytes())
    assert baseline['errors'] == [] and baseline['acceptance'] == 'PASS_SCOPED_LOCAL_BYTES_AND_WINDOW_ARITHMETIC'
    owners = []
    for day in successor['run_window']:
        folder = OLD / 'owners' / day
        owner = json.loads((folder / 'OWNER.json').read_bytes())
        profile = json.loads((folder / 'PROFILE_STRUCTURE_OWNER.json').read_bytes())
        selected = {key: verify(owner[key]) for key in ['raw','core','prior_core']}
        selected['profiles'] = ref(folder / 'profiles.jsonl.gz')
        profile_state_fields=set(); profile_rows=0
        with gzip.open(folder / 'profiles.jsonl.gz', 'rt', encoding='utf8') as stream:
            for line in stream:
                record=json.loads(line); profile_rows+=1
                profile_state_fields.update(record.get('states',{}))
                assert record.get('AS_RECORDED') is False
        assert profile_rows==owner['rows']
        assert not any('sector' in field.lower() or 'rotation' in field.lower() for field in profile_state_fields)
        selected['profiles']['field_isolation_check']=dict(row_count=profile_rows,state_fields=sorted(profile_state_fields),sector_rotation_fields=[],acceptance='PASS_STOCK_PROFILE_FIELDS_ONLY')
        sources = {key: verify(value) for key, value in owner['sources'].items()}
        rows = []
        with gzip.open(folder / 'raw.jsonl.gz', 'rt', encoding='utf8') as stream:
            for line in stream: rows.append(json.loads(line))
        assert all(v['exact'] for v in sources.values()) and all(selected[k]['exact'] for k in ['raw','core','prior_core'])
        assert len(rows)==owner['actual_raw_rows']
        typed_path = OUT / 'typed_delta' / day / 'delta_v2.json'
        comparison = dict(status='PENDING_TYPED_DELTA_RUNTIME_OUTPUT', actual_missing_input=str(typed_path))
        if typed_path.is_file():
            typed = json.loads(typed_path.read_bytes())
            expected = {r['security_id']: r for r in rows}
            bars = typed['target_bars']
            actual = {r['security_id']: r for r in bars}
            assert len(actual)==len(bars)
            fields=['open','high','low','close','volume','amount']
            differences=[]
            for sid in sorted(set(actual)&set(expected)):
                for field in fields:
                    if not math.isclose(float(actual[sid][field]),float(expected[sid][field]),rel_tol=0,abs_tol=1e-9):
                        differences.append(dict(security_id=sid,field=field,typed=actual[sid][field],owner=expected[sid][field]))
            comparison=dict(status='PASS_EXACT_TARGET_VALUES' if not differences else 'FAIL_NUMERIC_DIFFERENCES', typed_delta=ref(typed_path), common_security_count=len(set(actual)&set(expected)), six_field_check_count=6*len(set(actual)&set(expected)), differences=differences, typed_only=sorted(set(actual)-set(expected)), owner_only=sorted(set(expected)-set(actual)), semantic_note='Unmatched identities remain scope differences; this comparison does not admit them automatically')
            assert not differences
        owners.append(dict(trade_date=day, owner=ref(folder / 'OWNER.json'), profile_owner=ref(folder / 'PROFILE_STRUCTURE_OWNER.json'), source_digest=owner['source_digest'], row_count=owner['rows'], exact_source_bindings=sources, artifacts=selected, typed_delta_comparison=comparison, known=owner['known_fields'], profile_known_unknown=profile['counts'], raw_logical_digest=hashlib.sha256(canonical(rows)).hexdigest(), raw_actual_rows=len(rows), numeric_prior_evidence=next(x for x in baseline['numeric'] if x['trade_date']==day), source_mode=owner['knowledge_lineage'], AS_RECORDED=owner['AS_RECORDED']))
    delta = None
    if args.delta_receipt:
        delta = dict(binding=ref(args.delta_receipt), receipt=json.loads(args.delta_receipt.read_bytes()))
    reconciliation = dict(contract_id='R421_CORRECTED_OWNER_RECONCILIATION_V1', owners=owners, independent_numeric_baseline=ref(numeric), delta_v2=delta, original_528_and_35_suspension_baseline='PRESERVED; no original artifact overwritten', corrected_candidate_rebuilt=False, source_consistency='EXACT_BYTE_BINDINGS_RECHECKED; typed target bar cross-comparison pending unless separately attached', domains=dict(RAW='CORRECTED_CANDIDATE',Core_Profile='CORRECTED_CANDIDATE_WITH_EXISTING_INDEPENDENT_NUMERIC_ORACLE',Seed='STOCK_ONLY_LINEAGE_SEPARATE_REVIEW',TDX_sector='NO_ACCEPTED_TDX_DATED_MEMBERSHIP_WHERE_UNPROVEN',CSRC='AUXILIARY_ONLY',strict_PIT='EXCLUDED',BJ_unapproved_identity='EXCLUDED',prior_breakout='UNKNOWN_NOT_FALSE',legal_price_limit='EXCLUDED_FROM_SCOPED_ADMISSION'))
    recon = write('OCT08_CORRECTED_OWNER_SOURCE_RECONCILIATION.json', reconciliation)
    candidate = dict(contract_id=CONTRACT_ID, target_trade_date='2026-10-08', source_mode='RECONSTRUCTED_CORRECTED', AS_RECORDED=False, domains=['OFFICIAL_TDX_RAW_CURRENT_CANONICAL_SUBSET','CORRECTED_CORE_PROFILE'], production_permission=False, primary_taxonomy='TDX_INDUSTRY_CONCEPT', registry=seal, reconciliation=recon, predecessor=before[0], status='SCOPED_ADMISSION_REQUEST', exclusions=['TDX_DATED_SECTOR_WITHOUT_EVIDENCE','CSRC_PRIMARY_SUBSTITUTION','UNAPPROVED_BJ_IDENTITY','STRICT_PIT','PRIOR_BREAKOUT_ABSENCE','LEGAL_PRICE_LIMIT','MARKET_STRESS','FOCUS_FORWARD_PRODUCTION'])
    from workbench_analysis.sector_taxonomy_v2 import primary_projection
    candidate['primary_sector_capabilities']=primary_projection('2026-10-08',[],lambda rows:None)
    taxonomy=OUT/'TAXONOMY_STAGE_ACCEPTANCE.json'
    if taxonomy.exists():candidate['taxonomy_isolation_evidence']=ref(taxonomy)
    candidate_ref = write('SCOPED_SUCCESSOR_CANDIDATE.json', candidate)
    Path('E:/r421_scoped_cas').mkdir(parents=True, exist_ok=True)
    store = Path(tempfile.mkdtemp(prefix='candidate_', dir='E:/r421_scoped_cas'))
    first = candidate_cas(store, candidate, None)
    noop = candidate_cas(store, candidate, first['sha256'])
    try:
        candidate_cas(store,candidate,'0'*64)
        raise AssertionError('same bytes stale CAS accepted')
    except ValueError as error:
        assert str(error)=='STALE_CANDIDATE_CAS'
    changed = dict(candidate, candidate_revision=2)
    checks = {'same_hash_stale_CAS':dict(status='PASS',actual_error='STALE_CANDIDATE_CAS')}
    for name, call, reason in [('bad_source_digest',lambda:candidate_cas(store,dict(changed,registry=dict(seal,sha256='0'*64)),first['sha256']),'SCOPED_BINDING_DIGEST_MISMATCH'),('stale_cas', lambda: candidate_cas(store, changed, '0'*64), 'STALE_CANDIDATE_CAS'), ('fail_injection', lambda: candidate_cas(store, changed, first['sha256'], inject_failure=True), 'INJECTED_BEFORE_REPLACE'), ('wrong_namespace', lambda: candidate_cas(store, dict(changed,primary_taxonomy='BAOSTOCK_CSRC_INDUSTRY'), first['sha256']), 'PRIMARY_TAXONOMY_REQUIRED'), ('production_escalation', lambda: candidate_cas(store, dict(changed,production_permission=True), first['sha256']), 'PRODUCTION_PERMISSION_FORBIDDEN'), ('forged_PIT', lambda: candidate_cas(store, dict(changed,AS_RECORDED=True), first['sha256']), 'CORRECTED_LINEAGE_REQUIRED')]:
        try: call(); raise AssertionError(name + ' unexpectedly succeeded')
        except ValueError as error:
            assert str(error)==reason
            assert sha(store / 'SCOPED_CANDIDATE_POINTER.json')==first['sha256']
            checks[name]=dict(status='PASS', actual_error=str(error), unchanged_pointer=True)
    second = candidate_cas(store, changed, first['sha256'])
    try: rollback(store, second['sha256'], 'f'*64); raise AssertionError('wrong predecessor accepted')
    except (FileNotFoundError,ValueError) as error: checks['wrong_rollback_predecessor']=dict(status='PASS',actual_error=type(error).__name__)
    back = rollback(store, second['sha256'], first['sha256'])
    assert back['sha256']==first['sha256']
    assert [ref(p) for p in protected]==before
    write('SCOPED_SUCCESSOR_QA_AND_CAS_READBACK.json', dict(contract_id='R421_SCOPED_CAS_QA_V1', observed_at=datetime.now(timezone.utc).isoformat(), candidate=candidate_ref, production_admission='BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION', exact_missing_authority='Current policy requires all nine PIT-observed next-session components and does not authorize reconstructed corrected RAW/Core/Profile subset. No externally signed successor policy exists.', production_data_head_moved=False, protected_bytes_unchanged=before, test_store=str(store), actual_disk_CAS=[first,noop,second,back], negative_tests=checks, test_scope='ISOLATED_CANDIDATE_POINTER_ONLY; not production promotion', acceptance='PASS_STAGING_MECHANICS_ONLY; source and numerical admission remain independent gates'))
    write('SCOPED_ADMISSION_REQUEST.json',dict(candidate=candidate_ref, required_independent_reviews=successor['permissions_required'], production_action_requested='Review scoped corrected candidate; no accepted-head mutation authorized by this request', predecessor=before[0], source_mode='RECONSTRUCTED_CORRECTED', excluded_domains=candidate['exclusions']))
    print(json.dumps(dict(status='SUCCESSOR_CANDIDATE_AND_ISOLATED_CAS_READY',mismatches=len(mismatch),owners=len(owners),production_data_head_moved=False)))

if __name__ == '__main__': main()
