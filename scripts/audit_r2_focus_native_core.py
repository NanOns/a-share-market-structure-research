"""Actual dated native operands and independent series/extension rule oracle."""
import collections,gzip,json,math,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import checked_path
from scripts.audit_r2_current_stock_facts import risk
OUT=ROOT/'docs/evidence/r2_focus_native_core_continuation_20261008'

def main():
    candidate=json.loads((OUT/'FOCUS_CANDIDATE.json').read_bytes());pub=json.loads(checked_path(ROOT,candidate['publication']).read_bytes());owner=pub['sources']['native_core'];day=candidate['trade_date']
    def load(binding):
        with gzip.open(checked_path(ROOT,binding),'rt',encoding='utf8') as stream:return {r['security_id']:r for r in map(json.loads,stream)}
    factors=load(owner['factors']);profiles=load(owner['profiles']);p={x['parameter_id'].removeprefix('V4_04_'):x['value'] for x in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']};counts=collections.Counter();rows=[]
    with sqlite3.connect(checked_path(ROOT,owner['series'])) as db:
        for ep in pub['episodes']:
            for obs in ep['observations']:
                native=obs['native_core_evidence']
                if obs['trade_date']!=day:assert native['facts']=={};counts['earlier_day_not_backfilled']+=1;continue
                sid=ep['entity_id'];actual=native['facts'];f=factors[sid]['fields'];profile=profiles[sid];assert native['source']['factors']==owner['factors']
                for key,source in [('ma20','ma20'),('r5','ret5')]:assert actual[key]==(None if f[source].get('unknown_reason') else f[source]['value']);counts['native_value']+=1
                expected=profile['states']['severe_extension']['value'];assert actual['source_extended']==expected;counts['native_value']+=1
                for key in ['ma20','ret5']:
                    cell=f[key]
                    if cell['value'] is None or cell.get('unknown_reason'):counts['unknown_'+key]+=1;continue
                    def bar(d):
                        row=db.execute('SELECT payload FROM bars WHERE security=? AND day=?',(sid,d)).fetchone();return json.loads(row[0]) if row else None
                    if key=='ma20':
                        bars=[json.loads(x[0]) for x in db.execute('SELECT payload FROM bars WHERE security=? AND day<=? ORDER BY day DESC LIMIT 20',(sid,day))]
                        assert len(bars)==20 and all(b['qfq_ohlc'] for b in bars)
                        value=sum(float(b['qfq_ohlc'][3]) for b in bars)/20
                    else:
                        start=bar(cell['window_start_trade_date']);end=bar(day);assert start and end and start['qfq_ohlc'] and end['qfq_ohlc'];value=float(end['qfq_ohlc'][3])/float(start['qfq_ohlc'][3])-1
                    assert math.isclose(value,cell['value'],rel_tol=1e-11,abs_tol=1e-10),(sid,key,value,cell['value']);counts['independent_'+key]+=1
                source_risk=profile['states']['core_extension_risk'];computed=risk(source_risk['evidence'],p);expected=None if computed=='UNKNOWN' else computed=='EXTREME';assert actual['source_extended']==expected;counts['independent_severe_extension']+=1
                rows.append(dict(entity_id=sid,episode_id=ep['episode_id'],facts=actual,resolution=obs['path_resolution'],predicate_evidence=obs['predicate_evidence']))
    write(OUT/'NATIVE_CORE_ORACLE.json',dict(result='PASS',counts=dict(counts),comparisons=rows,sources=owner,strict_pit=False));print(json.dumps(dict(result='PASS',counts=dict(counts))))
if __name__=='__main__':main()
