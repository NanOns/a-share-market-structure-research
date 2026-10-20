"""Scoped diagnostic views with bounded public evidence, never credential paths."""
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
            bound=domain in m.get('domain_features',{})
            core_projection=domain in ('stocks','sectors')
            rows.append(dict(module=domain,record_count=len(data),as_of=reader.context['trade_date'],
                quality_counts=quality,unknown_fields=unknown,
                availability='BOUND' if bound or core_projection else 'NOT_BOUND',
                source_feature=domain if bound else 'BASE_PG_PROJECTION' if core_projection else 'NOT_BOUND_TO_PG_CANDIDATE',
                impact=[g for g in m['gaps'] if g['domain']==domain]))
        return reader.envelope(status='READY',items=rows,api_health='CURRENT_IMMUTABLE_READER_VERIFIED',intraday='NO_BOUND_INTRADAY_DATA',PIT='CURRENT_MEMBERSHIP_VALID_PRIOR_HISTORY_NOT_BACKFILLED',adjustment='NATIVE_LOCAL_AFFINE_FAIL_CLOSED',turnover='SEE_FIELD_LOCAL_SOURCE_QUALITY',freshness='LAST_ACCEPTED_SESSION_NOT_REALTIME')
    if part in ('sources','contracts'):
        return reader.envelope(status='READY',sources=m['sources'],field_registry=m['field_registry'],owners=m['owners'],source_contract_digest=m['source_contract_digest'],domain_contracts={k:v.get('contract_id') for k,v in m.get('domain_features',{}).items()},gaps=m['gaps'])
    if part=='jobs':
        counts=m.get('counts',{})
        return reader.envelope(status='SOURCE_INCOMPLETE',items=[],scope='PG_CANDIDATE_SNAPSHOT_ONLY',
            indexed_trade_date=m.get('context',{}).get('accepted_trade_date'),
            indexed_counts=counts,worker_started=False,source_requests=0,
            reason='PG_CANDIDATE_DOES_NOT_CONTAIN_DAILY_WORKER_RECEIPTS',
            log_policy='NO_WORKSPACE_RECEIPT_FALLBACK')
    if part=='legacy':return reader.envelope(status='READY',items=[dict(legacy=a,current=b,href=c) for a,b,c in LEGACY],legacy_database='RETIRED_NOT_RESTORED',legacy_summary='/v4/legacy-summary',scope='READ_ONLY_EXISTING_V4_SUMMARY_AND_REAL_PROJECTION')
    if part=='shadow':return reader.envelope(status='READY',href='/v4/shadow',scope='INDEPENDENT_SHADOW_CONTEXT_NOT_DEFAULT_PRODUCTION',LOO='SOURCE_NOT_BOUND_TO_CURRENT_RESEARCH_CONTEXT',v3_shadow='RETIRED_DATABASE_NO_IMPLICIT_RESTORE')
    return None
