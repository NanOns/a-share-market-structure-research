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

def date_valid_identity(identity,day):
    return bool(identity and identity.get('security_id') and identity.get('list_date') and identity['list_date']<=day and (not identity.get('delist_date') or day<identity['delist_date']))

def ref(root,path):
    p=Path(path).resolve();return dict(path=p.relative_to(Path(root).resolve()).as_posix(),sha256=sha(p),bytes=p.stat().st_size)

def checked(root,binding):
    p=(Path(root)/binding['path']).resolve()
    if not p.is_relative_to(Path(root).resolve()) or not p.is_file() or sha(p)!=binding['sha256']:
        raise ValueError('R43_SOURCE_DIGEST_MISMATCH:'+binding['path'])
    return p

def run_sources(root,out,dates,*,source_manifest_path):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    dates=sorted(set(dates))
    if len(dates)!=4 or any(not isinstance(day,str) or len(day)!=10 for day in dates):
        raise ValueError('FOUR_SESSION_SOURCE_SCOPE_REQUIRED')
    now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    existing=out/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json'
    if existing.is_file():
        # Replay the immutable source revision under its original freeze time;
        # execution times belong to run ledgers and must not mint new source IDs.
        now=json.loads(existing.read_bytes())['observed_at']
    source_manifest_path=Path(source_manifest_path)
    if not source_manifest_path.is_absolute():source_manifest_path=root/source_manifest_path
    if not source_manifest_path.is_file():raise ValueError('SOURCE_MANIFEST_REQUIRED')
    sources=json.loads(source_manifest_path.read_bytes())
    available=sorted({q.get('params',{}).get('date') for q in sources.get('query_receipts',[])
                      if q.get('method')=='query_daily_history_k_AStock' and q.get('params',{}).get('date')})
    if dates!=available:raise ValueError('SOURCE_MANIFEST_DATE_SCOPE_MISMATCH')
    old=source_manifest_path.parent
    typed_receipt_path=Path(sources.get('typed_receipt_path',''))
    if not typed_receipt_path.is_absolute():typed_receipt_path=root/typed_receipt_path
    if not typed_receipt_path.is_file():raise ValueError('TYPED_RECEIPT_BINDING_REQUIRED')
    typed_receipt=json.loads(typed_receipt_path.read_bytes())
    if typed_receipt.get('acceptance')!='PASS_TYPED_A_STOCK_SCOPE':raise ValueError('TYPED_RUNTIME_RECEIPT_NOT_ACCEPTED')
    frozen=checked(root,sources['sources']['gbbq'])
    runtime_contract_path=Path(sources.get('runtime_contract_path',''))
    if not runtime_contract_path.is_absolute():runtime_contract_path=root/runtime_contract_path
    if not runtime_contract_path.is_file():raise ValueError('READ_ONLY_SOURCE_ROOT_CONTRACT_REQUIRED')
    runtime_contract=json.loads(runtime_contract_path.read_bytes())
    roots=runtime_contract.get('read_only_tdx_roots')
    if not isinstance(roots,list) or not roots:raise ValueError('READ_ONLY_SOURCE_ROOT_CONTRACT_REQUIRED')
    actual=Path(roots[0])/'T0002/hq_cache/gbbq'
    if not actual.is_file():raise ValueError('ACTUAL_GBBQ_PATH_UNAVAILABLE:'+str(actual))
    if sha(actual)!=sha(frozen):raise ValueError('GBBQ_CHANGED_REQUIRES_NEW_CORRECTED_OWNER_REVISION')
    events=read_gbbq(frozen)
    classification=Path(sources.get('price_impact_classification_path',''))
    if not classification.is_absolute():classification=root/classification
    if not classification.is_file():raise ValueError('PRICE_IMPACT_CLASSIFICATION_BINDING_REQUIRED')
    identity=json.loads(checked(root,sources['sources']['identity']).read_bytes())['rows']
    bycode={r.get('source_security_key',r.get('symbol','')).upper():r for r in identity if r.get('security_id')}
    acceptance_path=Path(sources.get('canonical_acceptance_path',''))
    if not acceptance_path.is_absolute():acceptance_path=root/acceptance_path
    if not acceptance_path.is_file():raise ValueError('CANONICAL_ACCEPTANCE_BINDING_REQUIRED')
    acceptance=acceptance_path
    stage=root/json.loads(acceptance.read_bytes())['evidence']['manifest']['path']
    components=json.loads(stage.read_bytes())['components']
    results=[]
    for day in dates:
        query=next(q for q in sources['query_receipts'] if q['method']=='query_daily_history_k_AStock' and q['params'].get('date')==day)
        qpath=Path(query['path']).resolve()
        if not qpath.is_relative_to(root.resolve()):raise ValueError('QUERY_SOURCE_OUTSIDE_PROJECT')
        payload=json.loads(qpath.read_bytes());rows=payload['rows']
        response_digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        if response_digest!=query['hash'] or payload['hash']!=query['hash'] or payload['params']!=query['params'] or payload['method']!=query['method']:
            raise ValueError('DATED_QUERY_RESPONSE_DIGEST_MISMATCH')
        if not rows or any(r['date']!=day for r in rows):raise ValueError('DATED_BAOSTOCK_ROWS_REQUIRED')
        delta_root=Path(sources.get('typed_delta_root',''))
        if not delta_root.is_absolute():delta_root=root/delta_root
        delta=delta_root/day/'delta_v2.json'
        typed=json.loads(delta.read_bytes());bars={r['security_id']:r for r in typed['target_bars']}
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
        value=dict(contract_id='R43_CORRECTED_LIFECYCLE_V1',trade_date=day,status='READY_WITH_EXPLICIT_UNKNOWN' if unknown else 'READY',observed_at=now,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,PIT_ELIGIBLE=False,source_rows=lifecycle,active_security_ids=[r['security_id'] for r in lifecycle if r['security_id']],identity= sources['sources']['identity'],baostock=ref(root,qpath),typed_delta=ref(root,delta),unknown_source_keys=unknown)
        path=out/'sources'/day/'lifecycle.json';atomic(path,canonical(value))
        snapshot=dict(contract_id='CURRENT_LIFECYCLE_SNAPSHOT_V1',status='READY',trade_date=day,artifact_path=path.relative_to(root).as_posix(),artifact_sha256=sha(path),source_revision=sha(qpath),active_security_ids=value['active_security_ids'])
        special=build_special_phase_source_manifest(trade_date=day,project_root=root,v402_external_acceptance_path=acceptance,v402_stage_manifest_path=stage,event_store_path=root/components['R6_EVENTS']['path'],policy_path=root/components['R6_POLICY']['path'],lifecycle_snapshot=snapshot,observed_at=now,tdx_root=Path(roots[0]))
        special.update(contract_id='R43_CORRECTED_SPECIAL_PHASE_V1',AS_RECORDED=False,PIT_ELIGIBLE=False,knowledge_lineage='RECONSTRUCTED_CORRECTED')
        spath=out/'sources'/day/'special_phase.json';atomic(spath,canonical(special))
        results.append(dict(trade_date=day,typed_delta=ref(root,delta),bars=len(bars),baostock=ref(root,qpath),request_status='NOOP_SOURCE_ALREADY_FROZEN',request_count_this_run=0,original_requested_at=query['requested_at'],original_received_at=query['received_at'],lifecycle=ref(root,path),special_phase=ref(root,spath),suspended_no_bar=suspended,missing_bar_not_confirmed_suspended=missing,identity_unknown=unknown))
    receipt=dict(contract_id='R43_CORRECTED_SOURCE_CHAIN_V1',observed_at=now,GBBQ=dict(actual_read_path=str(actual),actual_sha256=sha(actual),frozen=ref(root,frozen),classification=ref(root,classification),record_count=len(events),category_counts=dict(Counter(str(e.category) for e in events)),price_events_by_date={d:sum(e.category==1 and e.event_date==int(d.replace('-','')) for e in events) for d in dates},optional_map_path=str(actual.with_suffix('.map')),optional_map_present=actual.with_suffix('.map').is_file(),optional_map_required_for_binary_decoder=False),dates=results,TDX_root_write_count=0,AS_RECORDED=False,strict_PIT_permission=False)
    atomic(out/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json',canonical(receipt))
    return receipt
