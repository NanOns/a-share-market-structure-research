"""Index accepted history and expose existing dated facts; no factor re-compute."""
from pathlib import Path
import json, gzip, sqlite3, hashlib, os, sys, zipfile, struct
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.r43_owner_replay import checked, ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def load(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:
        return [json.loads(x) for x in f if x.strip()] if '.jsonl' in p.name else json.load(f)

def main():
    headpath=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head=load(headpath);day=head['accepted_trade_date']
    folder=checked(ROOT,head['day_receipt']).parent
    replay=load(folder/'owner_v3/CORE_REPLAY.json');owner=next(o for o in replay['owners'] if o['trade_date']==day)
    bindings=dict(history=owner['history'],package=owner['sources']['package'],raw=head['owners'][day]['raw'],core=head['owners'][day]['core'],
                  names=load(ROOT/'config/v4_display_names_authority_v1.json')['source'],market=head['owners'][day]['market'])
    market=load(checked(ROOT,bindings['market']))
    limitrefs=[b for b in market['input_bindings'] if 'daily_price_limits' in b['path']]
    bindings.update({'limits_'+str(i):b for i,b in enumerate(limitrefs)})
    out=ROOT/'data/v4/core_product_read_r1'/hashlib.sha256(headpath.read_bytes()).hexdigest();out.mkdir(parents=True,exist_ok=True)
    dbpath=out/'history.sqlite'
    if not dbpath.exists():
        tmp=dbpath.with_suffix('.tmp');db=sqlite3.connect(tmp);db.execute('CREATE TABLE history(security TEXT PRIMARY KEY,payload TEXT) WITHOUT ROWID')
        count=0
        with gzip.open(checked(ROOT,bindings['history']),'rt',encoding='utf8') as stream:
            for line in stream:
                row=json.loads(line);assert all(b['trade_date']<=day for b in row['bars'])
                db.execute('INSERT INTO history VALUES (?,?)',(row['security_id'],json.dumps(row['bars'],separators=(',',':'))));count+=1
        db.commit();db.close();os.replace(tmp,dbpath)
    raw={r['security_id']:r for r in load(checked(ROOT,bindings['raw']))}
    core=load(checked(ROOT,bindings['core']));breadth=Counter(up=0,down=0,flat=0,unknown=0)
    for row in core:
        ret=row['fields']['ret1']['value'] if row['security_id'] in raw else None
        breadth['unknown' if ret is None else 'up' if ret>0 else 'down' if ret<0 else 'flat']+=1
    limits=load(checked(ROOT,limitrefs[0]));dated=[{x['security_id']:x for x in load(checked(ROOT,b))} for b in limitrefs]
    ladders=[]
    for item in limits:
        if item['limit_state']!='LIMIT_UP':continue
        run=0;exact=False
        for prior in dated:
            prior=prior.get(item['security_id'])
            if not prior or prior['limit_state']=='UNKNOWN':break
            if prior['limit_state']!='LIMIT_UP':exact=True;break
            run+=1
        ladders.append(dict(entity_id=item['security_id'],symbol=item['source_security_key'],consecutive_limit_up_lower_bound=run,exact_streak=run if exact else None,reason=None if exact else 'PREFIX_NOT_BOUND'))
    indices=[]
    with zipfile.ZipFile(checked(ROOT,bindings['package'])) as archive:
        names={n.lower():n for n in archive.namelist()}
        for symbol,name in [('sh000001','上证指数'),('sz399001','深证成指'),('sz399006','创业板指'),('sh000300','沪深300'),('sh000852','中证1000')]:
            member=names.get(symbol[:2]+'/lday/'+symbol+'.day')
            if not member:continue
            bars=[]
            for row in struct.iter_unpack('<IIIIIfII',archive.read(member)):
                dt=str(row[0]);dt=dt[:4]+'-'+dt[4:6]+'-'+dt[6:]
                if dt<=day:bars.append(dict(trade_date=dt,open=row[1]/100,high=row[2]/100,low=row[3]/100,close=row[4]/100,amount=row[5],volume=row[6],quality='KNOWN'))
            if bars and bars[-1]['trade_date']==day:indices.append(dict(symbol=symbol,display_name=name,bars=bars[-120:],price_basis='RAW_INDEX_POINTS',volume_unit='SOURCE_NATIVE_UNVERIFIED',source_member=member))
    facts=dict(contract_id='CORE_PRODUCT_MARKET_FACT_READ_R1',trade_date=day,breadth=dict(breadth,denominator=len(core),actual_quote_count=len(raw),amount_cny=sum(r['amount'] for r in raw.values()),definition='ret1 in native T0 QFQ coordinate; actual T0 bar required'),indices=indices,limits=dict(counts=dict(Counter(r['limit_state'] for r in limits)),rows=limits),ladders=ladders,sources=bindings,AS_RECORDED=False,PIT_ELIGIBLE=False)
    atomic_json(ROOT,out/'market.json',facts)
    manifest=dict(contract_id='CORE_PRODUCT_DATED_READ_PACK_R1',T0=day,head=ref(ROOT,headpath),history_index=ref(ROOT,dbpath),market_facts=ref(ROOT,out/'market.json'),source_bindings=bindings,AS_RECORDED=False,PIT_ELIGIBLE=False,read_only=True,external_acceptance='NOT_GRANTED')
    atomic_json(ROOT,out/'MANIFEST.json',manifest)
    atomic_json(ROOT,ROOT/'config/core_product_read_authority_r1.json',dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R1',manifest=ref(ROOT,out/'MANIFEST.json')))
    print(json.dumps(dict(T0=day,manifest=ref(ROOT,out/'MANIFEST.json'),indices=len(indices),breadth=facts['breadth'],limits=facts['limits']['counts'])))

if __name__=='__main__':main()
