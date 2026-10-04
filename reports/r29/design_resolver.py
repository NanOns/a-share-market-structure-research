"""Synthetic pure UI design resolver. Never imported by the production router."""
from copy import deepcopy
import hashlib
import json

CAPS=('STOCK_CORE','STOCK_SECTOR_DEPENDENT','SECTOR_STAGE','ROTATION','SECTOR_RISK_CHANGE')
DEPS={'STOCK_CORE':[],'SECTOR_STAGE':[],'STOCK_SECTOR_DEPENDENT':['STOCK_CORE','SECTOR_STAGE'],'ROTATION':['SECTOR_STAGE'],'SECTOR_RISK_CHANGE':['SECTOR_STAGE']}
MODULES={'today_overview':([],list(CAPS)),'sector_research':(['SECTOR_STAGE'],['ROTATION','SECTOR_RISK_CHANGE']),'stock_research':(['STOCK_CORE'],['STOCK_SECTOR_DEPENDENT']),'focus_tracking':([],list(CAPS)),'market_events':([],['STOCK_CORE','SECTOR_STAGE','ROTATION','SECTOR_RISK_CHANGE']),'data_diagnostics':([],list(CAPS)),'stock_sector_dependent':(['STOCK_SECTOR_DEPENDENT'],[]),'rotation':(['ROTATION'],[]),'sector_risk_change':(['SECTOR_RISK_CHANGE'],[])}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def permitted(cap, state, seen=None):
    seen=set() if seen is None else seen
    if cap in seen or cap not in CAPS: return False
    item=state['permissions'].get(cap)
    return bool(isinstance(item,dict) and item.get('permission') is True and item.get('accepted') is True and item.get('active') is True and item.get('receipt_digest') and all(permitted(d,state,seen|{cap}) for d in DEPS[cap]))


def resolve(module,state,explicit_shadow=False):
    required=MODULES[module][0]
    mode='SHADOW_V4' if explicit_shadow else 'PRODUCTION_V4' if required and all(permitted(c,state) for c in required) else 'LEGACY_PRODUCTION'
    reason=None
    if state.get('discovery') in ('latest','mtime','browser','page_local','global_flag'):
        return dict(module=module,mode='UNKNOWN',label='UNKNOWN',reason='IMPLICIT_SOURCE_FORBIDDEN',context=None,actual_route_changes=[])
    binding=state['bindings'].get((module,mode))
    valid=bool(binding and binding.get('accepted') is True and binding.get('module')==module and binding.get('source_mode')==mode)
    if mode=='PRODUCTION_V4':
        valid=valid and set(binding.get('capability_scope',[]))==set(required) and all(binding.get('permission_receipt_digests',{}).get(c)==state['permissions'][c]['receipt_digest'] and binding.get('route_heads',{}).get(c)==state['route_heads'][c] and all(binding.get(k)==state['permissions'][c].get(k) for k in ('model_contract_id','parameter_digest','state_lineage_id')) for c in required)
        if not valid: reason='EXACT_V4_BINDING_CONFLICT'
    if not valid:
        return dict(module=module,mode='UNKNOWN',label='UNKNOWN',reason=reason or 'EXACT_CONTEXT_UNAVAILABLE',context=None,actual_route_changes=[])
    label='PRODUCTION_V4_PROVISIONAL' if mode=='PRODUCTION_V4' else 'SHADOW' if explicit_shadow else 'LEGACY_PRODUCTION'
    if not required and not explicit_shadow: reason='COMPOSITE_OR_DIAGNOSTIC_HAS_NO_AGGREGATE_PERMISSION'
    if not explicit_shadow and required and not all(permitted(c,state) for c in required): reason='NO_PERMISSION'
    return dict(module=module,mode=mode,label=label,reason=reason,context=deepcopy(binding),context_digest=digest(binding),actual_route_changes=[])


def page_context(components,aggregate_label=None):
    if aggregate_label=='V4_PRODUCTION': return dict(status='REJECTED_GLOBAL_LABEL',actual_route_changes=[])
    manifest={row['module']:dict(mode=row['mode'],label=row['label'],context_digest=row.get('context_digest'),context=row['context']) for row in components}
    return dict(status='DESIGN_ONLY',manifest=manifest,page_token='design-page-'+digest(manifest),actual_route_changes=[])


def open_deep_link(link):
    context=link['context']
    fields=('module','trade_date','source_mode','publication_id','publication_revision','capability_scope','permission_receipt_digests')
    if context.get('accepted') is not True or context.get('source_mode') not in ('LEGACY_PRODUCTION','PRODUCTION_V4','SHADOW_V4') or any(f not in context for f in fields) or digest(context)!=link.get('context_digest'):
        return dict(status='EXACT_CONTEXT_UNAVAILABLE',context=None,write_allowed=False)
    return dict(status='HISTORICAL_EXACT_READ_ONLY',context=deepcopy(context),write_allowed=False)


def focus_write(row,state,endpoint):
    if row['mode']=='SHADOW_V4' or not row.get('context'): return False
    if row['mode']=='LEGACY_PRODUCTION': return endpoint.get('legacy_authority') is True and endpoint.get('legacy_route_head')==row['context']['legacy_route_head']
    context=row['context']; caps=context['capability_scope']
    if not caps: return False
    return bool(endpoint.get('accepted') is True and endpoint.get('source_mode')=='PRODUCTION_V4' and endpoint.get('context_digest')==row['context_digest'] and all(endpoint.get(k)==context.get(k) for k in ('model_contract_id','parameter_digest','state_lineage_id')) and set(endpoint.get('capability_scope',[]))==set(caps) and all(permitted(c,state) and state['focus_routes'][c]['accepted'] is True and state['focus_routes'][c]['source_mode']=='PRODUCTION_V4' and context['route_heads'][c]==state['focus_routes'][c]['route_head']==state['route_heads'][c]==endpoint.get('route_heads',{}).get(c) and context['permission_receipt_digests'][c]==state['permissions'][c]['receipt_digest']==endpoint.get('permission_receipt_digests',{}).get(c) for c in caps))


def affected(cap):
    result={cap}
    while True:
        update=result|{c for c,deps in DEPS.items() if result.intersection(deps)}
        if update==result: return sorted(result)
        result=update


def stale(context,state):
    return any(not permitted(c,state) or context.get('route_heads',{}).get(c)!=state['route_heads'][c] or context.get('permission_receipt_digests',{}).get(c)!=(state['permissions'].get(c) or {}).get('receipt_digest') for c in context.get('capability_scope',[]))


def fixture(enabled=()):
    state=dict(evidence_origin='CONTRACT_DESIGN_SIMULATION',permissions={},route_heads={c:'SIM_ROUTE_1' for c in CAPS},focus_routes={c:dict(accepted=True,source_mode='PRODUCTION_V4' if c in enabled else 'LEGACY_PRODUCTION',route_head='SIM_ROUTE_1') for c in CAPS},bindings={},user_pins=[dict(user_pin_id='SIM_PIN',owner='SIM_USER',revision=1)])
    identity=dict(model_contract_id='SIM_MODEL',parameter_digest='SIM_PARAMETERS',state_lineage_id='SIM_LINEAGE')
    for c in CAPS: state['permissions'][c]=dict(identity,permission=c in enabled,accepted=True,active=True,receipt_digest='SIM_PERMISSION_'+c)
    for module,(required,_) in MODULES.items():
        for mode in ('LEGACY_PRODUCTION','PRODUCTION_V4','SHADOW_V4'):
            state['bindings'][module,mode]=dict(identity,module=module,trade_date='SIM_DATE',source_mode=mode,namespace=mode,publication_id='SIM_PUBLICATION_'+module+'_'+mode,publication_revision=1,capability_scope=required,permission_receipt_digests={c:state['permissions'][c]['receipt_digest'] for c in required},route_heads={c:state['route_heads'][c] for c in required},legacy_route_head='SIM_LEGACY_HEAD',native_context_digest='SIM_NATIVE_DIGEST',accepted=True)
    return state


def vector_result(index):
    s=fixture()
    if index in (2,7,8,9,10,12,15,16): s=fixture(['STOCK_CORE'])
    if index in (3,5): s=fixture(['SECTOR_STAGE'])
    if index==4: s=fixture(['STOCK_CORE','STOCK_SECTOR_DEPENDENT'])
    if index in (17,18,19): s=fixture(CAPS)
    if index==7: s['permissions']['STOCK_CORE']['active']=False
    if index==8: s['bindings']['stock_research','PRODUCTION_V4']['capability_scope']=['SECTOR_STAGE']
    if index==20: s['permissions']['STOCK_CORE']['permission']='UNKNOWN'
    extra={}
    if index in (9,16):
        old=resolve('stock_research',s); s['route_heads']['STOCK_CORE']='SIM_ROUTE_2'
        extra=dict(stale=stale(old['context'],s),session_write_allowed=False,cache_action='INVALIDATE_AFFECTED_BINDING_NO_SILENT_REBASE')
    if index==10:
        old=resolve('stock_research',s); link=dict(context=old['context'],context_digest=old['context_digest']); s['route_heads']['STOCK_CORE']='SIM_ROUTE_2'
        extra=dict(deep_link=open_deep_link(link),original_context_digest=old['context_digest'])
    if index==11: s['discovery']='latest'
    rows={m:resolve(m,s,explicit_shadow=index in (6,14)) for m in MODULES}
    if index==12: extra['page']=page_context(list(rows.values()))
    if index==13: extra['page']=page_context(list(rows.values()),'V4_PRODUCTION')
    if index==14: extra['focus_write_allowed']=focus_write(rows['stock_research'],s,dict(accepted=True))
    if index==15: extra['user_pins_preserved']=s['user_pins']==fixture()['user_pins']
    if index in (17,18,19):
        caps=affected('ROTATION' if index==17 else 'SECTOR_STAGE')
        for c in caps: s['permissions'][c]['permission']=False
        rows={m:resolve(m,s) for m in MODULES}
        extra.update(rollback_affected=caps,user_pins_preserved=True,historical_context_preserved=True)
    return dict(kind='DESIGN_SIMULATION_ONLY',modules=rows,actual_default_cutover=False,actual_route_changes=[],production_grant=False,**extra)
