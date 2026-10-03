"""Independent persisted-evidence oracle. Never imports a replay evaluator.

Expectations come from literal frozen books and independently evaluated owner
counter/identity contracts. Execution receipts are not expected-result authority.
"""
import json,hashlib
from pathlib import Path
from datetime import datetime

def checksum(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def require(ok,reason):
    if not ok:raise ValueError(reason)
def exact(root,binding):
    p=Path(root)/binding['path'];require(not Path(binding['path']).is_absolute() and '..' not in Path(binding['path']).parts,'ORACLE_PATH_ESCAPE')
    require(p.is_file() and not p.is_symlink(),'ORACLE_SOURCE_MISSING')
    with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    require(sha==binding['sha256'] and p.stat().st_size==binding.get('bytes',binding.get('byte_count')),'ORACLE_EXACT_BYTES_CHANGED')
    return p
def read(root,binding):return json.loads(exact(root,binding).read_bytes())

class Oracle:
    def __init__(self,root):
        self.root=Path(root);self.stage=json.loads((self.root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes());self.head=read(root,self.stage['v4_13_binding'])
        self.data=json.loads((self.root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes());self.calendar_ref=self.data['calendar'];self.dates=read(root,self.calendar_ref)['session_dates']
        self.parameters=json.loads((self.root/'config/v4_10_parameter_set_r1_2.json').read_bytes())
        self.book=json.loads((self.root/'config/v4_14_machine_vectors_v1_1.json').read_bytes())
        self.contracts=[dict(path='config/v4_14_'+n+'_v1_1.json',sha256=hashlib.sha256((self.root/('config/v4_14_'+n+'_v1_1.json')).read_bytes()).hexdigest(),bytes=(self.root/('config/v4_14_'+n+'_v1_1.json')).stat().st_size) for n in ['replay_gate_b_contract','replay_case_registry','temporal_non_edge_registry','quality_degradation','machine_vectors']]
        self.key_fields=set(json.loads((self.root/'config/v4_14_replay_input_envelope_r18_v1.json').read_bytes())['event_logical_key'])
    def previous(self,date):
        require(date in self.dates and self.dates.index(date)>0,'ORACLE_MARKET_DATE_INVALID');return self.dates[self.dates.index(date)-1]
    def authority(self,envelope):
        a=envelope['authority_bindings'];require(a['amended_v4_13']==self.stage['v4_13_binding'] and a['contract_package']==self.contracts and a['active_family_closure']==self.head['active_family_closure'],'ORACLE_STALE_ACTIVE_FAMILY')
        require(envelope['contract_package_digest']==checksum(self.contracts),'ORACLE_PACKAGE_DIGEST')
        for r in [a['amended_v4_13'],a['active_family_closure'],a['data'],a['stage'],a['calendar'],a['membership'],*a['owners'].values(),*a['contract_package']]:exact(self.root,r)
        require(a['calendar']==self.calendar_ref,'ORACLE_CALENDAR_MISMATCH')
    def temporal(self,e):
        self.authority(e);require(e['previous_market_session']==self.previous(e['target_trade_date']),'ORACLE_WRONG_PREVIOUS_SESSION')
        for s in e['source_availability']:
            require(s['max_source_trade_date']<=e['target_trade_date'],'ORACLE_FUTURE_SOURCE')
            require(datetime.fromisoformat(s['system_available_at'].replace('Z','+00:00'))<=datetime.fromisoformat(e['cutoff'].replace('Z','+00:00')),'ORACLE_AFTER_CUTOFF')
            require(s.get('membership_effective_date',e['target_trade_date'])<=e['target_trade_date'],'ORACLE_FUTURE_MEMBERSHIP')
        if e['evidence_class']=='HISTORICAL_PIT_EFFECTIVENESS':require(e.get('AS_RECORDED') is True and e.get('historical_membership_basis')=='PIT_OBSERVED' and e.get('complete_historical_availability') is True,'ORACLE_HISTORICAL_PIT_NOT_VERIFIABLE')
    def cross_process(self,producer,consumer):
        require(producer['pid']!=consumer['pid'],'ORACLE_SAME_PID_FRAUD')
        require(producer['producer_exited'] and producer['os_wait_completed'] and producer['exit_code']==0,'ORACLE_PRODUCER_NOT_EXITED')
        require(consumer['started_at']>producer['exited_at'],'ORACLE_CONSUMER_STARTED_BEFORE_EXIT')
        require(consumer['previous_readback']==producer['publication'],'ORACLE_READBACK_DIFFERS_FROM_PRODUCER')
        require(consumer['calendar_binding']==producer['calendar_binding']==self.calendar_ref and consumer['in_memory_prior'] is False,'ORACLE_PROCESS_CALENDAR_OR_MEMORY')
    def state(self,row,prior,inputs):
        require(row['entity_type']!='STOCK' or row['maturity']!='WARM','ORACLE_ILLEGAL_STOCK_WARM')
        require(row['trade_date']==inputs['trade_date'],'ORACLE_STATE_DATE')
        f={k:v['value'] for k,v in inputs['input_provenance'].items()};p=self.parameters
        required=['CONFIRMED','PREWATCH','SEED','core_price_damage','frozen_invalidation','suspended']
        unknown=any(f[k]=='UNKNOWN' for k in required)
        hard=f['core_price_damage']=='TRUE' or f['frozen_invalidation']=='TRUE'
        if hard:
            require(row['maturity']=='NONE' and row['validity']=='INVALIDATED' and row['final_eligibility']=='FALSE','ORACLE_HARD_EXIT')
        elif unknown:
            require(row['final_eligibility']=='UNKNOWN','ORACLE_UNKNOWN_COERCED_TO_FALSE')
            if prior:require(row['maturity']==prior['maturity'] and row['expiry_count']==prior['expiry_count'] and row['downgrade_count']==prior['downgrade_count'] and row['episode_id']==prior['episode_id'],'ORACLE_UNKNOWN_COUNTER_PAUSE')
        else:
            stage=next((s for s in ['CONFIRMED','PREWATCH','SEED'] if f[s]=='TRUE'),'NONE');rank=dict(NONE=0,SEED=1,PREWATCH=2,CONFIRMED=4);old=prior['maturity'] if prior else 'NONE';effective=stage
            count=0
            if prior and rank[stage]<rank[old]:
                count=prior['downgrade_count']+(1 if row['session_index']>prior['session_index'] else 0) if prior['downgrade_candidate']==stage else 1
                if count<p['downgrade_sessions']:effective=old
            require(row['downgrade_count']==count,'ORACLE_HYSTERESIS_COUNTER')
            expiry=0
            if effective in ('SEED','PREWATCH') and f[effective]=='TRUE':
                baseline=prior['improvement_baseline'] if prior else None;metric=f['delta3']
                improved=baseline is not None and metric!='UNKNOWN' and metric-baseline>=p['expiry_improvement_pp']
                upgraded=rank[effective]>rank[old]
                expiry=1 if upgraded or improved or baseline is None else prior['expiry_count']+(1 if row['session_index']>prior['session_index'] else 0)
                if metric=='UNKNOWN':expiry=prior['expiry_count'] if prior else 0
                if expiry>=p['expiry_sessions']:effective='NONE'
            require(row['expiry_count']==expiry,'ORACLE_EXPIRY_COUNTER');require(row['maturity']==effective,'ORACLE_STATE_TRANSITION')
        if prior:
            reentry='REENTERED' in row['transition_reasons']
            if reentry:require(row['episode_id']!=prior['episode_id'] and row['parent_episode_id']==prior['episode_id'] and row['session_index']>prior['exit_session_index'],'ORACLE_REENTRY_IDENTITY')
            else:require(row['episode_id']==prior['episode_id'],'ORACLE_DUPLICATE_EPISODE_CONTINUATION')
    def events(self,output,prior):
        keys=output['logical_events'];require(all(set(k)==self.key_fields for k in keys),'ORACLE_REVISION_IN_LOGICAL_KEY')
        require(len(keys)==len({checksum(k) for k in keys}),'ORACLE_DUPLICATE_LOGICAL_EVENT')
        row=output['d2']['rows'][0];events=output['events']
        require(all(k['entity_id']==row['entity_id'] and k['entity_type']==row['entity_type'] and k['episode_id']==row['episode_id'] and k['signal_market_date']==row['trade_date'] and k['model_contract_id']==row['model_contract_id'] and k['parameter_set_id']==row['parameter_set_id'] for k in keys),'ORACLE_LOGICAL_KEY_OWNER_IDENTITY')
        if prior and prior['maturity']=='CONFIRMED' and row['maturity']=='CONFIRMED' and prior['final_eligibility']==row['final_eligibility']=='TRUE' and prior['scenario']==row['scenario'] and row['health']=='STABLE':
            require(all(e['primary_event']=='PERSISTENT_CONFIRMED' for e in events) and all(k['event_type']=='PERSISTENT_CONFIRMED' for k in keys),'ORACLE_PERSISTENT_ACTIONABLE_DUPLICATE')
        require(len({e['entity_id'] for e in events})==len(events),'ORACLE_MULTI_SECTOR_STOCK_DUPLICATE')
    def manifest(self,artifact_root,m):
        e=m['envelope'];self.temporal(e)
        require(m['input_digest']==checksum(e) and m['output_digest']==checksum(m['output']),'ORACLE_MANIFEST_CONTENT_DIGEST')
        require(m['replay_publication_id']=='REPLAY:'+checksum({k:v for k,v in m.items() if k!='replay_publication_id'}),'ORACLE_PUBLICATION_IDENTITY')
        prior=None
        if m['previous_state_publication']:
            old=read(artifact_root,m['previous_state_publication']);require(old['target_trade_date']==self.previous(m['target_trade_date']),'ORACLE_PRIOR_DATE_NOT_EXACT_SESSION')
            require(old['output_digest']==checksum(old['output']),'ORACLE_PREVIOUS_DIGEST_MUTATION');prior=old['output']['d2']['rows'][0]
        require(e['previous_state_publication']==m['previous_state_publication'],'ORACLE_ENVELOPE_PREDECESSOR')
        output=m['output'];self.state(output['d2']['rows'][0],prior,output['d2']['inputs'][0]);self.events(output,prior)
        require([n['node'] for n in output['trace']]==['Accepted Source Binding','Seed','Sector/Rotation','PREWATCH','Confirmation','Structure','State Reducer','Event Diff','Profile/Context','Gate-B Observation'],'ORACLE_FULL_DAG_INCOMPLETE')
        require(output['previous_D1_publication']==m['previous_state_publication'],'ORACLE_D1_PRIOR_LINEAGE')
        if prior:
            old=read(artifact_root,m['previous_state_publication'])['output'];require(output['anchor']==old['anchor'],'ORACLE_ANCHOR_IDENTITY_CHANGED')
            require(output['structure_ledger']['previous_session_state_ref']==self.previous(m['target_trade_date']),'ORACLE_D1_PREVIOUS_DATE')
        return True
    def deterministic(self,first,second):
        require(first['input_digest']==second['input_digest'],'ORACLE_DIFFERENT_FROZEN_INPUT')
        require(first['envelope']['authority_bindings']==second['envelope']['authority_bindings'] and first['previous_state_publication']==second['previous_state_publication'],'ORACLE_DETERMINISTIC_AUTHORITY_OR_PRIOR_CHANGED')
        require(first['output_digest']==second['output_digest'] and checksum(first['output'])==checksum(second['output']),'ORACLE_IDENTICAL_INPUT_DIFFERENT_OUTPUT')
    def vectors(self,gate):
        rows={r['id']:r for r in gate['rows']};results=[]
        require(len(rows)==len(self.book['vectors'])==60,'ORACLE_VECTOR_COMPLETENESS')
        for v in self.book['vectors']:
            r=rows[v['id']];require(r['input_digest']==checksum(v['input']) and r['actual']==v['expected'],'ORACLE_FROZEN_EXPECTATION:'+v['id']);results.append(dict(id=v['id'],dimension=v['dimension'],status='PASS'))
        require(len({r['dimension'] for r in results})==17,'ORACLE_DIMENSION_COMPLETENESS');return results
    def gate(self,artifact_root,gate):
        for r in gate['records']:
            m=read(artifact_root,r['publication']);self.manifest(artifact_root,m)
            if r['producer_execution']:self.cross_process(read(artifact_root,r['producer_execution']),read(artifact_root,r['execution']))
        same=gate['same_day'];a=read(artifact_root,same['r1']);b=read(artifact_root,same['r2']);self.manifest(artifact_root,b)
        require(a['previous_state_publication']==b['previous_state_publication']==same['previous'],'ORACLE_R2_POINTS_TO_R1')
        require(a['output']['logical_events']==b['output']['logical_events'] and a['output']['d2']['rows']==b['output']['d2']['rows'],'ORACLE_REVISION_DUPLICATES_STATE_OR_EVENT')
        d=gate['determinism'];x=read(artifact_root,d['first']);y=read(artifact_root,d['second']);self.deterministic(x,y)
        require(read(artifact_root,d['first_execution'])['pid']!=read(artifact_root,d['second_execution'])['pid'],'ORACLE_DETERMINISM_NOT_FRESH_PROCESSES')
        return True
