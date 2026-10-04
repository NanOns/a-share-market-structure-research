"""Isolated deterministic activation grants. Never usable as a real authority."""
import copy, uuid
from scripts.r24_io import ROOT, read, ref, atomic
from scripts.v4_16_real_shadow_runtime import dependency_digest, grant_digest

def prepare(name=None, changes=None):
    base='reports/r24/activation_simulation/'+(name or uuid.uuid4().hex)
    deps=read('config/v4_16_runtime_dependencies_v2.json')
    authority=read('config/v4_16_runtime_activation_authority_v2.json')
    lineage='R24_SIMULATION_LINEAGE'
    sources={}
    for family,key in [('OWNER_OUTPUT','owner'),('T0_SNAPSHOT','snapshot')]:
        p=read('config/v4_16_r23_'+key+'_fixture_v1.json')
        p.update(evidence_class='ACTIVATION_SIMULATION',evidence_origin='ACTIVATION_SIMULATION',evidence_status='NOT_REAL_EVIDENCE')
        for row in p.get('rows',[]):
            row['state_lineage_id']=lineage
            fixture_events=row.pop('radar_owner_events',[])
            if fixture_events:
                p.setdefault('events',[]).append(dict(entity_type=row['entity_type'],entity_id=row['entity_id'],
                    event_types=fixture_events,event_trade_date=p['trade_date']))
        binding=atomic(base+'/'+key+'.json',p)
        sources[family]=dict(binding=binding,target_trade_date='2026-09-28',source_identity='R24_SIM_'+family,
            source_revision='R1',provider='DETERMINISTIC_SIMULATION')
    seed=dict(publication_id='R24_BOUNDARY_SIMULATION',trade_date='2026-09-24',namespace='SHADOW_V4',
        evidence_class='RECONSTRUCTED_ASOF',model_contract_id='RESEARCH_STATE_V1',
        parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',state_lineage_id=lineage,owner_state={})
    predecessor=atomic(base+'/predecessor.json',seed)
    source_authority=dict(contract_id='R24_SIM_SOURCE_AUTHORITY_V1',environment_class='ACTIVATION_SIMULATION',
        adapter_id='ACCEPTED_LOCAL_EXACT_BYTES_V1',sources=sources,
        owner_heads=deps['owner_heads'],
        future_binding=ref('config/v4_16_r23_future_fixture_v1.json'))
    if changes:changes(authority,deps,source_authority,seed)
    predecessor=atomic(base+'/predecessor.json',seed)
    source_binding=atomic(base+'/source_authority.json',source_authority)
    authority.update(authority_id='R24_SIMULATION_'+base.rsplit('/',1)[1],runtime_authorized=True,
        real_shadow_authorized=True,environment_class='ACTIVATION_SIMULATION')
    authority['grant']=dict(authority_id=authority['authority_id'],effective_trade_date='2026-09-28',
        effective_from='2026-09-28T00:00:00Z',model_contract_id='RESEARCH_STATE_V1',
        parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',state_lineage_id=lineage,
        capability_scope=['PURE_CORE_STOCK'],runtime_dependency_contract_id=deps['contract_id'],
        dependency_set_digest=dependency_digest(deps),source_authority=source_binding,
        rollback_identity='R24_APPEND_ONLY_STOP_V1',expected_prior_activation_head=None,
        predecessor=predecessor,first_trade_date='2026-09-28',
        storage_identity=dict(database_path=base+'/successor.sqlite',namespace='SHADOW_V4',execution_mode='SHADOW',
            evidence_origin='ACTIVATION_SIMULATION',migration=deps['migration']),
        **{k:deps[k] for k in ('clock','slot','storage','source_adapters','initialization_boundary')})
    authority['external_acceptance']=atomic(base+'/acceptance.json',dict(
        authority_id=authority['authority_id'],authority_digest=grant_digest(authority),
        decision='SIMULATION_ONLY_NOT_REAL_ACCEPTANCE'))
    original=deps['activation']
    deps['activation']=atomic(base+'/authority.json',authority)
    deps['bindings']=[b if b!=original else deps['activation'] for b in deps['bindings']]
    manifest=base+'/dependencies.json'
    atomic(manifest,deps)
    request=dict(trade_date='2026-09-28',model_contract_id='RESEARCH_STATE_V1',
        parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',state_lineage_id=lineage,
        capabilities=['PURE_CORE_STOCK'],accepted_at='2026-09-28T14:00:00Z',revision=1,expected_head=None)
    return dict(base=base,manifest=manifest,request=request,database=base+'/successor.sqlite')

def controller(context):
    from scripts.v4_16_shadow_runtime import ShadowRuntimeController
    return ShadowRuntimeController(ROOT,mode='REAL_SHADOW',simulation_dependencies=context['manifest'])

class SimulationClock:
    def __init__(self,late=False):self.count=0;self.late=late
    def __call__(self):
        self.count+=1
        if self.count<=8:return '2026-09-28T13:00:01Z' if self.late else '2026-09-28T12:59:00Z'
        return '2026-09-28T13:01:00Z' if self.count==9 else '2026-09-28T14:00:00Z'

def regrant(context,mutate):
    deps=read(context['manifest'])
    authority=read(deps['activation']['path'])
    mutate(authority)
    acceptance=authority['external_acceptance']['path']
    authority['external_acceptance']=atomic(acceptance,dict(authority_id=authority['authority_id'],
       authority_digest=grant_digest(authority),decision='SIMULATION_ONLY_NOT_REAL_ACCEPTANCE'))
    old=deps['activation']
    deps['activation']=atomic(old['path'],authority)
    deps['bindings']=[deps['activation'] if b==old else b for b in deps['bindings']]
    atomic(context['manifest'],deps)
