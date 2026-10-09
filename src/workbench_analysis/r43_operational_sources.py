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

def date_valid_identity(identity,day):
    return bool(identity and identity.get('security_id') and identity.get('list_date') and identity['list_date']<=day and (not identity.get('delist_date') or day<identity['delist_date']))

def ref(root,path):
    p=Path(path).resolve();return dict(path=p.relative_to(Path(root).resolve()).as_posix(),sha256=sha(p),bytes=p.stat().st_size)

def checked(root,binding):
    p=(Path(root)/binding['path']).resolve()
    if not p.is_relative_to(Path(root).resolve()) or not p.is_file() or sha(p)!=binding['sha256']:
        raise ValueError('R43_SOURCE_DIGEST_MISMATCH:'+binding['path'])
    return p

def run_sources(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    existing=out/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json'
    if existing.is_file():
        # Replay the immutable source revision under its original freeze time;
        # execution times belong to run ledgers and must not mint new source IDs.
        now=json.loads(existing.read_bytes())['observed_at']
    old=root/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1'
    sources=json.loads((old/'SOURCE_BINDINGS.json').read_bytes())
    typed_receipt=json.loads((root/'docs/evidence/r4_2_1_20261009/TDX_A_STOCK_DELTA_V2_RUNTIME_RECEIPT.json').read_bytes())
    if typed_receipt.get('acceptance')!='PASS_TYPED_A_STOCK_SCOPE':raise ValueError('TYPED_RUNTIME_RECEIPT_NOT_ACCEPTED')
    frozen=checked(root,sources['sources']['gbbq'])
    actual=Path('D:/new_tdx/T0002/hq_cache/gbbq')
    if not actual.is_file():raise ValueError('ACTUAL_GBBQ_PATH_UNAVAILABLE:'+str(actual))
    if sha(actual)!=sha(frozen):raise ValueError('GBBQ_CHANGED_REQUIRES_NEW_CORRECTED_OWNER_REVISION')
    events=read_gbbq(frozen)
    classification=root/'config/v4_02_gbbq_price_impact_classification_v1.json'
    identity=json.loads(checked(root,sources['sources']['identity']).read_bytes())['rows']
    bycode={r.get('source_security_key',r.get('symbol','')).upper():r for r in identity if r.get('security_id')}
    acceptance=root/'reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json'
    stage=root/json.loads(acceptance.read_bytes())['evidence']['manifest']['path']
    components=json.loads(stage.read_bytes())['components']
    results=[]
    for day in DATES:
        query=next(q for q in sources['query_receipts'] if q['method']=='query_daily_history_k_AStock' and q['params'].get('date')==day)
        qpath=Path(query['path']).resolve()
        if not qpath.is_relative_to(root.resolve()):raise ValueError('QUERY_SOURCE_OUTSIDE_PROJECT')
        payload=json.loads(qpath.read_bytes());rows=payload['rows']
        response_digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        if response_digest!=query['hash'] or payload['hash']!=query['hash'] or payload['params']!=query['params'] or payload['method']!=query['method']:
            raise ValueError('DATED_QUERY_RESPONSE_DIGEST_MISMATCH')
        if not rows or any(r['date']!=day for r in rows):raise ValueError('DATED_BAOSTOCK_ROWS_REQUIRED')
        delta=root/'docs/evidence/r4_2_1_20261009/typed_delta'/day/'delta_v2.json'
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
        special=build_special_phase_source_manifest(trade_date=day,project_root=root,v402_external_acceptance_path=acceptance,v402_stage_manifest_path=stage,event_store_path=root/components['R6_EVENTS']['path'],policy_path=root/components['R6_POLICY']['path'],lifecycle_snapshot=snapshot,observed_at=now,tdx_root=Path('D:/new_tdx'))
        special.update(contract_id='R43_CORRECTED_SPECIAL_PHASE_V1',AS_RECORDED=False,PIT_ELIGIBLE=False,knowledge_lineage='RECONSTRUCTED_CORRECTED')
        spath=out/'sources'/day/'special_phase.json';atomic(spath,canonical(special))
        results.append(dict(trade_date=day,typed_delta=ref(root,delta),bars=len(bars),baostock=ref(root,qpath),request_status='NOOP_SOURCE_ALREADY_FROZEN',request_count_this_run=0,original_requested_at=query['requested_at'],original_received_at=query['received_at'],lifecycle=ref(root,path),special_phase=ref(root,spath),suspended_no_bar=suspended,missing_bar_not_confirmed_suspended=missing,identity_unknown=unknown))
    receipt=dict(contract_id='R43_CORRECTED_SOURCE_CHAIN_V1',observed_at=now,GBBQ=dict(actual_read_path=str(actual),actual_sha256=sha(actual),frozen=ref(root,frozen),classification=ref(root,classification),record_count=len(events),category_counts=dict(Counter(str(e.category) for e in events)),price_events_by_date={d:sum(e.category==1 and e.event_date==int(d.replace('-','')) for e in events) for d in DATES},optional_map_path=str(actual.with_suffix('.map')),optional_map_present=actual.with_suffix('.map').is_file(),optional_map_required_for_binary_decoder=False),dates=results,TDX_root_write_count=0,AS_RECORDED=False,strict_PIT_permission=False)
    atomic(out/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json',canonical(receipt))
    return receipt
