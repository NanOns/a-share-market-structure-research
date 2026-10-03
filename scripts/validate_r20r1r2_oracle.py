"""Independent production-shape lineage and Decimal projection/settlement oracle."""
import json,subprocess,sys
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP,localcontext
from datetime import datetime
from functools import lru_cache
from scripts.r20r1r2_io import ROOT,BASE,ref,exact,require,digest
sys.path.insert(0,str(ROOT/'src'))
from tdx.gbbq_reader import read_gbbq
REQUIRED=[1,3,5,10,20]
DENIED='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'

@lru_cache(maxsize=8)
def decoded(path,sha):return tuple(read_gbbq(Path(path)))

def packet_oracle(packet,root):
    root=Path(root);reg=json.loads((root/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes())
    h14=exact(reg['accepted_head'],root);seal=exact(h14['bindings']['runtime_seal'],root)
    require(all(h14['bindings']['data_head'][k]==reg['T0_data_archive'][k] for k in ['sha256','bytes']),'ORACLE_EXACT_T0_DATA_ARCHIVE')
    require(packet['accepted_head']==reg['accepted_head']==ref('data/v4/V4_14_ACCEPTED_HEAD.json',root) and packet['owner_publication']==reg['owner_publication'] and packet['owner_publication'] in seal['replay_publications'],'ORACLE_REAL_SEALED_T0')
    owner=exact(packet['owner_publication'],root);en=exact(packet['enrollment'],root);freeze=exact(packet['freeze'],root);prod=exact(reg['producer_receipt'],root)
    require(packet['enrollment']==reg['enrollment'] and packet['freeze']==reg['freeze'] and owner['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' and en['source_publication']==packet['owner_publication'] and freeze['enrollment']==packet['enrollment'],'ORACLE_EXACT_T0_LINEAGE')
    require(en['cohort_namespace']=='RECONSTRUCTED_ASOF' and owner['trade_date']==en['T0']==freeze['T0']==reg['T0'],'ORACLE_RECONSTRUCTED_SCOPE')
    log=exact(packet['endpoint_read_receipt'],root)
    require(packet['freeze_completed_at']==prod['end'] and packet['freeze'] in prod['real_freezes'] and prod['real_enrollment']==packet['enrollment'] and log['freeze']==packet['freeze'] and log['projection']==packet['projection'] and log['accepted_endpoints']==packet['accepted_endpoints'] and log['first_future_endpoint_open_at']==packet['first_future_endpoint_open_at'],'ORACLE_PERSISTED_READ_ORDER_BINDINGS')
    require(datetime.fromisoformat(prod['end'])<datetime.fromisoformat(log['first_future_endpoint_open_at']) and log['raw_provider_fallback'] is False and packet['raw_provider_fallback'] is False and packet['historical_prices_only'] is False,'ORACLE_NO_EARLY_OR_PROVIDER_READ')
    require(packet['HISTORICAL_PIT_EFFECTIVENESS']==packet['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED','ORACLE_NO_PIT_REALTIME_UPGRADE')
    # Independently traverse Data batches, then their accepted daily candidates.
    heads=[];b=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json',root);seen=set()
    while True:
        require(b['sha256'] not in seen,'ORACLE_HEAD_CYCLE');seen.add(b['sha256']);h=exact(b,root)
        require(h['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and h['version']=='2.0.0' and set(h)==set(exact(h['contract'],root)['required_fields']),'ORACLE_REAL_HEAD_SHAPE');heads.append((b,h))
        if b['sha256']==reg['T0_data_archive']['sha256']:break
        require(h['parent_head_sha256']==h['parent_archive']['sha256'] and exact(h['parent_archive'],root)['accepted_trade_date']<h['accepted_trade_date'],'ORACLE_BATCH_PARENT')
        b=h['parent_archive']
    heads.reverse();index=[i for i,(b,h) in enumerate(heads) if (b['sha256'],b['bytes'])==(packet['data_head']['sha256'],packet['data_head']['bytes'])]
    if not index:
        admitted=[]
        for hb,h in heads[1:]:
            record=exact(h['external_acceptance_record'],root)
            for binding in record['evidence_bindings']:
                if isinstance(binding,dict) and (binding.get('sha256'),binding.get('bytes'))==(packet['data_head']['sha256'],packet['data_head']['bytes']):admitted.append(h['accepted_trade_date'])
        require(len(admitted)==1,'ORACLE_SELECTED_ACCEPTED_SNAPSHOT');prior=exact(packet['data_head'],root);require(prior['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and prior['accepted_trade_date']==admitted[0],'ORACLE_PRIOR_ACCEPTED_SAME_CUTOFF')
        heads=[];b=packet['data_head'];seen=set()
        while True:
            require(b['sha256'] not in seen,'ORACLE_ARCHIVED_REVISION_CYCLE');seen.add(b['sha256']);h=exact(b,root);require(h['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and h['version']=='2.0.0' and set(h)==set(exact(h['contract'],root)['required_fields']),'ORACLE_ARCHIVED_SCHEMA');heads.append((b,h))
            if b['sha256']==reg['T0_data_archive']['sha256']:break
            require(h['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and h['parent_head_sha256']==h['parent_archive']['sha256'] and exact(h['parent_archive'],root)['accepted_trade_date']<h['accepted_trade_date'],'ORACLE_ARCHIVED_REVISION_PARENT');b=h['parent_archive']
        heads.reverse()
    else:
        require(len(index)==1,'ORACLE_SELECTED_ACCEPTED_SNAPSHOT');heads=heads[:index[0]+1];heads[-1]=(packet['data_head'],heads[-1][1]);exact(packet['data_head'],root)
    base=heads[0][1];ss=exact(heads[-1][1]['calendar'],root)['session_dates'];past=exact(base['calendar'],root)['session_dates']
    require(ss==sorted(set(ss)) and ss[:len(past)]==past,'ORACLE_ACCEPTED_CALENDAR_PREFIX')
    n=packet['horizon'];require(type(n) is int and n in REQUIRED,'ORACLE_HORIZON');i=ss.index(freeze['T0']);days=ss[i+1:i+n+1]
    require(len(days)==n and days[-1]<=heads[-1][1]['accepted_trade_date'],'ORACLE_MATURED_DUE_CUTOFF')
    resolved=[];previous_date=freeze['T0'];parent_head=heads[0][0];previous_components=base['component_artifacts']
    for hb,h in heads[1:]:
        require('FORWARD_EVALUATION_INPUTS' not in h['component_artifacts'],'ORACLE_NO_INVENTED_HEAD_LIST')
        chain=exact(h['accepted_chain'],root);record=exact(h['external_acceptance_record'],root)
        require(chain['contract_id']=='DM01_ACCEPTED_CONTINUOUS_CHAIN_V1' and chain['anchor']['archive']==parent_head==h['parent_archive'] and chain['external_acceptance_record']==h['external_acceptance_record'] and chain['accepted_through']==record['accepted_through']==h['accepted_trade_date'],'ORACLE_EXACT_CHAIN_AUTHORITY')
        require(record['candidate_bindings']==[x['candidate'] for x in chain['nodes']] and h['final_candidate']==chain['nodes'][-1]['candidate'] and h['external_acceptance']==record['external_acceptance']=='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN','ORACLE_ACCEPTED_MEMBERSHIP')
        require(record['accepted_scope']['sessions']==[x['trade_date'] for x in chain['nodes']] and record['external_authority']==chain['external_authority'] and record['audited_head']==chain['external_authority']['audited_head'],'ORACLE_ACCEPTANCE_SCOPE_AUTHORITY');exact(chain['external_authority']['document'],root)
        require(not any(h['permissions'].values()) and not any(chain[k] for k in ['production','shadow','focus']),'ORACLE_PROTECTED_PERMISSIONS')
        if root.resolve()==ROOT.resolve():require(not chain.get('fixture_scope') and not record.get('fixture_scope') and chain['external_authority']['authority_kind']=='INDEPENDENT_EXTERNAL_ACCEPTANCE','ORACLE_NO_ENGINEERING_REAL_UPGRADE')
        ctx=exact(chain['source_context'],root);require(ctx['calendar']['binding']==h['calendar'] and exact(chain['builder_contract'],root)['execution_context']==chain['source_context'],'ORACLE_CONTEXT_CALENDAR');parent=parent_head;components=previous_components
        for node in chain['nodes']:
            day=node['trade_date'];require(next((d for d in ss if d>previous_date),None)==day and node['parent']==parent,'ORACLE_SESSION_PARENT_GAP')
            c=exact(node['candidate'],root);pc=exact(c['parent_context_binding'],root);manifest=exact(pc['component_manifest_binding'],root)
            require(c['contract_id']=='DM01_ATOMIC_CONTINUOUS_CANDIDATE_R3_3' and c['components']==node['components'] and c['target_trade_date']==day and c['parent_data_head_digest']==parent['sha256'] and pc['binding']==parent and pc['components']==manifest['components']==components and manifest['parent_data_head_digest']==parent['sha256'],'ORACLE_CANDIDATE_PARENT_COMPONENTS')
            rr=node['components']['ADJUSTED_DAILY'];rb=ref((Path(rr['artifact_path']).parent/'receipt.json').as_posix(),root);ab=dict(path=rr['artifact_path'],sha256=rr['artifact_sha256'],bytes=rr['artifact_bytes']);a=exact(ab,root)
            require(exact(rb,root)==rr and rr['component_id']=='ADJUSTED_DAILY' and rr['contract_id']=='DM01_ADJUSTED_DAILY_INCREMENT_R3_3' and rr['trade_date']==rr['target_trade_date']==a['trade_date']==day and rr['parent_component_bindings']==components and rr['parent_data_head_digest']==parent['sha256'],'ORACLE_ACCEPTED_DAILY_RECEIPT')
            require(rr['source_revision']==c['source_freeze_digest'],'ORACLE_COMPONENT_FREEZE_REVISION')
            require(a['contract_id']=='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3' and digest(a['rows'])==rr['logical_digest'] and len(a['rows'])==rr['row_count'] and rr['status'] in ['FULL_PASS','DEGRADED_PASS'],'ORACLE_NATIVE_CONTENT')
            resolved.append(dict(trade_date=day,artifact=ab,receipt=rb,source_data_head=hb,accepted_chain=h['accepted_chain'],candidate=node['candidate'],source_context=chain['source_context']))
            components={k:dict(path=r['artifact_path'],sha256=r['artifact_sha256'],bytes=r['artifact_bytes']) for k,r in node['components'].items()};parent=node['candidate'];previous_date=day
        require(components==h['component_artifacts'] and h['component_permissions']['ADJUSTED_DAILY']['artifact']==components['ADJUSTED_DAILY'] and exact(h['component_permissions']['ADJUSTED_DAILY']['receipt'],root)==rr,'ORACLE_FINAL_COMPONENT_ONLY')
        require(h['canonical_data_revision']==c['logical_digest'] and h['source_revision']==c['source_freeze_digest'],'ORACLE_HEAD_REVISION_BINDINGS')
        parent_head=hb;previous_components=components
    items=[x for x in resolved if x['trade_date'] in days];require([x['trade_date'] for x in items]==days,'ORACLE_COMPLETE_ACCEPTED_PATH')
    require(packet['accepted_endpoints']==[x['artifact'] for x in items],'ORACLE_EXACT_RESOLVED_ENDPOINTS')
    projection=exact(packet['projection'],root)
    require(projection['contract_id']=='V4_15_ACCEPTED_FORWARD_EVALUATION_PROJECTION_V1' and projection['contract']==ref('config/v4_15_forward_projection_r20r1r2_v1.json',root) and projection['freeze']==packet['freeze'] and projection['evaluation_basis_date']==days[-1],'ORACLE_PROJECTION_RECEIPT_REQUIRED')
    def native(ab,day):
        rows=[r for r in exact(ab,root)['rows'] if r['security_id']==freeze['signal_id'] and r['trade_date']==day]
        require(len(rows)==1,'ORACLE_IDENTITY_AMBIGUITY');r=rows[0]
        require(not set(['evaluation_basis_date','verified_identity','verified_adjustment','T0_basis_verified','transform_coefficients','T0_transform_coefficients']).intersection(r),'ORACLE_NATIVE_SCHEMA_BOUNDARY')
        require(r['price_basis']=='TDX_NATIVE_AFFINE_QFQ' and r['adjustment_readiness']=='READY' and not r.get('unknown_reason') and Decimal(r['qfq_mul'])==1 and Decimal(r['qfq_add'])==0,'ORACLE_NATIVE_ADJUSTMENT_READY')
        require(r['source_authority']=='TDX_OFFICIAL_PACKAGE' and r['bao_stock_ohlc_substitution_permitted'] is False and r['record_quality']=='SOURCE_FILE_VALIDATED_RECORD' and r['identity_quality']=='R6_2_DATED_ROSTER_OBSERVED','ORACLE_NATIVE_TDX_IDENTITY')
        require(all(Decimal(r[k]).is_finite() and Decimal(r[k])>0 for k in ['open','high','low','close']),'ORACLE_NATIVE_PRICES');return r
    t0=native(base['component_artifacts']['ADJUSTED_DAILY'],freeze['T0']);require(Decimal(t0['close'])==Decimal(str(freeze['comparison_reference'])),'ORACLE_T0_REFERENCE_EQUALITY')
    inputs=exact(items[-1]['source_context'],root)['inputs'][days[-1]]['inputs'];gb=inputs['GBBQ'];exact(gb,root);dis=exact(inputs['GBBQ_DISPOSITIONS'],root);bc=json.loads((root/'config/dm01_incremental_builders_contract_r3_3.json').read_bytes());rules=exact(bc['gbbq_classification_binding'],root)
    require(projection['accepted_adjustment_source']==gb and projection['accepted_adjustment_disposition']==inputs['GBBQ_DISPOSITIONS'] and dis['gbbq_sha256']==gb['sha256'] and dis['first_eligible_formal_trade_date']<=days[-1] and dis['category_dispositions']=={k:v['formal_disposition'] for k,v in rules['dispositions'].items()},'ORACLE_ACCEPTED_GBBQ_BINDINGS')
    dispositions=[r for r in dis['rows'] if r['security_id']==freeze['signal_id']];require(len(dispositions)==1 and not dispositions[0].get('blocking_categories'),'ORACLE_UNSUPPORTED_ACTION')
    ev=[e for e in decoded(str((root/gb['path']).resolve()),gb['sha256']) if e.security_id.upper()==t0['source_security_key'].upper() and e.event_date<=int(days[-1].replace('-',''))]
    require(not any(rules['dispositions'].get(str(e.category),dict(formal_disposition='UNKNOWN_PRICE_IMPACT'))['formal_disposition'] in ['UNKNOWN_PRICE_IMPACT','PRICE_AFFECTING_UNSUPPORTED'] for e in ev),'ORACLE_UNSUPPORTED_CORPORATE_ACTION')
    # Independent affine composition, without calling the projection or affine evaluator.
    coeff={};a=Decimal(1);b=Decimal(0);effective=sorted((e for e in ev if e.category==1),key=lambda e:(e.event_date,e.source_record_index));j=len(effective)-1
    with localcontext() as dc:
        dc.prec=40
        for day in reversed([freeze['T0']]+days):
            while j>=0 and effective[j].event_date>int(day.replace('-','')):
                e=effective[j];q=lambda x:Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP);cash,rights,bonus,ratio=map(q,[e.c1,e.c2,e.c3,e.c4]);m=(Decimal(10)+bonus+ratio)/10;c=(cash-ratio*rights)/10;require(m>0,'ORACLE_VALID_XRXD');a=a/m;b=b-a*c;j-=1
            coeff[day]=dict(alpha=float(a),beta=float(b))
    expected_rows=[]
    for item in items:
        r=native(item['artifact'],item['trade_date']);rr=exact(item['receipt'],root);src=exact(item['source_context'],root)['inputs'][item['trade_date']]['inputs']
        require(all(src[k]['sha256'] in rr['input_publication_ids'] for k in ['GBBQ','GBBQ_DISPOSITIONS','TDX_PACKAGE_DELTA']) and r['identity_source_revision'] in rr['input_publication_ids'],'ORACLE_ACCEPTED_RECEIPT_SOURCE_INPUTS')
        marker=exact(item['candidate'],root);raw_receipt=marker['components']['RAW_DAILY'];raw_binding=dict(path=raw_receipt['artifact_path'],sha256=raw_receipt['artifact_sha256'],bytes=raw_receipt['artifact_bytes']);raw=exact(raw_binding,root);adjusted=exact(item['artifact'],root)
        require(adjusted['raw_daily_artifact_sha256']==raw_binding['sha256'] and r['raw_daily_digest']==raw_receipt['logical_digest'] and raw['contract_id']=='DM01_RAW_DAILY_ARTIFACT_R3_3' and raw['trade_date']==r['trade_date'] and digest(raw['rows'])==raw_receipt['logical_digest'],'ORACLE_ACCEPTED_RAW_ADJUSTED_LINK')
        delta=exact(src['TDX_PACKAGE_DELTA'],root);bars=[b for b in delta['target_bars'] if b['source_security_key']==r['source_security_key'] and str(b['trade_date'])==r['trade_date'].replace('-','')]
        require(r['source_digest']==src['TDX_PACKAGE_DELTA']['sha256'] and delta['contract_id']=='TDX_PACKAGE_DELTA_V1' and delta['target_date']==r['trade_date'] and delta['future_rows_consumed']==0 and delta['current_snapshot_id']==r['source_snapshot_id'] and len(bars)==1 and all(abs(Decimal(str(bars[0][k]))-Decimal(r[k]))<Decimal('1e-10') for k in ['open','high','low','close']),'ORACLE_NATIVE_TDX_BAR')
        require(r['source_security_key']==t0['source_security_key'] and r['identity_source_revision']==rr['identity_publication_id'] and r['adjustment_source_revision']==src['GBBQ']['sha256'],'ORACLE_NATIVE_SOURCE_REVISIONS')
        expected_rows.append(dict(source_data_head=item['source_data_head'],source_adjusted_daily_artifact=item['artifact'],source_component_receipt=item['receipt'],source_row_identity=dict(security_id=r['security_id'],source_security_key=r['source_security_key'],trade_date=r['trade_date']),source_row_digest=digest(r),security_id=r['security_id'],trade_date=r['trade_date'],evaluation_basis_date=days[-1],verified_identity=True,verified_adjustment=True,T0_basis_verified=True,transform_coefficients=coeff[r['trade_date']],T0_transform_coefficients=coeff[freeze['T0']],source_authority=r['source_authority'],status='ACTUAL',**{k:r[k] for k in ['open','high','low','close']}))
    require(projection['rows']==expected_rows and projection['T0_source_row_digest']==digest(t0) and projection['T0_transform_coefficients']==coeff[freeze['T0']],'ORACLE_INDEPENDENT_PROJECTION_AND_T0_MATH')
    outcome=exact(packet['outcome'],root);require(outcome['projection']==packet['projection'] and outcome['price_path']==expected_rows and outcome['frozen_t0']==packet['freeze'] and outcome['enrollment_id']==en['enrollment_id'] and outcome['horizon']==n and outcome['due_date']==days[-1] and outcome['outcome_status']=='OBSERVED' and outcome['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','ORACLE_OBSERVED_OUTCOME')
    require(all(x['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' for x in [projection,outcome,en,freeze]) and projection['raw_provider_fallback'] is False,'ORACLE_NO_PIT_UPGRADE')
    d=lambda x:Decimal(str(x));t=coeff[freeze['T0']];p0=d(t['alpha'])*d(freeze['comparison_reference'])+d(t['beta']);require(p0>0,'ORACLE_POSITIVE_T0');value=lambda r,k:d(r['transform_coefficients']['alpha'])*d(r[k])+d(r['transform_coefficients']['beta']);peak=p0;mdd=Decimal(0)
    for r in expected_rows:c=value(r,'close');peak=max(peak,c);mdd=min(mdd,c/peak-1)
    expected=dict(R_N=value(expected_rows[-1],'close')/p0-1,MFE_N=max([p0]+[value(r,'high') for r in expected_rows])/p0-1,MAE_N=min([p0]+[value(r,'low') for r in expected_rows])/p0-1,PATH_MDD_CLOSE_N=mdd)
    require(all(not isinstance(outcome[k],bool) and d(outcome[k]).is_finite() and abs(d(outcome[k])-v)<Decimal('1e-10') for k,v in expected.items()),'ORACLE_INDEPENDENT_SETTLEMENT_MATH')
    return n

def state_oracle(root,view=None):
    root=Path(root);view=view if view is not None else json.loads((root/'reports/r20r1r2/MATURITY_DEBT_READBACK.json').read_bytes());coverage=set()
    require({k:v for k,v in view.items() if k not in ['FIRST_OBSERVED','LATEST_VALIDATED']}==exact(view['LATEST_VALIDATED'],root),'ORACLE_IMMUTABLE_READBACK_REVISION')
    for key,entry in view['proofs_by_enrollment_horizon'].items():
        require(entry['FIRST_OBSERVED']==entry['receipt_history'][0] and entry['LATEST_VALIDATED']==entry['receipt_history'][-1],'ORACLE_APPEND_ONLY_FIRST_LATEST');previous=None
        for binding in entry['receipt_history']:
            proof=exact(binding,root);n=packet_oracle(proof['packet'],root);coverage.add(n);en=exact(proof['packet']['enrollment'],root);outcome=exact(proof['packet']['outcome'],root)
            require(proof['horizon']==n and proof['enrollment_id']==en['enrollment_id'] and proof['due_date']==outcome['due_date'] and key==digest([proof['enrollment_id'],n,proof['due_date']]) and all(entry[k]==proof[k] for k in ['enrollment_id','horizon','due_date']),'ORACLE_BOUND_HORIZON_COVERAGE')
            if previous:
                old=exact(previous['packet']['outcome'],root);require(outcome['revision_sequence']==old['revision_sequence']+1 and outcome['supersedes']==previous['packet']['outcome'] and proof['packet']['accepted_endpoints']!=previous['packet']['accepted_endpoints'],'ORACLE_NEXT_CORRECTION_REVISION')
            previous=proof
    proved=sorted(coverage);unproved=[n for n in REQUIRED if n not in proved];state='OPEN' if not proved else 'PARTIAL_MATURITY_EVIDENCE' if unproved else 'FULL_REQUIRED_HORIZONS_PROVEN';blocked=bool(unproved) or root.resolve()!=ROOT.resolve()
    require(view['required_horizons']==REQUIRED and view['proved_horizons']==proved and view['unproved_horizons']==unproved and view['aggregate_state']==view['status']==state,'ORACLE_HORIZON_STATE_PASS_KEEP')
    require(view['capability_by_horizon']=={str(n):'PASS_CAPABILITY_SCOPED' if n in proved else DENIED for n in REQUIRED} and view['blocks_matured_real_claims'] is blocked and view['blocks_unqualified_matured_real_claims'] is blocked and view['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']==(DENIED if blocked else 'PASS_CAPABILITY_SCOPED'),'ORACLE_UNQUALIFIED_CLAIMS_BLOCKED')
    require(view['HISTORICAL_PIT_EFFECTIVENESS']==view['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED' and view['T0_OBSERVATION_SCOPE']=='RECONSTRUCTED_ASOF' and view['stage_promotion_authorized'] is False and view['blocks_unrelated_development'] is False,'ORACLE_PROTECTED_SCOPE')
    return dict(status='PASS',aggregate_state=state,proved_horizons=proved,unproved_horizons=unproved)

def validate():
    current=state_oracle(ROOT);require(current['proved_horizons']==[],'CURRENT_REAL_MATURITY_NONE')
    transitions=[]
    for step in json.loads((ROOT/'reports/r20r1r2/PRODUCTION_SHAPED_REACHABILITY.json').read_bytes())['transitions']:
        directory=(ROOT/step['fixture_directory']).resolve();require(directory.is_relative_to(ROOT/'reports/r20r1r2/engineering_fixtures'),'ISOLATED_FIXTURE_ONLY');result=state_oracle(directory,exact(step['readback'],ROOT));require(result['proved_horizons']==step['proved_horizons'],'ORACLE_PRODUCTION_TRANSITIONS');transitions.append(result)
    require([x['aggregate_state'] for x in transitions]==['OPEN','PARTIAL_MATURITY_EVIDENCE','PARTIAL_MATURITY_EVIDENCE','FULL_REQUIRED_HORIZONS_PROVEN'],'ALL_PRODUCTION_COVERAGE_STATES')
    correction=json.loads((ROOT/'reports/r20r1r2/PRODUCTION_CORRECTION_REACHABILITY.json').read_bytes());directory=(ROOT/correction['fixture_directory']).resolve();require(directory.is_relative_to(ROOT/'reports/r20r1r2/engineering_fixtures'),'ISOLATED_CORRECTION_ONLY');view=exact(correction['readback']);cr=state_oracle(directory,view)
    require(cr['proved_horizons']==[1] and view['FIRST_OBSERVED']==correction['original_first_observed'] and len(next(iter(view['proofs_by_enrollment_horizon'].values()))['receipt_history'])==2,'PRODUCTION_CORRECTION_FIRST_LATEST_PASS_KEEP')
    for binding in json.loads((ROOT/'reports/r20r1r2/FROZEN_BASELINE_BINDINGS.json').read_bytes())['bindings']:exact(binding)
    require(subprocess.check_output(['git','diff',BASE,'--name-only','--','src','data','reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/r20r1','reports/r20r1r1','reports/v4_15_runtime_r20'],cwd=ROOT)==b'','PRIOR_ALGORITHMS_AND_EVIDENCE_PASS_KEEP')
    require(json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())['accepted_trade_date']=='2026-09-30' and json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())['accepted_stage_range']=='V4_00_TO_V4_14_ACCEPTED' and not (ROOT/'data/v4/V4_15_ACCEPTED_HEAD.json').exists(),'PROTECTED_STAGE_DATA')
    return dict(R20R1R2_REAL_DM01_DATA_HEAD_REACHABILITY='PASS_LOCAL',R20R1R2_REAL_DM01_ROW_SCHEMA_ADMISSION='PASS_LOCAL',R20R1R2_INDEPENDENT_ORACLE='PASS_LOCAL',PRODUCTION_SHAPED_POSITIVE_PATH='PASS',HORIZON_SCOPED_DEBT='PASS_KEEP',CURRENT_REAL_MATURITY_EVIDENCE='NONE',PROVED_HORIZONS=[],UNPROVED_HORIZONS=REQUIRED,REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME=DENIED,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED',transitions=transitions,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':print(json.dumps(validate(),indent=2))
