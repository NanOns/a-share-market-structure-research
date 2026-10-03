"""Independent disk oracle: does not import Radar/Cohort producer/evaluator."""
import gzip,hashlib,json
from pathlib import Path
from scripts.r20_io import ROOT,atomic
def key(row,keys):return hashlib.sha256(json.dumps([row[k] for k in keys],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def exact(root,binding):
    raw=(root/binding['path']).read_bytes()
    if len(raw)!=binding.get('bytes',binding.get('byte_count')) or hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('ORACLE_EXACT_BYTES')
    return raw
def check(root=ROOT,receipt_path='reports/r20c/RADAR_COHORT_PERSISTED_RUN.json'):
    receipt=json.loads((root/receipt_path).read_bytes());registry=json.loads((root/'config/v4_15_cohort_revision_policy_v1.json').read_bytes())
    expected_enrollments=set();realcounts={};publication_counts=[]
    for binding in receipt['publications']:
        output=json.loads(exact(root,binding));source=json.loads(exact(root,output['source_publication']))
        if output['authority']['current_v4_14']['path']!='data/v4/V4_14_ACCEPTED_HEAD.json':raise ValueError('ORACLE_CURRENT_STAGE')
        if 'output' in source:
            rows=source['output']['d2']['rows'];events=source['output'].get('events',[]);pid=source['replay_publication_id'];date=source['target_trade_date'];evidence=source['evidence_class']
        else:
            rows=json.loads(gzip.decompress(exact(root,source['current_owner_publication'])))['rows'];events=json.loads(gzip.decompress(exact(root,source['event_source'])));pid='V4_14:'+output['source_publication']['sha256'];date=source['trade_date'];evidence=source['evidence_class']
        ledger={};event_ids=set()
        for row in rows:
            if row['entity_type']=='STOCK' and row.get('maturity')=='WARM':continue
            types=set()
            for e in events:
                if e['entity_id']==row['entity_id'] and e['entity_type']==row['entity_type']:
                    for typ in e.get('event_types',[e.get('event_type','NONE')]):
                        mapped={'CONFIRMATION_INVALIDATED':'INVALIDATION'}.get(typ,typ)
                        if mapped in {'FIRST_PREWATCH','REENTRY_PREWATCH','UPGRADE_TO_WARM','NEW_CONFIRMED','REACCELERATION_EVENT','INVALIDATION'}:types.add(mapped)
            if 'ENROLLED' in row.get('transition_reasons',[]) and row.get('maturity')=='PREWATCH':types.add('REENTRY_PREWATCH' if row.get('parent_episode_id') else 'FIRST_PREWATCH')
            if row.get('final_eligibility')=='TRUE' or types:
                l=dict(model_contract_id=row.get('model_contract_id','RESEARCH_STATE_V1'),state_lineage_id=row.get('state_lineage_id',row.get('model_namespace',evidence)),publication_id=pid,entity_type=row['entity_type'],entity_id=row['entity_id'],signal_type=row.get('maturity','UNKNOWN'))
                ledger[key(l,registry['daily_ledger_key'])]=l
            for typ in types:
                if typ=='UPGRADE_TO_WARM' and row['entity_type']=='STOCK':continue
                e=dict(model_contract_id=row.get('model_contract_id','RESEARCH_STATE_V1'),state_lineage_id=row.get('state_lineage_id',row.get('model_namespace',evidence)),entity_type=row['entity_type'],entity_id=row['entity_id'],episode_id=row['episode_id'],event_type=typ,event_trade_date=date)
                eid=key(e,registry['logical_event_key']);event_ids.add(eid)
                if row.get('final_eligibility')=='TRUE' and typ!='INVALIDATION':expected_enrollments.add(key(dict(logical_event_id=eid,cohort_namespace='ENGINEERING_SYNTHETIC' if evidence=='ENGINEERING_SYNTHETIC' else 'RECONSTRUCTED_ASOF'),['logical_event_id','cohort_namespace']))
        actualledger=[json.loads(exact(root,r)) for r in output['daily_ledger']]
        if {r['ledger_id'] for r in actualledger}!=set(ledger):raise ValueError('ORACLE_COMPLETE_LEDGER')
        if {json.loads(exact(root,r))['logical_event_id'] for r in output['logical_events']}!=event_ids:raise ValueError('ORACLE_LOGICAL_EVENTS')
        for r in actualledger:
            if key(r,registry['daily_ledger_key'])!=r['ledger_id'] or r['display_rank'] is not None or r['focus_activation_state'] is not None:raise ValueError('ORACLE_LEDGER_IDENTITY_OR_FOCUS')
        for ref in output['observations']:
            obs=json.loads(exact(root,ref))
            if key(obs,registry['observation_key'])!=obs['observation_id']:raise ValueError('ORACLE_OBSERVATION_IDENTITY')
        publication_counts.append(dict(trade_date=date,ledger=len(ledger),logical_events=len(event_ids),evidence_class=evidence))
        if evidence=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED':realcounts=dict(owner_rows=len(rows),ledger=len(ledger),logical_events=len(event_ids),namespace='RECONSTRUCTED_ASOF')
    enrollments=[json.loads(exact(root,r)) for r in receipt['persisted_enrollments']]
    if {r['enrollment_id'] for r in enrollments}!=expected_enrollments:raise ValueError('ORACLE_COMPLETE_ENROLLMENT')
    for r in enrollments:
        if key(r,['logical_event_id','cohort_namespace'])!=r['enrollment_id'] or r['HISTORICAL_PIT_EFFECTIVENESS']!='NOT_GRANTED' or r['settlement_continues'] is not True:raise ValueError('ORACLE_T0_IDENTITY')
        if r.get('parameter_identity_quality')=='KNOWN':
            exact(root,r['parameter_source'])
            if r['parameter_digest']!=r['parameter_source']['sha256']:raise ValueError('ORACLE_PARAMETER_DIGEST')
        elif r['parameter_digest'] is not None:raise ValueError('ORACLE_UNKNOWN_PARAMETER_NULL')
        if r['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' and r['comparison_reference'] is not None:
            data=json.loads((root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes());price_ref=data['component_artifacts']['ADJUSTED_DAILY']
            if r['comparison_reference_source']!=price_ref:raise ValueError('ORACLE_T0_PRICE_AUTHORITY')
            prices=json.loads(exact(root,price_ref));matches=[q for q in prices['rows'] if q['security_id']==r['entity_id'] and q['trade_date']==r['T0']]
            if len(matches)!=1 or float(matches[0]['close'])!=r['comparison_reference'] or matches[0]['adjustment_source_revision']!=r['adjustment_identity']:raise ValueError('ORACLE_T0_PRICE')
    return dict(R20C_V4_15_RADAR_COHORT_RUNTIME='PASS_LOCAL',RADAR_RUNTIME='IMPLEMENTED_ENGINEERING',VALIDATION_COHORT_RUNTIME='IMPLEMENTED_ENGINEERING',RADAR_COHORT_PERSISTED_E2E='PASS_LOCAL',independent_identity_oracle='PASS_LOCAL',publication_counts=publication_counts,real_accepted_source=realcounts,unique_enrollments=len(enrollments),V4_15_ACCEPTED_HEAD='NOT_CREATED',Production=False,Shadow=False,Focus=False,NEXT='R20E_AFTER_R20D_AND_R20B')
if __name__=='__main__':
    result=check();atomic(ROOT/'reports/r20c/INDEPENDENT_RADAR_COHORT_GATE.json',result);print(json.dumps(result))
