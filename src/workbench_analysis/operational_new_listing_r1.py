"""Append-only current-day IPO identity adapter; frozen predecessors stay intact."""
from pathlib import Path
from datetime import datetime,timezone,date
from types import SimpleNamespace
import json
from .r43_owner_replay import checked,ref,load
from .tdx_official_daily_source import sha256_file,sha256_bytes,_json_bytes
from .operational_daily_storage_v1 import atomic_json
from .operational_owner_adapter_v1 import private_scope
from .security_entity_identity import stable_security_id

CONTRACT='V4_CURRENT_OPERATIONAL_NEW_LISTING_R1'
PATH='config/v4_operational_new_listing_r1.json'

def validate_basic(code,day,rows,existing_ids):
    if len(rows)!=1:raise ValueError('IPO_BASIC_SINGLE_RECORD_REQUIRED')
    row=rows[0]
    if row.get('code','').upper()!=code or row.get('type')!='1' or row.get('status')!='1':
        raise ValueError('IPO_BASIC_CODE_TYPE_STATUS_MISMATCH')
    if row.get('ipoDate')!=day or row.get('outDate'):raise ValueError('IPO_CURRENT_DAY_LISTING_REQUIRED')
    date.fromisoformat(day)
    exchange=code.split('.')[0];number=code.split('.')[1]
    if exchange=='SZ':board='CHINEXT' if number.startswith(('300','301')) else 'SZ_MAIN'
    elif exchange=='SH':board='STAR' if number.startswith(('688','689')) else 'SH_MAIN'
    else:raise ValueError('IPO_UNSUPPORTED_EXCHANGE')
    sid=stable_security_id(exchange,code,day)
    if sid in existing_ids:raise ValueError('IPO_STABLE_ID_COLLISION')
    return dict(source_security_key=code,security_id=sid,exchange=exchange,symbol=code,
        list_date=day,delist_date=None,board_scope=board,security_type='A_STOCK',
        name=row.get('code_name'),identity_status='IDENTITY_BOUND',trade_date=day,
        knowledge_lineage='CURRENT_DATED_OPERATIONAL_PROVIDER_FACT',AS_RECORDED=False,
        PIT_ELIGIBLE=False,absence_is_delisting_evidence=False,bao_daily_row_is_identity_authority=False)

def admitted_identity(root,day,gate,freeze):
    root=Path(root);contract=load(root/PATH)
    if contract.get('contract_id')!=CONTRACT or contract.get('full_product_release') is not False:
        raise ValueError('IPO_OPERATIONAL_SCOPE_CONTRACT_REQUIRED')
    deps=gate['dependency_bindings'];adds=deps['unknown_codes']
    if deps['missing_codes']:raise ValueError('IPO_ADAPTER_CANNOT_INFER_DELISTING')
    if len(adds)>contract['max_new_listings_per_session']:raise ValueError('IPO_REQUEST_BOUND_EXCEEDED')
    facts=gate['native_provider_facts']
    if facts['status']!='NATIVE_PROVIDERS_RECONCILED':raise ValueError('IPO_NATIVE_FACTS_NOT_RECONCILED')
    previous=load(checked(root,deps['identity']));ids={r['security_id'] for r in previous['rows']}
    daily={r['code'].upper():r for r in freeze['normalized']['daily']['rows']}
    folder=root/'data/v4/dynamic_daily_sources/new_listing_r1'/day
    evidence=[];new=[]
    from .baostock_supplemental import RequestBudget
    from .operational_baostock_client_v1 import BaoStockClient
    from .operational_runtime_acceptance_v2 import load as runtime_manifest
    manifest=runtime_manifest(checked(root,freeze['runtime_manifest']),project_root=root)
    pending=[code for code in adds if not (folder/(code+'.json')).is_file()]
    if pending:
        with BaoStockClient(RequestBudget(root/'reports/v4_baostock/request_ledger.json'),auth_mode=manifest['auth_mode'],runtime_acceptance_manifest=manifest) as client:
            for code in pending:
                started=datetime.now(timezone.utc).isoformat()
                rows,metadata=client.query_rows('operational_new_listing_basic','query_stock_basic',code=code.lower(),max_rows=2,max_pages=1)
                if metadata['error_code']!='0':raise ValueError('IPO_BASIC_PROVIDER_NOT_READY')
                validate_basic(code,day,rows,ids)
                atomic_json(root,folder/(code+'.json'),dict(contract_id=CONTRACT,target_session=day,code=code,rows=rows,metadata=metadata,requested_at=started,received_at=datetime.now(timezone.utc).isoformat()))
    for code in adds:
        if daily[code]['tradestatus']!='1':raise ValueError('IPO_NATIVE_ACTIVE_BAR_REQUIRED')
        p=folder/(code+'.json');record=load(p)
        if record['target_session']!=day or record['code']!=code:raise ValueError('IPO_CACHE_DATE_CODE_MISMATCH')
        row=validate_basic(code,day,record['rows'],ids);row['source_binding']=ref(root,p)
        row['knowledge_time']=record['received_at'];new.append(row);ids.add(row['security_id']);evidence.append(ref(root,p))
    document=dict(previous,contract_id=CONTRACT,trade_date=day,predecessor_identity=deps['identity'],
        rows=previous['rows']+new,new_listings=new,provider_evidence=evidence,policy=ref(root,root/PATH),
        roster_source=freeze['native_baostock'],native_source=freeze['tdx'],full_product_release=False,PIT_ELIGIBLE=False,AS_RECORDED=False)
    key=sha256_bytes(_json_bytes(document));p=folder/'identities'/key/'IDENTITY.json'
    if not p.exists():atomic_json(root,p,document)
    return ref(root,p)

def gate_adapter(original,root,day,artifact,result,now=None):
    result,gate=original(root,day,artifact,result,now)
    if gate['status']!='WAIT_DATED_IDENTITY_AUTHORITY' or not gate['dependency_bindings'].get('unknown_codes'):return result,gate
    identity=admitted_identity(root,day,gate,artifact)
    from .source_readiness_v2 import source_readiness
    sources=dict(gate['sources']);old=sources.pop('dated_identity_authority')
    readiness=source_readiness(day,now or datetime.now(timezone.utc),sources)
    deps=dict(gate['dependency_bindings'],identity=identity,predecessor_identity=gate['dependency_bindings']['identity'],
        new_listing_identity=identity,accepted_pool_count=len(load(checked(root,identity))['rows']),
        accepted_pool_sha256=sha256_bytes(_json_bytes(sorted(old['actual_codes']))),
        unknown_codes=[],newly_admitted_codes=sorted(set(old['actual_codes'])-set(old['expected_codes'])))
    readiness.update(source_freeze=result['source_freeze'],dependency_bindings=deps,
        native_provider_facts=gate['native_provider_facts'],AS_RECORDED=False,PIT_ELIGIBLE=False,
        dated_identity_authority=dict(contract_id=CONTRACT,status='CURRENT_DAY_NEW_LISTING_BOUND',identity=identity,predecessor=gate['dependency_bindings']['identity']))
    # New identity participates in every generation/source key. Old readiness
    # is retained; append a new receipt, never replace an accepted source.
    p=Path(root)/'data/v4/dynamic_daily_sources/source_readiness'/day/(sha256_bytes(_json_bytes(readiness))+'.json')
    if not p.exists():atomic_json(root,p,readiness)
    return dict(result,source_readiness=ref(root,p),source_ready=readiness['source_ready']),readiness

def ready_build(root,freeze_binding,**kwargs):
    from . import operational_daily_ready_owner_v2 as ready
    from . import operational_daily_owner_v1 as owner
    from .operational_owner_adapter_v1 import replay
    gate=load(checked(root,kwargs['source_readiness']));identity=gate['dependency_bindings'].get('new_listing_identity')
    if not identity:return ready.build(root,freeze_binding,**kwargs)
    root=Path(root).resolve();parent=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    life=parent['owners'][parent['accepted_trade_date']]['lifecycle'];life_path=checked(root,life)
    overlay=root/'data/v4/dynamic_daily_sources/new_listing_r1'/load(checked(root,freeze_binding))['target_session']/'overlays'/identity['sha256']
    atomic_json(root,overlay/'LIFECYCLE.json',dict(load(life_path),identity=identity))
    data_head=load(root/'data/v4/V4_DATA_ACCEPTED_HEAD.json')
    data_head['component_artifacts']['IDENTITY_UNIVERSE']=identity
    atomic_json(root,overlay/'DATA_HEAD.json',data_head)
    def mapped_load(path):
        return load(overlay/'LIFECYCLE.json') if Path(path).resolve()==life_path.resolve() else load(path)
    prepared=private_scope(owner,dict(load=mapped_load))['prepare']
    def prepare(*args,**kw):
        context=prepared(*args,**kw)
        context['mappings'][str((root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').resolve())]=str(overlay/'DATA_HEAD.json')
        # Identity is date-bounded: replay excludes this listing before IPO day.
        return context
    proxy=SimpleNamespace(**vars(owner));proxy.prepare=prepare
    return private_scope(ready,dict(owner=proxy))['build'](root,freeze_binding,**kwargs)
