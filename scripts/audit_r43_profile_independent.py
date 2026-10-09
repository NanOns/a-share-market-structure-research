"""Independent frozen Profile branch oracle on the 128 actual price samples."""
import gzip,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/r4_3_four_session_closeout_20261009'
def load(p):return json.loads(p.read_bytes())
def rows(p):
    with gzip.open(p,'rt',encoding='utf8') as f:return [json.loads(l) for l in f if l.strip()]
def main():
    numeric=load(OUT/'05_FOUR_SESSION_RAW_QFQ_CORE_PROFILE_NUMERIC_ORACLE.json');params=load(ROOT/'config/v4_04_parameter_set_v1.json');p={r['parameter_id'].removeprefix('V4_04_'):r['value'] for r in params['parameters']};errors=[];samples=[]
    snapshot=load(OUT/'MEMBER_SNAPSHOT_S.json')
    for date in numeric['dates']:
        profiles={r['security_id']:r for r in rows(OUT/'owner_v3/owners'/date['trade_date']/'profiles.jsonl.gz')}
        for specimen in date['samples']:
            profile=profiles[specimen['security_id']];cells=profile['states'];checks=[]
            for name,sourcekey in [('amount_state','amount_ratio20'),('volume_state','volume_ratio20')]:
                cell=cells[name];ratio=cell['evidence'][sourcekey]
                if ratio is None:expected='UNKNOWN'
                else:expected=next((label for cutoff,label in [(p['RATIO_VERY_DRY'],'VERY_DRY'),(p['RATIO_CONTRACTED'],'CONTRACTED'),(p['RATIO_NORMAL'],'NORMAL'),(p['RATIO_EXPANDED'],'EXPANDED')] if ratio<cutoff),'VERY_EXPANDED')
                checks.append(dict(field=name,expected=expected,actual=cell['value']))
            cell=cells['near_high20_state'];e=cell['evidence'];atr=e['atr20'];c=e['close'];h=e['prior_high20'];distance=(h-c)/atr if atr is not None and atr>0 and c is not None and h is not None else None
            expected='UNKNOWN' if distance is None else 'ABOVE_PRIOR_HIGH' if distance<0 else 'NEAR' if distance<=p['NEAR_HIGH_ATR'] else 'BELOW';checks.append(dict(field='near_high20_state',expected=expected,actual=cell['value']))
            cell=cells['ma_structure_state'];e=cell['evidence'];a,b,c,s=[e[k] for k in ('ma5','ma10','ma20','slope20')]
            expected='UNKNOWN' if any(v is None for v in (a,b,c,s)) else 'BULL_ALIGNED' if a>b>c and s>0 else 'BEAR_ALIGNED' if a<b<c and s<0 else 'BULL_TRANSITION' if a>c and s>=0 else 'BEAR_TRANSITION' if a<c and s<=0 else 'MIXED';checks.append(dict(field='ma_structure_state',expected=expected,actual=cell['value']))
            for check in checks:
                if check['expected']!=check['actual']:errors.append(dict(trade_date=date['trade_date'],security_id=profile['security_id'],**check))
            assert profile['membership_snapshot_id']==snapshot['membership_snapshot_id'] and profile['AS_RECORDED'] is False and profile['PIT_ELIGIBLE'] is False
            assert all(cell['membership_context']['membership_snapshot_id']==snapshot['membership_snapshot_id'] for cell in cells.values())
            samples.append(dict(trade_date=date['trade_date'],security_id=profile['security_id'],category=specimen['category'],checks=checks,metadata_inheritance='PASS'))
    target=OUT/'05_INDEPENDENT_PROFILE_BRANCH_AND_METADATA_ORACLE.json';tmp=target.with_suffix('.tmp.profile');tmp.write_text(json.dumps(dict(contract='R43_INDEPENDENT_PROFILE_BRANCH_ORACLE_V1',actual_samples=len(samples),checks=len(samples)*4,source_numeric_oracle='05_FOUR_SESSION_RAW_QFQ_CORE_PROFILE_NUMERIC_ORACLE.json',parameter_set='config/v4_04_parameter_set_v1.json',semantics='Independent rule branches on exact published primitive evidence; price primitives independently verified by linked oracle',samples=samples,errors=errors,acceptance='PASS' if not errors else 'FAIL'),ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,target);print(len(samples),len(errors))
if __name__=='__main__':main()
