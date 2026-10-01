"""Runtime capability is independent of the historical date requested by a capture."""
from __future__ import annotations
from datetime import date,datetime
import hashlib,json
from workbench_analysis.baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,DAILY_REQUIRED_FIELDS,FACTOR_REQUIRED_FIELDS

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def classify_capture_response(record, *, target, required_fields):
    date.fromisoformat(target)
    if record.get('request_count',0)<1:raise ValueError('PROVIDER_NOT_QUERIED')
    times={}
    for field in ['observed_at','received_at']:
        t=datetime.fromisoformat(record[field].replace('Z','+00:00'))
        if t.tzinfo is None or t.date()<date.fromisoformat(target):raise ValueError('CAPTURE_TIME_BACKDATED_OR_UNZONED')
        times[field]=t
    if times['received_at']<times['observed_at']:raise ValueError('CAPTURE_RECEIVED_BEFORE_OBSERVED')
    if record.get('error_code')!='0':return 'HISTORICAL_CATCHUP_QUERY_FAILED'
    if record.get('provider_date')!=target or not set(required_fields)<=set(record.get('fields',[])):return 'PROVIDER_SCHEMA_MISMATCH'
    return 'PROVIDER_TARGET_DATE_EMPTY' if record.get('row_count')==0 else 'AVAILABLE'

def build_capability(sdk,endpoint,smoke,proof):
    if smoke['auth_mode']!='PUBLIC_ANONYMOUS' or not endpoint.get('connected_peer_ip') or endpoint.get('connected_peer_port')!=10030:
        raise ValueError('PUBLIC_RUNTIME_ENDPOINT_NOT_VERIFIED')
    for method,required in [(DAILY_METHOD,DAILY_REQUIRED_FIELDS),(FACTOR_METHOD,FACTOR_REQUIRED_FIELDS)]:
        r=smoke['responses'][method]
        state=classify_capture_response(r,target=smoke['smoke_date'],required_fields=required)
        if state not in ('AVAILABLE','PROVIDER_TARGET_DATE_EMPTY') or (method==DAILY_METHOD and state!='AVAILABLE'):
            raise ValueError('RUNTIME_CAPABILITY_SMOKE_FAILED:'+state)
    payload=dict(contract_id='BAOSTOCK_DM01_RUNTIME_CAPABILITY_V2',version='2.0.0',status='VERIFIED_ENGINEERING_CAPABILITY_EXTERNAL_PENDING',
        sdk={k:sdk[k] for k in ['package','version','installed_python_sources_sha256']},auth_mode='PUBLIC_ANONYMOUS',endpoint=endpoint,
        methods=[DAILY_METHOD,FACTOR_METHOD],schemas={DAILY_METHOD:sorted(DAILY_REQUIRED_FIELDS),FACTOR_METHOD:sorted(FACTOR_REQUIRED_FIELDS)},
        smoke_date=smoke['smoke_date'],smoke_binding=proof,request_budget=dict(maximum_requests=12,maximum_rows_per_method=20000,maximum_pages=1),
        independent_of_target_date=True,external_acceptance=None)
    payload['runtime_capability_id']='BS-CAP-V2:'+digest(payload);return payload

def require_capability(capability,sdk,target):
    date.fromisoformat(target)
    if capability.get('contract_id')!='BAOSTOCK_DM01_RUNTIME_CAPABILITY_V2' or capability.get('status')!='VERIFIED_ENGINEERING_CAPABILITY_EXTERNAL_PENDING':raise ValueError('PROVIDER_RUNTIME_UNACCEPTED')
    material={k:v for k,v in capability.items() if k!='runtime_capability_id'}
    if capability.get('runtime_capability_id')!='BS-CAP-V2:'+digest(material):raise ValueError('RUNTIME_CAPABILITY_ID_INVALID')
    if any(capability['sdk'].get(k)!=sdk.get(k) for k in capability['sdk']):raise ValueError('SDK_HASH_MISMATCH')
    # No equality check between target and smoke date: this is the repaired boundary.
    return capability['runtime_capability_id']
