"""Dated zero-change factor acceptance; never invent a provider response date."""
from pathlib import Path
import json
from .baostock_runtime_acceptance import canonical_sha256,load_runtime_acceptance_manifest,runtime_acceptance_error
from .r43_owner_replay import checked,ref
from .operational_daily_storage_v1 import atomic_json
from .tdx_official_daily_source import sha256_file

CONTRACT='OPERATIONAL_BAOSTOCK_RUNTIME_ZERO_CHANGE_V2'


def error(manifest,*,sdk,auth_mode):
    if manifest.get('contract_id')!=CONTRACT:return runtime_acceptance_error(manifest,sdk=sdk,auth_mode=auth_mode)
    material=dict(manifest);supplied=material.pop('manifest_sha256',None)
    if supplied!=canonical_sha256(material) or manifest.get('status')!='ACCEPTED':return 'V2_RUNTIME_DIGEST_OR_STATUS_INVALID'
    if manifest.get('auth_mode')!=auth_mode or any(manifest['runtime'].get(k)!=sdk.get(k) for k in ('package','version','installed_python_sources_sha256')):
        return 'V2_RUNTIME_SDK_OR_AUTH_MISMATCH'
    smoke=manifest['live_smoke'];target=smoke['target_date']
    if smoke['status']!='PASS' or smoke['daily'].get('provider_date')!=target:return 'V2_DATED_DAILY_SMOKE_REQUIRED'
    factor=smoke['adjustment_factor']
    from .baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD
    if smoke['daily'].get('method')!=DAILY_METHOD or factor.get('method')!=FACTOR_METHOD:return 'V2_METHOD_SCOPE_INVALID'
    if factor.get('row_count')!=0 or factor.get('provider_date') is not None or factor.get('no_change_target_session')!=target:
        return 'V2_ZERO_CHANGE_SCOPE_INVALID'
    if not factor.get('no_change_proof'):return 'V2_ZERO_CHANGE_PROOF_MISSING'
    return None


def load(path,*,project_root):
    path=Path(path);manifest=json.loads(path.read_bytes())
    if manifest.get('contract_id')!=CONTRACT:return load_runtime_acceptance_manifest(path,project_root=project_root)
    receipt=json.loads(checked(project_root,manifest['smoke_receipt']).read_bytes())
    if receipt.get('status')!='PASS' or receipt.get('live_smoke')!=manifest['live_smoke'] or receipt.get('runtime')!=manifest['runtime']:
        raise ValueError('V2_REAL_SMOKE_RECEIPT_MISMATCH')
    proof=json.loads(checked(project_root,manifest['live_smoke']['adjustment_factor']['no_change_proof']).read_bytes())
    target=manifest['live_smoke']['target_date']
    if proof.get('acceptance')!='VERIFIED_ALL_TARGET_UNIVERSE_NO_CHANGE' or proof['target_session']!=target:
        raise ValueError('V2_NO_CHANGE_PROOF_NOT_VERIFIED')
    if set(proof['queried_codes'])!=set(proof['target_universe_codes']):raise ValueError('V2_NO_CHANGE_UNIVERSE_COVERAGE')
    response_codes=[]
    for record in proof['responses']:
        payload=json.loads(checked(project_root,record).read_bytes())
        response_codes.append(payload['code'])
        if payload['rows'] or payload['params']!={'code':payload['code'],'start_date':target,'end_date':target} or payload['metadata']['error_code']!='0':
            raise ValueError('V2_ZERO_CHANGE_RESPONSE_NOT_EXACT')
        if any(payload.get('sdk',{}).get(key)!=manifest['runtime'].get(key) for key in ('package','version','installed_python_sources_sha256')):
            raise ValueError('V2_ZERO_CHANGE_RESPONSE_SDK_MISMATCH')
    if len(response_codes)!=len(set(response_codes)) or set(response_codes)!=set(proof['target_universe_codes']):
        raise ValueError('V2_NO_CHANGE_RESPONSE_COVERAGE')
    return manifest


def prove_no_change(root,target,daily,client,sdk):
    from datetime import datetime,timezone
    root=Path(root);codes=sorted({r['code'].lower() for r in daily})
    if len(codes)!=len(daily) or not 1<=len(codes)<=8000:raise ValueError('NO_CHANGE_TARGET_UNIVERSE_INVALID')
    folder=root/'data/v4/dynamic_daily_sources/no_change'/target/sdk['installed_python_sources_sha256']
    responses=[]
    for code in codes:
        path=folder/(code+'.json')
        if path.is_file():payload=json.loads(path.read_bytes())
        else:
            params=dict(code=code,start_date=target,end_date=target)
            requested=datetime.now(timezone.utc).isoformat()
            rows,metadata=client.query_rows('dynamic_no_change_factor_probe','query_adjust_factor',**params,max_rows=100,max_pages=1)
            if rows:raise ValueError('EMPTY_BATCH_CONTRADICTS_TARGET_FACTOR_RESPONSE')
            if metadata.get('error_code')!='0' or not {'code','dividOperateDate','foreAdjustFactor','backAdjustFactor'}<=set(metadata['fields']):
                raise ValueError('NO_CHANGE_FACTOR_RESPONSE_SCHEMA_UNVERIFIED')
            payload=dict(contract_id='TARGET_FACTOR_NO_CHANGE_RESPONSE_V1',code=code,params=params,rows=rows,metadata=metadata,
                         sdk=sdk,requested_at=requested,received_at=datetime.now(timezone.utc).isoformat(),AS_RECORDED=False)
            atomic_json(root,path,payload)
        if payload['rows'] or payload['params']!=dict(code=code,start_date=target,end_date=target) or payload['sdk']!=sdk or payload['metadata'].get('error_code')!='0':
            raise ValueError('NO_CHANGE_CACHE_SCOPE_MISMATCH')
        responses.append(ref(root,path))
    path=folder/'NO_CHANGE_PROOF.json'
    atomic_json(root,path,dict(contract_id='ALL_TARGET_UNIVERSE_FACTOR_NO_CHANGE_PROOF_V1',target_session=target,
        target_universe_codes=codes,queried_codes=codes,responses=responses,acceptance='VERIFIED_ALL_TARGET_UNIVERSE_NO_CHANGE',
        response_date_not_synthesized=True,AS_RECORDED=False,PIT_ELIGIBLE=False))
    return ref(root,path)
