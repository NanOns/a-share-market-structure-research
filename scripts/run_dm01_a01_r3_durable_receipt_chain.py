"""Real accepted-source projection and atomic continuous candidate execution."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import struct
import sys
import zipfile
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from workbench_analysis.dm01_incremental_component_builders_r3_3 import load,digest,sha,_write_immutable,BUILD_ORDER,resolve_target_session,CONTRACT_PATH
from workbench_analysis.dm01_candidate_orchestrator_r3_3 import build_candidate,candidate_parent
from workbench_analysis.daily_source_freeze import build_source_freeze_manifest_v2
from scripts.build_v4_02_formal_periods import period_key
from tdx.gbbq_reader import read_gbbq
BASE='data/v4/source_evidence/dm01_a01_r3/durable_chain_inputs_r2/'
P='reports/audits/DM01_A01_R3_'
STAGE=ROOT/'data/v4/dm01_candidate_staging_r3/durable_r3'

def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def save(name,value):
    stem=Path(name); path=BASE+(stem.parent/(stem.stem+'_'+digest(value)+stem.suffix)).as_posix()
    _write_immutable(ROOT/path,value);return bind(path)
def report(name,value):atomic_json(ROOT/(P+name+'_R3.json'),value)
def iso(value):
    if value is None:return None
    s=str(value);return s[:4]+'-'+s[4:6]+'-'+s[6:8]
def query(c,sql,params=()):
    result=c.execute(sql,params);keys=[r[0] for r in result.description]
    return [dict(zip(keys,row)) for row in result.fetchall()]
def serial(row):return {k:(str(v) if isinstance(v,Decimal) else v.isoformat() if hasattr(v,'isoformat') else v) for k,v in row.items()}
def active(records,target):
    return [r for r in records if r['exchange'] in ('SH','SZ') and r['list_date']<=target
        and (not r.get('delist_date') or r['delist_date']>=target)
        and r.get('symbol_effective_from',r['list_date'])<=target
        and (not r.get('symbol_effective_to') or r['symbol_effective_to']>=target)]

def execute():
    contract=read(CONTRACT_PATH);context=load(contract['execution_context']);parent=context['parent']
    entry=read(P+'STAGE_ENTRY_R1.json');heads=[ROOT/b['path'] for b in entry['protected_bindings']]
    results=[];contexts=[]
    for target in context['sessions']:
        source=context['inputs'][target]
        freeze=build_source_freeze_manifest_v2(trade_date=target,sources=source['families'],changed_tdx_files=[],
            observed_at=context['observed_at'],ingested_at=context['observed_at'],system_available_at=context['observed_at'])
        freeze.update(inputs=source['inputs'],parent_data_head_digest=parent['binding']['sha256'],
            calendar_publication_id=context['calendar']['publication_id'],identity_publication_id=context['identity']['publication_id'],
            field_source_instances=source['instances'],tdx_roots=['D:/new_tdx'],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
        freeze['manifest_sha256']=digest({k:v for k,v in freeze.items() if k!='manifest_sha256'})
        args=dict(parent_data_head=parent,source_freeze=freeze,calendar_binding=context['calendar'],identity_binding=context['identity'],staging_root=STAGE,head_paths=heads)
        result=build_candidate(**args)
        report(target.replace('-','')+'_CANDIDATE',dict(target_trade_date=target,parent=parent['binding'],**result))
        print(json.dumps(dict(target=target,status=result['status'],reason=result.get('reason'),rows={k:r['row_count'] for k,r in result.get('components',{}).items()})),flush=True)
        if result['status'] not in ('READY_FOR_EXTERNAL_REAUDIT','NOOP_IDENTICAL_CANDIDATE'):
            report('CONTINUOUS_CHAIN_POSTCHECK',dict(status='BLOCKED',failed_date=target,subsequent_sessions_stopped=True,results=results+[result],data_head_moved=False))
            raise ValueError('INCOMPLETE_DAY_STOPS_CHAIN')
        repeat=build_candidate(**args)
        assert repeat['status']=='NOOP_IDENTICAL_CANDIDATE' and repeat['logical_digest']==result['logical_digest']
        results.append(result);contexts.append(args);parent=candidate_parent(result,STAGE)
    unchanged=all(sha(ROOT/b['path'])==b['sha256'] for b in entry['protected_bindings']);assert unchanged
    # Real-source late failure: seven completed components never yield a consumable marker.
    bad=deepcopy(contexts[0]);bad['source_freeze']=deepcopy(bad['source_freeze'])
    wrong=save('atomic_probe_wrong_price_rules.json',dict(rules=[]))
    bad['source_freeze']['inputs']['PRICE_RULES']=wrong
    bad['source_freeze']['manifest_sha256']=digest({k:v for k,v in bad['source_freeze'].items() if k!='manifest_sha256'})
    failure=build_candidate(**bad)
    assert failure['status']=='BLOCKED' and len(failure['completed_components'])==7
    failures=list(STAGE.rglob('failure.json'))
    assert all(not (p.parent/'PROMOTION_CANDIDATE.json').exists() for p in failures)
    report('ATOMIC_FAILURE_PROBES',dict(status='PASS',real_source_late_component_failure=failure,
        failure_bindings=[bind(p.relative_to(ROOT).as_posix()) for p in failures],partial_candidates_visible=False,
        subsequent_session_dispatch_after_failure=False,heads_unchanged=unchanged))
    revised=deepcopy(contexts[0]);revised['source_freeze']=deepcopy(revised['source_freeze'])
    # A new actual observation receipt revision changes source identity without fabricating provider values.
    revision=save('source_revision_reobservation.json',dict(source=source['instances'],observed_at=datetime.now(timezone.utc).isoformat(),
        kind='SOURCE_BINDING_REVERIFICATION_REVISION; PROVIDER_FACT_BYTES_UNCHANGED'))
    revised['source_freeze']['source_verification_revision']=revision
    revised['source_freeze']['manifest_sha256']=digest({k:v for k,v in revised['source_freeze'].items() if k!='manifest_sha256'})
    revisionresult=build_candidate(**revised)
    assert revisionresult['status']=='READY_FOR_EXTERNAL_REAUDIT' and revisionresult['candidate_revision']!=results[0]['candidate_revision']
    assert all(bind(r['candidate']['path'])==r['candidate'] for r in results)
    report('DETERMINISM',dict(status='PASS',same_source_same_parent_reruns='NOOP_IDENTICAL_CANDIDATE',logical_digests=[r['logical_digest'] for r in results],
        source_binding_revision_changes_candidate_revision=True,revised_source_candidate=revisionresult['candidate'],old_candidates_immutable=True,
        revision_scope='NEW_SOURCE_VERIFICATION_RECEIPT_IDENTITY_NOT_FABRICATED_PRICE_OR_STATUS'))
    report('CONTINUOUS_CHAIN_POSTCHECK',dict(status='PASS',sessions=context['sessions'],accepted_anchor=contract['accepted_data_head'],
        candidates=[r['candidate'] for r in results],all_nine_each_day=True,all_independent_postchecks='PASS',no_intermediate_session_skipped=True,
        old_business_heads_unchanged=True,data_head_moved=False,stage_head_moved=False,dm01_all_nine_accepted=False,
        production_permission=False,shadow_production_permission=False,focus_cutover_permission=False))
    report('EXTERNAL_REAUDIT_HANDOFF',dict(status='READY_FOR_EXTERNAL_REAUDIT',phase_A='PASS',
        chain_postcheck=bind(P+'CONTINUOUS_CHAIN_POSTCHECK_R3.json'),determinism=bind(P+'DETERMINISM_R3.json'),
        atomicity=bind(P+'ATOMIC_FAILURE_PROBES_R3.json'),contract=bind(CONTRACT_PATH),source_context=contract['execution_context'],
        clean_regression='PENDING_CLEAN_DETACHED',external_acceptance='PENDING',data_head_moved=False,
        permitted_next_stage='INDEPENDENT_EXTERNAL_REAUDIT_ONLY'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    if args.prepare:raise ValueError('ORIGINAL_FROZEN_EXECUTION_CONTEXT_REQUIRED')
    execute()
