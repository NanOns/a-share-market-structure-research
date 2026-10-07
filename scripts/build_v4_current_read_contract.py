"""Freeze exact accepted owner sources before authoring the UI."""
import gzip
import hashlib
import json
from scripts.v4_production_cutover_evidence import ROOT, REPORT, binding, write


def load(path):
    return json.loads((ROOT/path).read_bytes())


def bound_load(ref):
    actual=binding(ref['path'])
    assert actual['sha256']==ref['sha256'] and actual['bytes']==ref.get('bytes',ref.get('byte_count')),'OWNER_RECEIPT_BINDING_INVALID'
    return load(ref['path'])


def main():
    authority=load('config/v4_current_stage_authority_v2.json')
    data=load('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    stage=load('data/v4/V4_STAGE_ACCEPTED_HEAD.json')
    head=load('data/v4/V4_15_ACCEPTED_HEAD.json')
    replay_head=load('data/v4/V4_14_ACCEPTED_HEAD.json')
    replay_seal=bound_load(replay_head['bindings']['runtime_seal'])
    candidates=[]
    for ref in replay_seal['replay_publications']:
        value=bound_load(ref)
        if value.get('trade_date')==data['accepted_trade_date'] and value.get('evidence_class')=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED':candidates.append((ref,value))
    assert len(candidates)==1,'EXACT_CURRENT_REAL_OWNER_PUBLICATION_REQUIRED'
    replay_ref,replay=candidates[0]
    runtime_seal=bound_load(head['bindings']['runtime_seal'])
    producer_ref=runtime_seal['persisted_processes']['PRODUCER_RECEIPT.json']
    settlement_ref=runtime_seal['persisted_processes']['SETTLEMENT_RECEIPT.json']
    producer=bound_load(producer_ref)
    settlement=bound_load(settlement_ref)
    pub=bound_load(producer['real_publication'])
    assert data['accepted_trade_date']==head['accepted_trade_date']==pub['trade_date']==replay['trade_date'],'OWNER_ACCEPTANCE_NOT_CURRENT'
    assert authority['data_head']['sha256']==binding('data/v4/V4_DATA_ACCEPTED_HEAD.json')['sha256'],'STAGE_AUTHORITY_DATA_HEAD_NOT_CURRENT'
    member=load(authority['membership']['path'])
    sources={}
    def add(key, ref, owner, cid):
        actual=binding(ref['path'],owner,cid)
        assert actual['sha256']==ref['sha256'] and actual['bytes']==ref.get('bytes',ref.get('byte_count')),(key,actual)
        sources[key]=actual
    for key in ['RAW_DAILY','IDENTITY_UNIVERSE','ADJUSTED_DAILY','TRADING_STATUS']:
        info=data['component_permissions'][key]
        add(key,info['artifact'],info['accepted_owner_stage'],info['accepted_algorithm_contract'])
        add(key+'_receipt',info['receipt'],info['accepted_owner_stage'],info['accepted_algorithm_contract'])
    add('replay',replay_ref,'V4-14','V4_14_ACCEPTED_HEAD_V1')
    add('states',replay['current_owner_publication'],'V4-11','RESEARCH_STATE_V1')
    add('events',replay['event_source'],'V4-11','STATE_EVENT_V1')
    add('membership',member['facts'],'V4-08','V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1')
    name_ref=stage['bindings']['v4_01_identity_map']
    add('identity_names',binding(name_ref['path']),'V4-01','SECURITY_ENTITY_MAP_R7')
    assert sources['identity_names']['sha256']==name_ref['sha256']
    add('radar',producer['real_publication'],'V4-15','V4_15_RADAR_COHORT_ENGINEERING_V1')
    add('producer',producer_ref,'V4-15','V4_15_RUNTIME_CANDIDATE_R20_SEAL_V1')
    add('settlement_receipt',settlement_ref,'V4-15','V4_15_RUNTIME_CANDIDATE_R20_SEAL_V1')
    for key,ref in [('runtime_seal',head['bindings']['runtime_seal']),('maturity',head['bindings']['maturity_readback']),('replay_seal',load('data/v4/V4_14_ACCEPTED_HEAD.json')['bindings']['runtime_seal'])]:
        add(key,ref,'V4-15' if key!='replay_seal' else 'V4-14',key)
    with gzip.open(ROOT/sources['states']['path'],'rt',encoding='utf8') as stream: states=json.load(stream)['rows']
    fields=['entity_id','entity_type','trade_date','scenario','scenario_status','state','final_eligibility','state_freshness','health','maturity','episode_id','matched_predicates','unknown_predicates','reason_codes']
    compact=[{k:r[k] for k in fields if k in r} for r in states]
    projection=(json.dumps(dict(source=sources['states'],rows=compact,projection_only=True),ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
    projection_path='data/v4/production_views/blobs/'+hashlib.sha256(projection).hexdigest()+'.json'
    target=ROOT/projection_path
    if target.exists():assert target.read_bytes()==projection,'IMMUTABLE_PROJECTION_CONFLICT'
    else:write(target,projection)
    add('state_view',binding(projection_path),'V4-11','V4_CURRENT_ACCEPTED_READ_CONTRACT_V1')
    refs={key:[] for key in ['ledger','observations','cohort','outcomes']}
    for key,values in [('ledger',pub['daily_ledger']),('observations',pub['observations']),('cohort',pub['enrollments']),('outcomes',settlement['real_outcomes'])]:
        for ref in values:
            actual=binding(ref['path'],'V4-15','V4_15_RADAR_COHORT_ENGINEERING_V1' if key!='outcomes' else 'V4_15_SETTLEMENT_RUNTIME_V1')
            assert actual['sha256']==ref['sha256'] and actual['bytes']==ref['bytes']
            refs[key].append(actual)
    anchors={key:binding(path) for key,path in dict(stage_authority='config/v4_current_stage_authority_v2.json',data_head='data/v4/V4_DATA_ACCEPTED_HEAD.json',stage_head='data/v4/V4_STAGE_ACCEPTED_HEAD.json',owner_head='data/v4/V4_15_ACCEPTED_HEAD.json',permission_authority='config/v4_19_focus_source_cutover_contract_v1.json',ui_v1='config/v4_20_default_ui_cutover_contract_v1.json').items()}
    for key,ref in anchors.items():
        archive='data/v4/production_views/blobs/'+ref['sha256']+'.json'
        write(archive,(ROOT/ref['path']).read_bytes())
        anchors[key]={**ref,'path':archive,'authority_source_path':ref['path']}
    owners={key:binding(value['path'],key) for key,value in authority['immutable_owner_heads'].items()}
    modules={'summary':['events','observations','replay','identity_names'],'radar':['radar','ledger','replay','identity_names'], 'entity':['RAW_DAILY','IDENTITY_UNIVERSE','states','state_view','events','identity_names'], 'sector':['membership'], 'cohort':['radar','cohort','maturity','identity_names'], 'settlement':['outcomes','settlement_receipt','maturity'], 'health':['replay','maturity']}
    contract=dict(contract_id='V4_CURRENT_ACCEPTED_READ_CONTRACT_V1',version='1.0.0',source_mode='V4_ACCEPTED_RESEARCH_READONLY',namespace='V4_CURRENT_ACCEPTED',anchors=anchors,owner_heads=owners,sources=sources,row_bindings=refs,modules=modules,
        accepted_trade_date=data['accepted_trade_date'],fallback='NONE',writes=False,focus_write=False,permission_grant=False,
        states=['READY_CURRENT_ACCEPTED','WAIT_NEXT_ACCEPTED_INPUT','EMPTY_VALID','NO_ELIGIBLE_OBJECTS','PENDING','RIGHT_CENSORED','NOT_AUTHORIZED','UNKNOWN','SOURCE_INVALID','SOURCE_FIELD_UNAVAILABLE'],
        quality_policy='Preserve owner UNKNOWN/reasons; a known identifier does not promote algorithm signal quality; actual validated empty is EMPTY_VALID',
        lineage_policy='Current heads and exact owner seal -> real scoped publication -> bound rows; older producer stage heads are explicit historical evidence, never current authority',
        daily_refresh='V4_ACCEPTED_CURRENT_REFRESH_V1',source_discovery=False)
    write('config/v4_current_accepted_read_contract_v1.json',contract)
    v1=binding('config/v4_20_default_ui_cutover_contract_v1.json')
    write('config/v4_20_default_ui_cutover_contract_v2.json',dict(contract_id='V4_20_DEFAULT_UI_CUTOVER_CONTRACT_V2',version='2.0.0',predecessor=v1,predecessor_rules_preserved=True,added_display_mode='V4_ACCEPTED_RESEARCH_READONLY',
        resolution=[dict(permission=True,accepted_readable=True,mode='PRODUCTION_V4_PROVISIONAL'),dict(permission=False,accepted_readable=True,mode='V4_ACCEPTED_RESEARCH_READONLY'),dict(permission=False,accepted_readable=False,mode='NO_PERMISSION')],
        writes='V4-19 exact permission receipts required independently; display never authorizes Focus mutation',global_v4_pass=False,shadow_stable_evidence=False))
    inventory=[]
    for module,keys in modules.items():
        for key in keys:
            values=refs.get(key,[sources.get(key)])
            for value in values:
                inventory.append(dict(module=module,field={'events':'effective_event / counterevidence','observations':'why_now','ledger':'signal_type / eligibility_state','states':'scenario / health / final_eligibility','RAW_DAILY':'close / source_security_key','IDENTITY_UNIVERSE':'security_id / list_date','membership':'sector_id / security_id','cohort':'T0 / evidence_class','outcomes':'horizon / outcome_status','maturity':'unproved_horizons'}.get(key,key),owner_stage=value['owner_stage'],source_artifact=value,field_path='rows[*]' if key in ['states','RAW_DAILY','IDENTITY_UNIVERSE'] else key,availability='EXACT_BOUND',quality_semantics=contract['quality_policy'],fallback='NONE'))
    write(REPORT/'CURRENT_COMPONENT_OWNER_INVENTORY.json',dict(fields=inventory,stock_state_owner='V4-11',relative_state='UNKNOWN_ACCEPTED_OWNER_CAPABILITY_UNAVAILABLE; never substitute price returns',sector_state='Accepted PIT membership; rotation algorithm capability remains scoped UNKNOWN',health_owner='V4-14/V4-15'))
    print('P0-1 source contracts frozen',len(compact),flush=True)


if __name__=='__main__':main()
