"""Accepted price-limit facts and frozen official index bars, never a 10% shortcut."""
import json,sys,zipfile
from pathlib import Path
from dataclasses import asdict
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter,operational_path
from scripts.build_fp05_market import verified
from workbench_service.current_v4_context import canonical,digest
from tdx.day_reader import decode_record

def main():
    out=enter(9);headref=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json');head=json.loads(verified(headref).read_bytes());target=head['trade_date'] if 'trade_date' in head else head['accepted_trade_date']
    sources={k:head['component_artifacts'][k] for k in ('RAW_DAILY','PRICE_LIMIT','TRADING_STATUS','IDENTITY_UNIVERSE')};sources['data_head']=headref;sources['projection_adapter']=ref('scripts/build_fp09_market_center.py')
    limit=json.loads(verified(sources['PRICE_LIMIT']).read_bytes())['rows'];raw=json.loads(verified(sources['RAW_DAILY']).read_bytes())['rows'];prices={r['security_id']:r for r in raw};states=Counter(r['limit_status'] for r in limit);breadth=Counter();amount=0
    for r in limit:
        p=prices.get(r['security_id']);reference=r.get('reference_price')
        if not p or r['trading_status']!='ACTUAL_TRADED' or reference is None:breadth['unknown']+=1;continue
        delta=float(p['close'])-float(reference);breadth['up' if delta>0.000001 else 'down' if delta<-.000001 else 'flat']+=1
    amount=sum(float(r['amount']) for r in raw)
    chain=json.loads(verified(head['accepted_chain']).read_bytes());dated={}
    for node in chain['nodes']:
        if node['trade_date']>target:continue
        receipt=node['components']['PRICE_LIMIT'];binding=dict(path=receipt['artifact_path'],sha256=receipt['artifact_sha256']);sources['limits_'+node['trade_date']]=binding;dated[node['trade_date']]={r['security_id']:r for r in json.loads(verified(binding).read_bytes())['rows']}
    ladder=[]
    for r in limit:
        if r['limit_status']!='LIMIT_UP':continue
        run=0;prefix_unknown=True
        for day in sorted(dated,reverse=True):
            previous=dated[day].get(r['security_id'])
            if not previous or previous['limit_status']=='UNKNOWN':break
            if previous['limit_status']!='LIMIT_UP':prefix_unknown=False;break
            run+=1
        ladder.append(dict(entity_id=r['security_id'],symbol=r['source_security_key'],consecutive_limit_up_lower_bound=run,exact_streak=None if prefix_unknown else run,reason='HISTORICAL_PREFIX_NOT_BOUND' if prefix_unknown else None))
    zpath=ROOT/'data/v4/source_evidence/dm01_a01_r3/tdx/20261001T100202286790Z/sha256-d87d490151ffb45ff63c500f925be8acb7de992de693eb871029211d7ed87655/hsjday.zip';sources['index_archive']=ref(zpath);assert sources['index_archive']['sha256']=='d87d490151ffb45ff63c500f925be8acb7de992de693eb871029211d7ed87655'
    indices=[]
    with zipfile.ZipFile(zpath) as archive:
        for filename,name in [('sh000001','上证指数'),('sz399001','深证成指'),('sz399006','创业板指'),('sh000300','沪深300'),('sh000852','中证1000')]:
            member=filename[:2]+'/lday/'+filename+'.day';data=archive.read(member);assert len(data)%32==0;bars=[]
            for i in range(0,len(data),32):
                b=asdict(decode_record(data[i:i+32]));day=str(b.pop('trade_date'));b['trade_date']=day[:4]+'-'+day[4:6]+'-'+day[6:];b.pop('reserved')
                if b['trade_date']<=target:bars.append(dict(**b,quality='KNOWN'))
            bars=bars[-120:];assert bars and bars[-1]['trade_date']==target;indices.append(dict(symbol=filename,display_name=name,bars=bars,price_basis='RAW_INDEX_POINTS',volume_unit='SOURCE_NATIVE_INDEX_VOLUME_UNVERIFIED',amount_unit='CNY',source_member=member))
    publication=dict(contract_id='FP09_MARKET_CENTER_V1',trade_date=target,sources=sources,indices=indices,breadth=dict(breadth,denominator=len(limit),actual_quote_count=len(raw),amount_cny=amount),limits=dict(counts=dict(states),rows=limit,rule_ids=sorted({r['rule_id'] for r in limit if r.get('rule_id')})),ladders=ladder,facts_events=dict(status='SOURCE_UNAVAILABLE',items=[],reason='NO_APPROVED_BOUND_OFFICIAL_OR_MEDIA_EVENT_DATASET'),broken_limit=dict(status='SOURCE_UNAVAILABLE',reason='INTRADAY_LIMIT_TOUCH_SEQUENCE_NOT_BOUND'),mode='POST_CLOSE_AS_OF',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    path=ROOT/'data/v4/fp09_market_center'/digest(canonical(publication))/'market_center.json';write(path,publication);write(operational_path('v4_market_center_authority_v1.json',for_write=True),dict(contract_id='FP09_MARKET_CENTER_AUTHORITY_V1',trade_date=target,input_data_head=headref,publication=ref(path)));write(out/'REAL_SOURCE_READBACK.json',dict(indices=[dict(name=i['display_name'],bars=len(i['bars']),last=i['bars'][-1]) for i in indices],breadth=publication['breadth'],limits=dict(states),ladder_count=len(ladder),sources=sources))
    print(json.dumps(dict(indices=len(indices),limits=dict(states),breadth=publication['breadth']),ensure_ascii=False))
if __name__=='__main__':main()
