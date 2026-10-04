"""Future-session fixtures are isolated simulations, never actual daily acceptance."""
import uuid
from scripts.r24r1_io import ROOT, read, ref, atomic
from scripts.v4_16_go_forward_shadow_runtime import dependency_digest, grant_digest, digest

TARGET='2026-10-08'
PRIOR='2026-09-30'

def prepare(name=None, mutate=None, changes=None):
    base='reports/r24r1/activation_simulation/'+(name or uuid.uuid4().hex)
    deps=read('config/v4_16_runtime_dependencies_v3.json')
    authority=read(deps['activation']['path'])
    contract=read(deps['go_forward_input']['path'])
    lineage='R24R1_SIMULATION_LINEAGE'
    sources={}; runtime_sources={}
    for family,key in [('OWNER_OUTPUT','owner'),('T0_SNAPSHOT','snapshot')]:
        p=read('config/v4_16_r23_'+key+'_fixture_v1.json')
        p.update(trade_date=TARGET,evidence_class='ACTIVATION_SIMULATION',evidence_origin='ACTIVATION_SIMULATION',evidence_status='NOT_REAL_EVIDENCE')
        for row in p.get('rows',[]):
            row['state_lineage_id']=lineage
            if 'trade_date' in row:row['trade_date']=TARGET
            if 'cutoff' in row:row['cutoff']=TARGET+'T12:59:00Z'
            fixture_events=row.pop('radar_owner_events',[])
            if fixture_events:p.setdefault('events',[]).append(dict(entity_type=row['entity_type'],entity_id=row['entity_id'],event_types=fixture_events,event_trade_date=TARGET))
        binding=atomic(base+'/'+key+'.json',p)
        runtime_sources[family]=dict(binding=binding,target_trade_date=TARGET,source_identity='R24R1_SIM_'+family,source_revision='R1',provider='DETERMINISTIC_SIMULATION')
        sources[family]=binding
    for family in ['TDX_RAW_DAILY','ADJUSTED_DAILY']:
        sources[family]=atomic(base+'/'+family.lower()+'.json',dict(trade_date=TARGET,max_source_trade_date=TARGET,rows=[],evidence_class='ACTIVATION_SIMULATION',not_real_evidence=True))
    daily=dict(contract_id=contract['contract_id'],daily_input_id='SIM_DAY_'+base.rsplit('/',1)[1],revision=1,
        target_trade_date=TARGET,accepted_at=TARGET+'T12:59:00Z',previous_trade_date=PRIOR,target_session_confirmed=True,
        calendar=atomic(base+'/calendar.json',dict(session_dates=[PRIOR,TARGET,'2026-10-09','2026-10-12','2026-10-13','2026-10-14'],fixture_only=True)),
        identity=atomic(base+'/identity.json',dict(accepted=True,target_trade_date=TARGET,universe=['S','C1','C2'],evidence_class='ACTIVATION_SIMULATION')),
        membership='NOT_REQUIRED_FOR_SCOPE',sources={k:dict(binding=b,target_trade_date=TARGET,max_source_trade_date=TARGET,
            provider_observed_at=TARGET+'T12:58:00Z',system_available_at=TARGET+'T12:58:30Z',accepted_at=TARGET+'T12:59:00Z',quality='ACCEPTED',capability='PURE_CORE_STOCK') for k,b in sources.items()},
        snapshot_identity='SIM_SNAPSHOT_'+base.rsplit('/',1)[1],max_source_trade_date=TARGET,
        immutable_algorithm_bindings=contract['immutable_algorithm_bindings'],environment_class='ACTIVATION_SIMULATION',**contract['model_identity'])
    grant_extra=dict(target_trade_date=TARGET,daily_input_boundary=TARGET+'T13:00:00Z',minimum_daily_input_revision=1)
    if mutate:mutate(daily,grant_extra,base)
    daily['source_manifest_digest']=digest(daily['sources'])
    daily['quality_capability_matrix']={k:dict(quality=v['quality'],capability=v['capability']) for k,v in daily['sources'].items()}
    daily.setdefault('day_package',atomic(base+'/package.json',dict(trade_date=TARGET,snapshot_identity=daily['snapshot_identity'],sources=daily['sources'])))
    daily['daily_input_digest']=digest(daily)
    daily_binding=atomic(base+'/daily_input.json',daily)
    seed=dict(publication_id='R24R1_BOUNDARY_SIMULATION',trade_date=PRIOR,namespace='SHADOW_V4',evidence_class='RECONSTRUCTED_ASOF',
        model_contract_id='RESEARCH_STATE_V1',parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',state_lineage_id=lineage,owner_state={})
    source_authority=dict(contract_id='R24R1_SIM_SOURCE_AUTHORITY_V1',environment_class='ACTIVATION_SIMULATION',
        adapter_id='ACCEPTED_LOCAL_EXACT_BYTES_V1',sources=runtime_sources,owner_heads=deps['owner_heads'])
    if changes:changes(authority,deps,source_authority,seed)
    predecessor=atomic(base+'/predecessor.json',seed)
    import json
    future=json.loads(json.dumps(read('config/v4_16_r23_future_fixture_v1.json')).replace('2026-09-29','2026-10-09'))
    future.update(evidence_origin='ACTIVATION_SIMULATION',evidence_class='NOT_REAL_EVIDENCE')
    future_binding=atomic(base+'/future.json',future)
    source_authority['future_binding']=future_binding
    source_binding=atomic(base+'/source_authority.json',source_authority)
    authority.update(authority_id='R24R1_SIMULATION_'+base.rsplit('/',1)[1],runtime_authorized=True,real_shadow_authorized=True,environment_class='ACTIVATION_SIMULATION')
    authority['grant']=dict(authority_id=authority['authority_id'],effective_trade_date=TARGET,effective_from=TARGET+'T00:00:00Z',
        model_contract_id='RESEARCH_STATE_V1',parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',state_lineage_id=lineage,
        capability_scope=['PURE_CORE_STOCK'],runtime_dependency_contract_id=deps['contract_id'],dependency_set_digest=dependency_digest(deps),
        source_authority=source_binding,rollback_identity='R24_APPEND_ONLY_STOP_V1',expected_prior_activation_head=None,
        predecessor=predecessor,first_trade_date=TARGET,daily_input_authority=daily_binding,daily_input_digest=daily['daily_input_digest'],
        storage_identity=dict(database_path=base+'/successor.sqlite',namespace='SHADOW_V4',execution_mode='SHADOW',evidence_origin='ACTIVATION_SIMULATION',migration=deps['migration']),
        **grant_extra,**{k:deps[k] for k in ('clock','slot','storage','source_adapters','initialization_boundary')})
    authority['external_acceptance']=atomic(base+'/acceptance.json',dict(authority_id=authority['authority_id'],authority_digest=grant_digest(authority),decision='SIMULATION_ONLY_NOT_REAL_ACCEPTANCE'))
    old=deps['activation']; deps['activation']=atomic(base+'/authority.json',authority)
    deps['bindings']=[deps['activation'] if b==old else b for b in deps['bindings']]
    manifest=base+'/dependencies.json'; atomic(manifest,deps)
    return dict(base=base,manifest=manifest,database=base+'/successor.sqlite',request=dict(trade_date=TARGET,model_contract_id='RESEARCH_STATE_V1',
        parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',state_lineage_id=lineage,capabilities=['PURE_CORE_STOCK'],accepted_at=TARGET+'T14:00:00Z',revision=1,expected_head=None))

def controller(context):
    from scripts.v4_16_shadow_runtime import ShadowRuntimeController
    return ShadowRuntimeController(ROOT,mode='REAL_SHADOW',simulation_dependencies=context['manifest'])

class SimulationClock:
    def __init__(self,late=False):self.count=0;self.late=late
    def __call__(self):
        self.count+=1
        return TARGET+('T13:00:01Z' if self.late else 'T12:59:00Z') if self.count<=8 else TARGET+('T13:01:00Z' if self.count==9 else 'T14:00:00Z')

def regrant(context,mutate):
    deps=read(context['manifest']); a=read(deps['activation']['path'])
    mutate(a)
    a['external_acceptance']=atomic(a['external_acceptance']['path'],dict(authority_id=a['authority_id'],authority_digest=grant_digest(a),decision='SIMULATION_ONLY_NOT_REAL_ACCEPTANCE'))
    old=deps['activation']; deps['activation']=atomic(old['path'],a)
    deps['bindings']=[deps['activation'] if b==old else b for b in deps['bindings']]
    atomic(context['manifest'],deps)
