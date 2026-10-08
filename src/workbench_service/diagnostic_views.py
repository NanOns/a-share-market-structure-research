"""Scoped diagnostic views with bounded public evidence, never credential paths."""
import json
from .domain_views import objects,value

LEGACY=[('领先行业/概念','板块研究背景','/v4/research/sectors'),('当前强势','板块确认状态','/v4/research/sectors'),('早期启动/结构突破','WARM 诊断','/v4/research/diagnostics/legacy'),('预观察板块/个股','V4 PREWATCH','/v4/research/stocks?maturity=PREWATCH'),('V3.3 候选','当日确认变化','/v4/research/home'),('创新高/RPS','个股技术画像','/v4/research/stocks'),('RPS/周期矩阵','字段与历史能力诊断','/v4/research/diagnostics/fields')]
def diagnostic(reader,part):
    m=reader.manifest
    if part=='health':
        rows=[]
        for domain in ('stocks','sectors','focus','forward','market'):
            data=objects(reader,domain);quality={};unknown={}
            for item in data:
                for key,cell in item['fields'].items():
                    q=cell.get('quality','UNKNOWN');quality[q]=quality.get(q,0)+1
                    if q=='UNKNOWN':unknown[key]=unknown.get(key,0)+1
            rows.append(dict(module=domain,record_count=len(data),as_of=reader.context['trade_date'],quality_counts=quality,unknown_fields=unknown,source_feature=domain if domain in m.get('domain_features',{}) else 'BOUND_OWNER_PROJECTION',impact=[g for g in m['gaps'] if g['domain']==domain]))
        return reader.envelope(status='READY',items=rows,api_health='CURRENT_IMMUTABLE_READER_VERIFIED',intraday='NO_BOUND_INTRADAY_DATA',PIT='CURRENT_MEMBERSHIP_VALID_PRIOR_HISTORY_NOT_BACKFILLED',adjustment='NATIVE_LOCAL_AFFINE_FAIL_CLOSED',turnover='SEE_FIELD_LOCAL_SOURCE_QUALITY',freshness='LAST_ACCEPTED_SESSION_NOT_REALTIME')
    if part in ('sources','contracts'):
        return reader.envelope(status='READY',sources=m['sources'],field_registry=m['field_registry'],owners=m['owners'],source_contract_digest=m['source_contract_digest'],domain_contracts={k:v.get('contract_id') for k,v in m.get('domain_features',{}).items()},gaps=m['gaps'])
    if part=='jobs':
        rows=[]
        for name in ('BUILD_LATEST.json','DAILY_LATEST.json','FAILED_RECEIPT.json'):
            path=reader.root/'runtime/research_daily'/name
            if not path.exists():continue
            data=json.loads(path.read_bytes());rows.append(dict(job=name,status=data.get('status'),indexed_counts=data.get('counts'),last_successful_date=data.get('last_successful_date'),reason_code=data.get('pipeline_exit_code'),pointer_preserved=data.get('pointer_preserved'),source_requests=data.get('source_requests')))
        return reader.envelope(status='READY',items=rows,log_policy='BOUNDED_STATUS_ONLY_NO_RAW_SHELL_OR_CREDENTIAL_PATHS')
    if part=='legacy':return reader.envelope(status='READY',items=[dict(legacy=a,current=b,href=c) for a,b,c in LEGACY],legacy_database='RETIRED_NOT_RESTORED',legacy_summary='/v4/legacy-summary',scope='READ_ONLY_EXISTING_V4_SUMMARY_AND_REAL_PROJECTION')
    if part=='shadow':return reader.envelope(status='READY',href='/v4/shadow',scope='INDEPENDENT_SHADOW_CONTEXT_NOT_DEFAULT_PRODUCTION',LOO='SOURCE_NOT_BOUND_TO_CURRENT_RESEARCH_CONTEXT',v3_shadow='RETIRED_DATABASE_NO_IMPLICIT_RESTORE')
    return None
