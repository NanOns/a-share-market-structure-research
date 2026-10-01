"""Full-row business equality for the unchanged price runtime and explicit remaining quality reasons."""
import gzip,json,sys
from pathlib import Path
from collections import Counter
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.build_v4_02_price_limits_generic import BUSINESS_FIELDS
P='reports/audits/A12_R2_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def rows(p):
    with gzip.open(ROOT/p,'rt',encoding='utf8') as f:yield from (json.loads(l) for l in f)
def reasons(value,prefix=''):
    if isinstance(value,dict):
        if value.get('quality') in ('UNKNOWN','UNAVAILABLE','BLOCKED') or value.get('status') in ('UNKNOWN','UNAVAILABLE','BLOCKED'):
            yield prefix+':'+str(value.get('reason') or value.get('reason_code') or value.get('quality') or value.get('status'))
        for k,v in value.items():yield from reasons(v,prefix+'.'+k if prefix else k)
    elif isinstance(value,list):
        for v in value:yield from reasons(v,prefix+'[]')
def main():
    r=read(P+'V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json');c=duckdb.connect()
    fields=list(dict.fromkeys(['security_id','source_security_key','trade_date','trading_status',*BUSINESS_FIELDS]));cols=','.join(fields)
    old='data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_20260927.jsonl.gz';new=r['artifacts']['price']['path']
    for n,p in [('old',old),('new',new)]:c.execute('create table '+n+' as select '+cols+' from read_json_auto(?)',[str(ROOT/p)])
    diff=c.execute('select count(*) from ((select * from old except all select * from new) union all (select * from new except all select * from old))').fetchone()[0];assert diff==0
    price=c.execute('select limit_status,count(*) from new group by all').fetchall();unknown=c.execute("select reason,count(*) from new where limit_status='UNKNOWN' group by all").fetchall()
    # R1 candidate comparison shows which boundary repair actually changes business outputs.
    c.execute('create table r1 as select '+cols+' from read_json_auto(?)',[str(ROOT/'data/v4/artifact_store/a12_authority_candidate_r1/V4_02_PRICE_LIMIT_AUTHORITY_R1.jsonl.gz')])
    transitions=c.execute('select r1.limit_status,new.limit_status,count(*) from r1 join new using(security_id,source_security_key,trade_date) group by all').fetchall()
    profiles={}
    for stage,p in [('V4_04',read(P+'V4_04_TRUE_REPLAY_R1.json')['artifact']['path']),('V4_05','reports/audits/a12_v4_05_r2/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz')]:
        quality=Counter();unknown_reasons=Counter();examples=[]
        for row in rows(p):
            quality[row['profile_quality']]+=1;rs=list(reasons(row));unknown_reasons.update(rs)
            if len(examples)<6:examples.append(dict(security_id=row['security_id'],profile_quality=row['profile_quality'],unknown_fields=rs))
        profiles[stage]=dict(quality_counts=dict(quality),unknown_field_reason_counts=dict(unknown_reasons),examples=examples,artifact=bind(p))
    atomic_json(ROOT/(P+'PRICE_AND_REMAINING_QUALITY_PROOF_R1.json'),dict(status='PASS_PRICE_RUNTIME_AND_EXPLICIT_REMAINING_QUALITY',old_price=bind(old),candidate=r['artifacts']['price'],all_price_business_fields=fields,all_price_business_differences=diff,known=sum(n for s,n in price if s!='UNKNOWN'),unknown=sum(n for s,n in price if s=='UNKNOWN'),price_status_counts=dict(price),unknown_reasons=dict(unknown),r1_to_r2_price_transitions=transitions,profile_quality=profiles,conclusion='Status/ST source boundary restored in candidate. Existing unrelated unknown factors/adjustment/reference capabilities remain; no business completion claim for Core Profile and no fitted counts',formal_publication=False,external_acceptance=None))
    print('PASS_PRICE_BUSINESS_EQUAL',dict(price),'quality', {k:v['quality_counts'] for k,v in profiles.items()})
if __name__=='__main__':main()
