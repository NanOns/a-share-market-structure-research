"""Small immutable PG corrections over preserved dated history versions."""
import json
from pathlib import Path
from copy import deepcopy
from .v4_native import configured_dsn,workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore,canonical,digest,CONTRACT as STORE
from workbench_analysis.r43_owner_replay import checked

CONTRACT='V4_PG_DATED_HISTORY_QFQ_CORRECTIONS_R2'
FOLDER='data/v4/chart_price_corrections_v2'

def validate(payload):
    if payload.get('contract_id')!=CONTRACT or payload.get('PIT_ELIGIBLE') is not False or payload.get('AS_RECORDED') is not False:
        raise ValueError('HISTORY_CORRECTIONS_CONTRACT_REQUIRED')
    if payload['base'].get('contract_id')!='V4_PG_DATED_HISTORY_INDEX_R1' or payload['base']['T0']!=payload['T0']:
        raise ValueError('HISTORY_CORRECTIONS_BASE_SCOPE')
    keys=set()
    for row in payload['corrections']:
        key=row['security_id'],row['trade_date']
        if key in keys or row['trade_date']>payload['T0']:raise ValueError('HISTORY_CORRECTIONS_DUPLICATE_OR_FUTURE')
        keys.add(key)
        if any(value is not None and (not isinstance(value,list) or len(value)!=4) for value in (row['previous'],row['current'])):
            raise ValueError('HISTORY_CORRECTIONS_OHLC_SHAPE')
    return payload

def prepare(root,base,corrections,source_bindings):
    payload=validate(dict(contract_id=CONTRACT,T0=base['T0'],base=base,corrections=corrections,source_bindings=source_bindings,PIT_ELIGIBLE=False,AS_RECORDED=False))
    for binding in source_bindings.values():checked(root,binding)
    descriptor=ForwardFactStore(root,FOLDER).append('qfq_corrections',digest(canonical(payload)),payload)
    return dict(contract_id=CONTRACT,engine='postgresql',T0=base['T0'],head_token=base['head_token'],base=base,corrections=descriptor,
        source_digest=digest(canonical(source_bindings)),price_basis='EXACT_HALF_UP_QFQ_WITH_PRESERVED_DATED_SOURCE_COVERAGE')

def read(root,binding,day,sid):
    if binding.get('contract_id')!=CONTRACT or binding.get('engine')!='postgresql' or binding.get('T0')!=day:
        raise ValueError('HISTORY_CORRECTIONS_READ_SCOPE')
    root=Path(root).resolve();folder=root/FOLDER;descriptor_binding=binding['corrections']
    path=checked(root,descriptor_binding)
    if not path.resolve().is_relative_to(folder) or not path.name.endswith('.pg.json'):raise ValueError('HISTORY_CORRECTIONS_PG_REQUIRED_NO_FALLBACK')
    descriptor=json.loads(path.read_bytes())
    if descriptor.get('contract_id')!=STORE or descriptor.get('engine')!='postgresql' or descriptor.get('schema')!=workspace_schema(folder,'forward') or descriptor.get('kind')!='qfq_corrections':
        raise ValueError('HISTORY_CORRECTIONS_DESCRIPTOR_SCOPE')
    store=ForwardFactStore.__new__(ForwardFactStore);store.root=root;store.folder=folder;store.schema=descriptor['schema']
    store.database_identity=descriptor['database_identity'];store.dsn=configured_dsn()
    payload=validate(store.read(descriptor_binding))
    if payload['base']!=binding['base'] or payload['T0']!=day or digest(canonical(payload['source_bindings']))!=binding['source_digest']:
        raise ValueError('HISTORY_CORRECTIONS_SOURCE_MISMATCH')
    for source in payload['source_bindings'].values():checked(root,source)
    from .v4_history_pg_r1 import read as base_read
    bars=base_read(root,binding['base'],day,sid)
    if bars is None:return None
    bars=deepcopy(bars);bydate={bar['trade_date']:bar for bar in bars}
    for row in payload['corrections']:
        if row['security_id']!=sid:continue
        bar=bydate.get(row['trade_date'])
        if bar is None or bar.get('qfq_ohlc')!=row['previous']:raise ValueError('HISTORY_CORRECTIONS_PREDECESSOR_VALUE_MISMATCH')
        bar['qfq_ohlc']=row['current']
    return bars
