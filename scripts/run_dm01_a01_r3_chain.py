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
from workbench_analysis.dm01_incremental_component_builders_r3 import load,digest,sha,_write_immutable,BUILD_ORDER,resolve_target_session,CONTRACT_PATH
from workbench_analysis.dm01_candidate_orchestrator_r3 import build_candidate,candidate_parent
from workbench_analysis.daily_source_freeze import build_source_freeze_manifest_v2
from scripts.build_v4_02_formal_periods import period_key
from tdx.gbbq_reader import read_gbbq
BASE='data/v4/source_evidence/dm01_a01_r3/chain_inputs_r1/'
P='reports/audits/DM01_A01_R3_'
STAGE=ROOT/'data/v4/dm01_candidate_staging_r3'

def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def save(name,value):
    stem=Path(name); path=BASE+(stem.parent/(stem.stem+'_'+digest(value)+stem.suffix)).as_posix()
    _write_immutable(ROOT/path,value);return bind(path)
def report(name,value):atomic_json(ROOT/(P+name+'_R1.json'),value)
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

def prepare():
    if read('reports/audits/A10_A12_R3_EXTERNAL_ACCEPTANCE_FORMALIZATION_R1.json')['phase_A']!='PASS':
        raise ValueError('PHASE_A_MUST_PASS_FIRST')
    now=datetime.now(timezone.utc).isoformat()
    dataref=bind('data/v4/V4_DATA_ACCEPTED_HEAD.json');datahead=load(dataref);cutoff=datahead['accepted_trade_date'];cutnum=int(cutoff.replace('-',''))
    old=read('config/dm01_incremental_builders_contract_r1.json')
    ih=bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json');idhead=load(ih);idref=idhead['identity_revision']
    original=load(idref)['records']
    records=[dict(r,board_scope=r['exchange']+'_MAIN' if r['board']=='MAIN' else r['board'],system_available_at=now) for r in original]
    ir=save('identity_projection.json',dict(contract_id='ACCEPTED_IDENTITY_NORMALIZED_VIEW_R3',accepted_head_binding=ih,
        source_identity_binding=idref,projection_observed_at=now,records=records,AS_RECORDED=False))
    identity=dict(status='ACCEPTED',publication_id=ir['sha256'],binding=ir,records=records)
    ch=old['accepted_calendar_head'];calhead=load(ch);extension=load(calhead['accepted_extension'])
    historical='data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json'
    histref=bind(historical)
    sessions=sorted(set(load(histref)['session_dates'])|{r['trade_date'] for r in extension['sessions']})
    cp=dict(accepted_head_binding=ch,accepted_historical_calendar=histref,session_dates=sessions,coverage_end=calhead['coverage_end'])
    cr=save('calendar_union.json',cp)
    calendar=dict(status='ACCEPTED',publication_id=cr['sha256'],binding=cr,payload_digest=digest(cp),**cp)
    completed=[];cursor=cutoff
    while True:
        try:target=resolve_target_session(cursor,calendar,now)
        except ValueError as exc:
            if str(exc) in ('BLOCKED_CALENDAR_COVERAGE','WAIT_MARKET_CLOSE'):break
            raise
        completed.append(target);cursor=target
    assert completed
    report('SESSION_RESOLUTION',dict(status='PASS',accepted_data_head=dataref,parent_date=cutoff,accepted_calendar_head=ch,
        calendar_union=cr,next_completed_sessions=completed,observed_at=now,
        resolver='MIN_ACCEPTED_COMPLETED_SESSION_STRICTLY_AFTER_PARENT',hardcoded_pipeline_sessions=False))
    activeparent=active(records,cutoff);sids={r['security_id'] for r in activeparent};keys={r['source_security_key'] for r in activeparent}
    daily='data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet'
    weekly='data/v4/artifact_store/v4_02/V4_02_FORMAL_WEEKLY_RAW_QFQ_R7_20260927.parquet'
    monthly='data/v4/artifact_store/v4_02/V4_02_FORMAL_MONTHLY_RAW_QFQ_R7_20260927.parquet'
    status='data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz'
    st='data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_R7_20260927.jsonl.gz'
    price='data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_20260927.jsonl.gz'
    accepted_sources=[bind(p) for p in (daily,weekly,monthly,status,st,price,'data/v4/V4_02_ACCEPTED_HEAD.json',idref['path'])]
    c=duckdb.connect();c.execute('SET threads=4')
    c.execute('CREATE TEMP TABLE canonical AS SELECT * FROM read_parquet(?)',[str(ROOT/daily)])
    actual=query(c,'SELECT * FROM canonical WHERE trade_date=?',[cutnum])
    latest=query(c,'SELECT canonical_security_id,source_security_key,raw_close,trade_date FROM canonical WHERE trade_date<=? QUALIFY row_number() over (partition by canonical_security_id order by trade_date desc)=1',[cutnum])
    latestby={r['canonical_security_id']:r for r in latest}
    parents={}
    for cap in BUILD_ORDER:
        if cap=='IDENTITY_UNIVERSE':rows=[dict(r,trade_date=cutoff) for r in activeparent]
        elif cap in ('RAW_DAILY','ADJUSTED_DAILY'):
            rows=[]
            for r in actual:
                if r['source_security_key'] not in keys:continue
                prices={p:r[('raw_' if cap=='RAW_DAILY' else 'qfq_')+p] for p in ('open','high','low','close')}
                rows.append(serial(dict(security_id=r['canonical_security_id'],source_security_key=r['source_security_key'],trade_date=cutoff,
                    **prices,volume=r['volume'],amount=r['amount'],board_scope=r['board_scope'],adjusted_quality=r['adjusted_quality'])))
        elif cap in ('TRADING_STATUS','ISST','PRICE_LIMIT'):
            source={'TRADING_STATUS':status,'ISST':st,'PRICE_LIMIT':price}[cap]
            rows=[serial(r) for r in query(c,'SELECT * FROM read_json_auto(?, sample_size=-1) WHERE trade_date=?',[str(ROOT/source),cutoff]) if r['source_security_key'] in keys]
            if cap=='PRICE_LIMIT':
                for r in rows:
                    previous=latestby.get(r['security_id'])
                    r.update(next_reference_close=str(previous['raw_close']) if previous else None,next_reference_blocked_by=None,
                        reference_state_basis='LAST_ACTUAL_ACCEPTED_CANONICAL_RAW_CLOSE',reference_state_source_date=iso(previous['trade_date']) if previous else None)
        elif cap.startswith('PERIOD_'):
            rows=[];basis='QFQ' if cap=='PERIOD_ADJUSTED' else 'RAW'
            for kind,source in [('WEEKLY',weekly),('MONTHLY',monthly)]:
                originalrows=query(c,'SELECT * FROM read_parquet(?) WHERE price_basis=? AND period_start_date=(SELECT max(period_start_date) FROM read_parquet(?))',[str(ROOT/source),basis,str(ROOT/source)])
                start=min(r['period_start_date'] for r in originalrows)
                firsts={r['canonical_security_id']:r['first'] for r in query(c,'SELECT canonical_security_id,min(trade_date) AS first FROM canonical WHERE trade_date between ? and ? GROUP BY canonical_security_id',[start,cutnum])}
                for r in originalrows:
                    if r['canonical_security_id'] not in sids:continue
                    first=firsts.get(r['canonical_security_id'])
                    row=dict(security_id=r['canonical_security_id'],source_security_key=r['source_security_key'],trade_date=cutoff,
                        as_of_date=cutoff,parent_daily_cutoff=cutoff,period_type=kind,period_key=period_key(r['period_start_date'],kind),
                        period_end_date=iso(r['period_end_date']),period_view=r['period_view'],price_basis=basis,
                        **{p:(str(r[p]) if r[p] is not None else None) for p in ('open','high','low','close')},
                        **{k:r[k] for k in ('volume','amount','actual_count','calendar_count','suspended_count','data_gap_count','unknown_count','period_status','source_daily_digest')},
                        first_source_date=iso(first),max_source_date=iso(r['max_source_trade_date']),
                        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False)
                    if r['period_status'].startswith('BLOCKED') and basis=='QFQ':row['unknown_reason']='ACCEPTED_PARENT_ADJUSTMENT_OR_STATUS_BLOCKED'
                    rows.append(row)
        else:
            # Exact dated phase projection from the accepted price truth, retaining original reason/state.
            rows=[{**r} for r in load(parents['PRICE_LIMIT'])['rows']]
        parents[cap]=save('parent_'+cap+'.json',dict(trade_date=cutoff,rows=rows,
            projection_scope='TARGET_STATE_PLUS_OPEN_PERIODS; CLOSED_HISTORY_RETAINED_BY_EXACT_ARCHIVE_BINDINGS',accepted_source_bindings=accepted_sources))
    pm=save('accepted_parent_components.json',dict(parent_data_head_digest=dataref['sha256'],components=parents,
        accepted_data_head=dataref,accepted_source_bindings=accepted_sources,
        projection='READ_ONLY_EXACT_ACCEPTED_ARTIFACT_PROJECTION_NOT_NEW_ACCEPTANCE'))
    parent=dict(kind='ACCEPTED_ANCHOR',head=datahead,binding=dataref,components=parents,component_manifest_binding=pm)
    go=bind('data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json');goh=load(go)
    gbmeta=load(goh['evidence_bindings']['gbbq_snapshot']);gbpath=str(Path(goh['evidence_bindings']['gbbq_snapshot']['path']).parent/'gbbq').replace('\\','/')
    gb=bind(gbpath);assert gb['sha256']==gbmeta['files']['gbbq']['sha256']
    classification=load(old['gbbq_classification_binding']);categories={k:v['formal_disposition'] for k,v in classification['dispositions'].items()}
    events=list(read_gbbq(ROOT/gbpath));eventmap={}
    for e in events:eventmap.setdefault(e.security_id.upper(),[]).append(e)
    # The old parent's last actual close is carried through intervening accepted actions.
    from workbench_analysis.price_reference_state import PreviousCloseState
    from workbench_analysis.v4_02_closure import ex_right_reference_price
    from adjustment.tdx_adjustment import xrxd_from_gbbq
    prices=load(parents['PRICE_LIMIT'])
    for r in prices['rows']:
        if not r['reference_state_source_date']:continue
        state=PreviousCloseState(Decimal(r['next_reference_close']))
        for day in sorted({e.event_date for e in eventmap.get(r['source_security_key'],[]) if int(r['reference_state_source_date'].replace('-',''))<e.event_date<=cutnum}):
            state.apply_actions([(categories.get(str(e.category),'UNKNOWN_PRICE_IMPACT'),xrxd_from_gbbq(e) if e.category==1 else None)
                for e in eventmap[r['source_security_key']] if e.event_date==day],lambda v,a:ex_right_reference_price(v,a,'0.01'))
        r.update(next_reference_close=str(state.value) if state.value is not None else None,next_reference_blocked_by=state.blocked_by)
    # Derived reference state is a new immutable projection, never overwrite the earlier exact price slice.
    parents['PRICE_LIMIT']=save('parent_PRICE_LIMIT_REFERENCE_STATE.json',prices)
    pm=save('accepted_parent_components_reference_state.json',dict(parent_data_head_digest=dataref['sha256'],components=parents,
        accepted_data_head=dataref,accepted_source_bindings=accepted_sources,projection='LAST_ACTUAL_CLOSE_PLUS_ACCEPTED_NATIVE_ACTIONS'))
    parent['component_manifest_binding']=pm
    inputs={};instanceindex=read('reports/audits/A10_A12_R3_SOURCE_INSTANCE_MANIFEST_R1.json')['instances']
    capture=read('reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json');currentreceipt=load(capture['capture_receipt'])
    assert capture['status']=='PASS'
    for target in completed:
        instance=instanceindex.get(target)
        if instance is None:instance=read(P+target.replace('-','')+'_SOURCE_CAPTURE_R1.json')['instances']
        raw=load(load(instance['TRADING_STATUS'])['raw_artifact']);eligible=active(records,target);roster={r['source_security_key'] for r in eligible}
        provider=load(instance['TRADING_STATUS'])
        bao=save(target+'/baostock_daily.json',dict(status='BAOSTOCK_DAILY_SNAPSHOT_READY',trade_date=target,provider_date=target,
            snapshot_id=provider['source_revision'],daily_rows=raw['rows'],raw_response_binding=provider['raw_artifact'],
            source_instances=instance,origin='DELAYED_HISTORICAL_RETRIEVAL',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
        prior_capture=ROOT/goh['evidence_bindings']['official_tdx_package']['path']
        if target==goh['first_accepted_target_trade_date']:
            pkg=goh['evidence_bindings']['official_tdx_package'];actual_receipt=bind((prior_capture.parent/'capture_receipt.json').relative_to(ROOT).as_posix());kind='EXTERNALLY_ACCEPTED_GO_FORWARD_PACKAGE'
        else:pkg=currentreceipt['package'];actual_receipt=capture['capture_receipt'];kind='CURRENT_OFFICIAL_ZIP_RECONSTRUCTED'
        bars=[];excluded=0;future=0;targetnum=int(target.replace('-',''))
        with zipfile.ZipFile(ROOT/pkg['path']) as z:
            for name in z.namelist():
                stem=Path(name).stem
                if not name.lower().endswith('.day') or len(stem)!=8:continue
                key=stem[:2].upper()+'.'+stem[2:]
                if key not in roster:excluded+=1;continue
                data=z.read(name)
                if len(data)%32:raise ValueError('TDX_DAY_RECORD_LENGTH_INVALID')
                hits=[]
                for offset in range(0,len(data),32):
                    row=struct.unpack('<IIIIIfII',data[offset:offset+32])
                    future+=int(row[0]>targetnum)
                    if row[0]==targetnum:hits.append(row)
                if len(hits)>1:raise ValueError('TDX_DUPLICATE_TARGET_ROW')
                if hits:
                    d,op,hi,lo,cl,amount,volume,_=hits[0]
                    bars.append(dict(security_id=key,source_security_key=key,trade_date=d,
                        open=op/100,high=hi/100,low=lo/100,close=cl/100,amount=amount,volume=volume))
        delta=save(target+'/tdx_target_delta.json',dict(contract_id='TDX_PACKAGE_DELTA_V1',status='READY',target_date=target,
            current_snapshot_id='sha256-'+pkg['sha256'],target_bars=sorted(bars,key=lambda r:r['source_security_key']),
            revision_events=[],future_rows_discarded=future,future_rows_consumed=0,out_of_scope_files_excluded=excluded))
        page=save(target+'/tdx_target_slice.json',dict(contract_id='DM01_TDX_TARGET_SLICE_V3',target_date=target,
            snapshot_id='sha256-'+pkg['sha256'],package_binding=pkg,actual_capture_receipt=actual_receipt,capture_kind=kind,
            delta_binding=delta,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,future_rows_consumed=0))
        disp=save(target+'/gbbq_dispositions.json',dict(gbbq_sha256=gb['sha256'],first_eligible_formal_trade_date=gbmeta['first_eligible_formal_trade_date'],
            category_dispositions=categories,rows=[dict(security_id=r['security_id'],blocking_categories=sorted({e.category
                for e in eventmap.get(r['source_security_key'],[]) if e.event_date<=targetnum and categories.get(str(e.category),'UNKNOWN_PRICE_IMPACT') in ('UNKNOWN_PRICE_IMPACT','PRICE_AFFECTING_UNSUPPORTED')})) for r in eligible]))
        lifecycle=save(target+'/lifecycle.json',dict(contract_id='CURRENT_LIFECYCLE_SNAPSHOT_V1',trade_date=target,
            active_security_ids=sorted(r['security_id'] for r in eligible),accepted_identity_projection=ir,source_instances=instance,
            membership_basis='ACCEPTED_DATED_IDENTITY_INTERVALS',absence_is_delisting_evidence=False))
        phase=save(target+'/special_phase.json',dict(contract_id='SPECIAL_PHASE_SOURCE_MANIFEST_V1',trade_date=target,status='READY',
            event_store=old['accepted_phase_bindings']['event_store'],policy=old['accepted_phase_bindings']['policy'],
            lifecycle_snapshot=lifecycle,active_security_ids=sorted(r['security_id'] for r in eligible)))
        factor=save(target+'/supplemental_factor_availability.json',dict(source_role='SUPPLEMENTAL_CROSSCHECK',
            status='NOT_REQUIRED_BY_FINAL_ALL_NINE',capability_blocked=False,canonical_qfq_authority=False,query_count=0))
        families=dict(TDX_PAGE_CAPTURE=page,TDX_FULL_PACKAGE=pkg,TDX_PACKAGE_DELTA=delta,OFFICIAL_CALENDAR=cr,
            BAOSTOCK_DAILY_UPDATE=bao,BAOSTOCK_ADJUSTMENT_FACTOR=factor,GBBQ=gb,IDENTITY_LIFECYCLE=lifecycle,SPECIAL_PRICE_PHASE=phase)
        families={k:dict(v,bytes=(ROOT/v['path']).stat().st_size,source_revision='sha256-'+v['sha256'] if k=='TDX_FULL_PACKAGE' else 'sha256:'+v['sha256']) for k,v in families.items()}
        inputs[target]=dict(families=families,inputs=dict(TDX_PACKAGE_DELTA=delta,BAOSTOCK_DAILY_UPDATE=bao,GBBQ=gb,
            GBBQ_DISPOSITIONS=disp,SPECIAL_PRICE_PHASE=phase,PRICE_RULES=old['accepted_phase_bindings']['rules']),instances=instance)
    context=save('chain_execution_context.json',dict(parent=parent,calendar=calendar,identity=identity,sessions=completed,inputs=inputs,observed_at=now))
    contract=deepcopy(old)
    contract.update(contract_id='DM01_A01_INCREMENTAL_BUILDERS_R3',version='3.0.0',status='CANDIDATE_CONTINUOUS_RECONSTRUCTED_ONLY',
        supersedes=bind('config/dm01_incremental_builders_contract_r1.json'),accepted_data_head=dataref,accepted_historical_calendar=histref,
        accepted_identity_head=ih,accepted_go_forward_head=go,bootstrap_parent_manifest=pm,
        producer_governance=bind('config/source_authority_governance_r4.json'),execution_context=context,
        candidate_parent_protocol='EXACT_ALL_NINE_READY_MARKER_CHAIN_TO_FIXED_ACCEPTED_ANCHOR',
        tdx_historical_retrieval='OFFICIAL_ZIP_EXACT_TARGET_SLICE; EXCLUDE_FUTURE_BARS; NO_BACKDATED_AVAILABILITY',
        AS_RECORDED=False,external_acceptance=None,source_factor_policy='SUPPLEMENTAL_OPTIONAL_WITH_EXPLICIT_AVAILABILITY_RECEIPT',
        next_stage='INDEPENDENT_EXTERNAL_REAUDIT_NO_DATA_HEAD_PROMOTION')
    newpaths=('src/workbench_analysis/dm01_chain_contract_r3.py','src/workbench_analysis/dm01_incremental_component_builders_r3.py',
        'src/workbench_analysis/dm01_candidate_orchestrator_r3.py','src/workbench_analysis/dm01_independent_postcheck_r3.py',
        'src/workbench_analysis/source_authority_producers_r4.py','scripts/run_dm01_a01_r3_chain.py')
    contract['runtime_bindings']=[r for r in old['runtime_bindings'] if not r['path'].startswith(('src/workbench_analysis/dm01_incremental_component_builders.py',
        'src/workbench_analysis/dm01_candidate_orchestrator_r1.py','src/workbench_analysis/dm01_independent_postcheck_r1.py','scripts/run_dm01_a01_next_session_r1.py'))]+[bind(p) for p in newpaths]
    for cap in contract['capabilities'].values():
        cap['runtime_bindings']=[r for r in cap['runtime_bindings'] if r['path']!='src/workbench_analysis/dm01_incremental_component_builders.py']+[bind(newpaths[1])]
    _write_immutable(ROOT/CONTRACT_PATH,contract)
    print(json.dumps(dict(prepared=True,sessions=completed,parent_members=len(activeparent),input_context=context)))

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
        chain_postcheck=bind(P+'CONTINUOUS_CHAIN_POSTCHECK_R1.json'),determinism=bind(P+'DETERMINISM_R1.json'),
        atomicity=bind(P+'ATOMIC_FAILURE_PROBES_R1.json'),contract=bind(CONTRACT_PATH),source_context=contract['execution_context'],
        clean_regression='PENDING_CLEAN_DETACHED',external_acceptance='PENDING',data_head_moved=False,
        permitted_next_stage='INDEPENDENT_EXTERNAL_REAUDIT_ONLY'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    if args.prepare:prepare()
    else:execute()
