"""Date-bounded corrected source adapters; original PIT adapters remain immutable."""
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import hashlib
from .scoped_successor_r421 import sha, canonical, atomic
from .daily_source_manifests import build_special_phase_source_manifest
from tdx.gbbq_reader import read_gbbq

DATES=['2026-09-28','2026-09-29','2026-09-30','2026-10-08']
_SOURCE_IDS={
    'source_bindings':'466173943ad7d3ca1bf1ebb23e236fc86ea35394f70609c8b1603d8493cfbf18',
    'typed_receipt':'81e97c29fa72275c653d09cec6dc37ac89b0b3ea0f38aa456ca81839528fe6ab',
    'acceptance':'56c7b651981895ae533dc1d50924a0b915c55a1543180a0d34460546b72c0adb',
    'typed_delta':{
        '2026-09-28':'526c8158b25faf812f517ffc7957f1fb604f559fc8fe70a28e302e5314c5848e',
        '2026-09-29':'50b381385c92dd43fd26f2ff6e34377f004d724355af01e68cdf6282ff5d14bc',
        '2026-09-30':'85a3505e6ebd2f4514169a55538298fab33cb21243472663b8ba6d064bce61e7',
        '2026-10-08':'7983fc463af682ca709852abcebd14fec2d0395bac7b07fba38601ae134e2379',
    },
}

def date_valid_identity(identity,day):
    return bool(identity and identity.get('security_id') and identity.get('list_date') and identity['list_date']<=day and (not identity.get('delist_date') or day<identity['delist_date']))

def ref(root,path):
    p=Path(path).resolve();return dict(path=p.relative_to(Path(root).resolve()).as_posix(),sha256=sha(p),bytes=p.stat().st_size)

def checked(root,binding):
    """Materialize the exact V4 source binding from PG SourceIngress."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import bound_bytes
    try:
        return bound_bytes(root,binding)
    except ValueError as exc:
        raise ValueError('R43_PG_SOURCE_INGRESS_UNAVAILABLE:'+binding['path']) from exc

def read_source_bytes(root,binding):
    """Read an exact bound input in memory from the shared PG ingress store."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
    source=read_bound(root,binding['path'],binding['sha256'])
    if len(source['raw'])!=binding.get('bytes',len(source['raw'])):
        raise ValueError('R43_PG_SOURCE_INGRESS_SIZE_MISMATCH')
    return source['raw']

def run_sources(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound,read_path
    def historical_fact(path):
        return read_path(root,Path(path).resolve().relative_to(root.resolve()).as_posix())
    def historical_json(source_id):
        from workbench_db.v4_historical_source_ingress_pg_r1 import read_source
        value=read_source(root,source_id)['value']
        if not isinstance(value,dict):raise ValueError('HISTORICAL_PG_JSON_REQUIRED:'+str(source_id))
        return value
    def historical_special_inputs(components):
        event=components['R6_EVENTS'];policy=components['R6_POLICY']
        event_fact=read_bound(root,event['path'],event['sha256'])
        policy_fact=read_bound(root,policy['path'],policy['sha256'])
        records=[json.loads(line) for line in (event_fact['text'] or '').splitlines() if line.strip()]
        contract=policy_fact['value']
        if not isinstance(contract,dict):raise ValueError('SPECIAL_PHASE_POLICY_PG_JSON_REQUIRED')
        return records,contract,event,policy
    from common.paths import resolve_tdx_root
    tdx_root=resolve_tdx_root(root)
    now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    existing=out/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json'
    try:
        previous=historical_fact(existing)['value']
    except ValueError as exc:
        if str(exc) not in {'HISTORICAL_SOURCE_INGRESS_PATH_UNAVAILABLE','HISTORICAL_SOURCE_INGRESS_NOT_FOUND'}:
            raise
    else:
        # Replay the immutable source revision under its original freeze time.
        now=previous['observed_at']
    sources=historical_json(_SOURCE_IDS['source_bindings'])
    typed_receipt=historical_json(_SOURCE_IDS['typed_receipt'])
    if typed_receipt.get('acceptance')!='PASS_TYPED_A_STOCK_SCOPE':raise ValueError('TYPED_RUNTIME_RECEIPT_NOT_ACCEPTED')
    frozen=checked(root,sources['sources']['gbbq'])
    actual=tdx_root/'T0002/hq_cache/gbbq'
    if not actual.is_file():raise ValueError('ACTUAL_GBBQ_PATH_UNAVAILABLE:'+str(actual))
    if sha(actual)!=sha(frozen):raise ValueError('GBBQ_CHANGED_REQUIRES_NEW_CORRECTED_OWNER_REVISION')
    events=read_gbbq(frozen)
    classification=root/'config/v4_02_gbbq_price_impact_classification_v1.json'
    identity=read_bound(root,sources['sources']['identity']['path'],
                        sources['sources']['identity']['sha256'])['value']['rows']
    bycode={r.get('source_security_key',r.get('symbol','')).upper():r for r in identity if r.get('security_id')}
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_source
    acceptance_fact=read_source(root,_SOURCE_IDS['acceptance'])
    acceptance= root/acceptance_fact['record']['source_path']
    acceptance_value=acceptance_fact['value']
    stage=root/acceptance_value['evidence']['manifest']['path']
    stage_value=historical_fact(stage)['value']
    components=stage_value['components']
    event_records,policy_contract,event_binding,policy_binding=historical_special_inputs(components)
    acceptance_source=acceptance_fact['record']
    stage_source=historical_fact(stage)['record']
    results=[]
    for day in DATES:
        query=next(q for q in sources['query_receipts'] if q['method']=='query_daily_history_k_AStock' and q['params'].get('date')==day)
        qpath=Path(query['path']).resolve()
        if not qpath.is_relative_to(root.resolve()):raise ValueError('QUERY_SOURCE_OUTSIDE_PROJECT')
        query_fact=historical_fact(qpath);payload=query_fact['value'];rows=payload['rows']
        response_digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        if response_digest!=query['hash'] or payload['hash']!=query['hash'] or payload['params']!=query['params'] or payload['method']!=query['method']:
            raise ValueError('DATED_QUERY_RESPONSE_DIGEST_MISMATCH')
        if not rows or any(r['date']!=day for r in rows):raise ValueError('DATED_BAOSTOCK_ROWS_REQUIRED')
        delta_fact=read_source(root,_SOURCE_IDS['typed_delta'][day])
        delta=root/delta_fact['record']['source_path']
        typed=delta_fact['value'];bars={r['security_id']:r for r in typed['target_bars']}
        actual_bar_digest=hashlib.sha256(json.dumps(typed['target_bars'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if actual_bar_digest!=typed_receipt['targets'][day]['target_bar_digest'] or typed.get('target_date')!=day or typed.get('current_package_sha256')!=sources['sources']['package']['sha256'] or len(bars)!=len(typed['target_bars']):
            raise ValueError('TYPED_DELTA_TARGET_OR_DIGEST_MISMATCH')
        lifecycle=[];unknown=[];suspended=[];missing=[]
        for r in rows:
            key=r['code'].upper();i=bycode.get(key)
            valid=date_valid_identity(i,day)
            sid=i['security_id'] if valid else None
            if sid is None:unknown.append(key)
            if sid and sid not in bars:
                (suspended if str(r.get('tradestatus'))=='0' else missing).append(key)
            lifecycle.append(dict(security_id=sid,source_security_key=key,trade_date=day,identity_status='IDENTITY_BOUND' if valid else 'IDENTITY_UNKNOWN',reason=None if valid else 'NO_DATE_VALID_ACCEPTED_CANONICAL_IDENTITY',trading_status=r.get('tradestatus'),has_tdx_bar=sid in bars,absence_is_delisting_evidence=False))
        value=dict(contract_id='R43_CORRECTED_LIFECYCLE_V1',trade_date=day,status='READY_WITH_EXPLICIT_UNKNOWN' if unknown else 'READY',observed_at=now,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,PIT_ELIGIBLE=False,source_rows=lifecycle,active_security_ids=[r['security_id'] for r in lifecycle if r['security_id']],identity= sources['sources']['identity'],baostock=dict(path=query_fact['record']['source_path'],sha256=query_fact['record']['source_sha256'],bytes=query_fact['record']['source_bytes']),typed_delta=dict(path=delta_fact['record']['source_path'],sha256=delta_fact['record']['source_sha256'],bytes=delta_fact['record']['source_bytes']),unknown_source_keys=unknown)
        path=out/'sources'/day/'lifecycle.json';atomic(path,canonical(value))
        from workbench_db.v4_dm01_stage_state_pg_r1 import append_stage
        lifecycle_pg_binding=append_stage(root,day,'lifecycle_snapshot',value)
        snapshot=dict(contract_id='CURRENT_LIFECYCLE_SNAPSHOT_V1',status='READY',trade_date=day,artifact_path=path.relative_to(root).as_posix(),artifact_sha256=sha(path),source_revision=sha(qpath),active_security_ids=value['active_security_ids'])
        special=build_special_phase_source_manifest(trade_date=day,project_root=root,v402_external_acceptance_path=acceptance,v402_stage_manifest_path=stage,event_store_path=root/components['R6_EVENTS']['path'],policy_path=root/components['R6_POLICY']['path'],lifecycle_snapshot=snapshot,observed_at=now,tdx_root=tdx_root,event_records=event_records,policy_contract=policy_contract,event_source_binding=event_binding,policy_source_binding=policy_binding,v402_external_acceptance=acceptance_value,v402_stage_manifest=stage_value,v402_source_bindings=dict(contract_id='V4_HISTORICAL_SOURCE_INGRESS_PG_R1',acceptance=dict(path=acceptance_source['source_path'],sha256=acceptance_source['source_sha256']),stage_manifest=dict(path=stage_source['source_path'],sha256=stage_source['source_sha256'])),lifecycle_pg_binding=lifecycle_pg_binding)
        special.update(contract_id='R43_CORRECTED_SPECIAL_PHASE_V1',AS_RECORDED=False,PIT_ELIGIBLE=False,knowledge_lineage='RECONSTRUCTED_CORRECTED')
        spath=out/'sources'/day/'special_phase.json';atomic(spath,canonical(special))
        results.append(dict(trade_date=day,typed_delta=dict(path=delta_fact['record']['source_path'],sha256=delta_fact['record']['source_sha256'],bytes=delta_fact['record']['source_bytes']),bars=len(bars),baostock=dict(path=query_fact['record']['source_path'],sha256=query_fact['record']['source_sha256'],bytes=query_fact['record']['source_bytes']),request_status='NOOP_SOURCE_ALREADY_FROZEN',request_count_this_run=0,original_requested_at=query['requested_at'],original_received_at=query['received_at'],lifecycle=ref(root,path),special_phase=ref(root,spath),suspended_no_bar=suspended,missing_bar_not_confirmed_suspended=missing,identity_unknown=unknown))
    receipt=dict(contract_id='R43_CORRECTED_SOURCE_CHAIN_V1',observed_at=now,GBBQ=dict(actual_read_path=str(actual),actual_sha256=sha(actual),frozen=ref(root,frozen),classification=ref(root,classification),record_count=len(events),category_counts=dict(Counter(str(e.category) for e in events)),price_events_by_date={d:sum(e.category==1 and e.event_date==int(d.replace('-','')) for e in events) for d in DATES},optional_map_path=str(actual.with_suffix('.map')),optional_map_present=actual.with_suffix('.map').is_file(),optional_map_required_for_binary_decoder=False),dates=results,TDX_root_write_count=0,AS_RECORDED=False,strict_PIT_permission=False)
    atomic(out/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json',canonical(receipt))
    return receipt
