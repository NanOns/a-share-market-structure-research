"""Independent threshold oracle over actual accepted owner evidence.

Does not call profile_core state functions. Input accuracy remains a separate
factor-source audit; this proves categorical rules and snapshot projection.
"""
import collections,gzip,json,math,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import checked_path
OUT=ROOT/'docs/evidence/r2_presentation_continuation_20261008'
P={x['parameter_id'].removeprefix('V4_04_'):x['value'] for x in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}

def rule(field,e):
    numeric=[v for k,v in e.items() if k not in ('period_view','hh_progress','ll_progress','core_price_damage','minimum_liquidity')]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in numeric):return 'UNKNOWN'
    if field in ('weekly_trend_state','monthly_trend_state'):
        period='WEEKLY' if field.startswith('weekly') else 'MONTHLY';key='ma5' if period=='WEEKLY' else 'ma3'
        if e['period_view']!='CLOSED_ONLY':return 'UNKNOWN'
        return period+('_UP' if e['close']>e[key]>e['previous_'+key] else '_DOWN' if e['close']<e[key]<e['previous_'+key] else '_FLAT')
    if field=='amount_state':
        x=e['amount_ratio20']
        for threshold,state in [('RATIO_VERY_DRY','VERY_DRY'),('RATIO_CONTRACTED','CONTRACTED'),('RATIO_NORMAL','NORMAL'),('RATIO_EXPANDED','EXPANDED')]:
            if x<P[threshold]:return state
        return 'VERY_EXPANDED'
    if field=='position_state':
        if e['bias20_atr']>=P['POSITION_EXTENDED_BIAS']:return 'EXTENDED'
        for threshold,state in [('POSITION_HIGH','HIGH_ZONE'),('POSITION_MID_HIGH','MID_HIGH'),('POSITION_MID','MID_ZONE'),('POSITION_MID_LOW','MID_LOW')]:
            if e['pos60']>=P[threshold]:return state
        return 'LOW_ZONE'
    if field=='ma_structure_state':
        a,b,c,s=(e[k] for k in ('ma5','ma10','ma20','slope20'))
        if a>b>c and s>0:return 'BULL_ALIGNED'
        if a<b<c and s<0:return 'BEAR_ALIGNED'
        if a>c and s>=0:return 'BULL_TRANSITION'
        if a<c and s<=0:return 'BEAR_TRANSITION'
        return 'MIXED'
    if field=='compression_state':
        if not isinstance(e['minimum_liquidity'],bool):return 'UNKNOWN'
        a,v,r,m=(e[k] for k in ('atr_ratio','vol_ratio','range_ratio','amount_ratio20'))
        if max(a,v)>=P['COMPRESS_EXTREME']:return 'EXPANDING_EXTREME'
        if max(a,v)>=P['COMPRESS_EXPAND']:return 'EXPANDING'
        if e['minimum_liquidity'] and r<=P['COMPRESS_STRONG_RANGE'] and max(a,v)<=P['COMPRESS_STRONG_ATR_VOL'] and m<=P['COMPRESS_STRONG_AMOUNT']:return 'COMPRESSING_STRONG'
        if e['minimum_liquidity'] and r<=P['COMPRESS_RANGE'] and max(a,v)<=P['COMPRESS_ATR_VOL']:return 'COMPRESSING'
        return 'NORMAL'
    if field=='trend_state':
        if any(not isinstance(e[k],bool) for k in ('hh_progress','ll_progress','core_price_damage')):return 'UNKNOWN'
        c,m20,m60,s20,s60=(e[k] for k in ('close','ma20','ma60','slope20','slope60'));d=P['SLOPE_DEADBAND_ATR']
        if c<m20 and s20<-d and s60<-d and e['ll_progress']:return 'DOWNTREND_STRONG'
        if c>m20 and s20>d and (c>m60 or s60>d) and e['hh_progress'] and not e['core_price_damage']:return 'UPTREND_STRONG'
        if c<m20 and s20<-d:return 'DOWNTREND'
        if c>m20 and s20>d and not e['core_price_damage']:return 'UPTREND'
        return 'SIDEWAYS_WEAK' if c<m20 else 'SIDEWAYS_STRONG' if c>m20 else 'SIDEWAYS'
    raise AssertionError(field)

def main():
    reader=ProductionV4ResearchReader(ROOT);source=reader.manifest['domain_features']['stocks']['profiles'];counts=collections.defaultdict(collections.Counter);excluded=[];seen=set()
    fields=('trend_state','weekly_trend_state','monthly_trend_state','position_state','ma_structure_state','compression_state','amount_state')
    with sqlite3.connect(reader.path.as_uri()+'?mode=ro',uri=True) as db:
        projection={json.loads(p)['entity_id']:json.loads(p)['fields'] for p, in db.execute('SELECT payload FROM objects WHERE domain=?',('stocks',))}
    with gzip.open(checked_path(ROOT,source),'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line);sid=row['security_id']
            if sid not in projection:
                excluded.append(dict(security_id=sid,reason='NOT_IN_ACCEPTED_CURRENT_RAW_STOCK_SCOPE'));continue
            assert sid not in seen;seen.add(sid)
            for field in fields:
                state=row['states'][field];expected=rule(field,state['evidence'])
                assert expected==state['value'],(sid,field,expected,state['value'])
                assert projection[sid][field]['value']==expected,(sid,field,'PROJECTION_MISMATCH')
                if expected=='UNKNOWN':assert state['unknown_reason'];counts[field]['unknown_preserved']+=1
                else:counts[field]['known_verified']+=1
    assert seen==set(projection) and len(seen)==5213
    write(OUT/'PROFILE_STATE_ORACLE.json',dict(result='PASS',scope='OWNER_INPUT_THRESHOLD_RULES_AND_SNAPSHOT_NOT_INDEPENDENT_RAW_INPUT_RECOMPUTATION',source=source,parameters=ref('config/v4_04_parameter_set_v1.json'),fields=counts,excluded_owner_identities=excluded,accepted_stock_count=len(seen),comparison_count=sum(sum(c.values()) for c in counts.values())))
    print(json.dumps(dict(result='PASS',comparisons=sum(sum(c.values()) for c in counts.values()))))

if __name__=='__main__':main()
