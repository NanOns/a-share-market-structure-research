"""Bind compact LOO/Market evidence to existing immutable owners; no production writes."""
from pathlib import Path
import gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.market_source_acquisition import official_sessions
from workbench_analysis.operational_daily_periods_v1 import derive_periods
OUT=ROOT/'docs/evidence/dynamic_daily_r2_20261009/minipack'
def load(p):return json.loads(p.read_bytes())
def checked(binding):
    p=Path(binding['path']);p=p if p.is_absolute() else ROOT/p
    with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=binding['sha256']:raise ValueError('OWNER_SHA_MISMATCH:'+str(p))
    return p
def rows(binding):
    with gzip.open(checked(binding),'rt',encoding='utf8') as f:
        return [json.loads(line) for line in f]
def main():
    head=load(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    for day in ('2026-10-08','2026-10-09'):
        owners=head['owners'][day];data=load(OUT/'numerical'/f'{day}.json')
        core={r['security_id']:r for r in rows(owners['core'])}
        loo={r['security_id']:r for r in rows(owners['relative_sector'])}
        native={r['sector_id']:r for r in rows(owners['sector'])}
        eligible={m['sector_id'] for r in loo.values() for m in r['memberships'] if m.get('relative_substitutions')}
        selected=sorted((r for r in native.values() if r['sector_id'] in eligible),key=lambda r:(len(r['member_ids']),r['sector_id']))[:3]
        if len(selected)!=3:raise ValueError('THREE_VERIFIABLE_LOO_SECTORS_REQUIRED')
        data['sectors']=[dict(sector_id=r['sector_id'],member_ids=r['member_ids'],expected={k:r['fields'][k]['value'] for k in ('sector_rs1','breadth_ret1')}) for r in selected]
        for sector in data['sectors']:
            sector['contributions']=[dict(security_id=s,**{k:core[s]['fields'][k]['value'] for k in ('ret1','ret5')}) for s in sector['member_ids']]
            candidates=[(s,m) for s in sorted(sector['member_ids']) for m in loo[s]['memberships'] if m['sector_id']==sector['sector_id'] and m.get('relative_substitutions')]
            sector['loo_cases']=[]
            if candidates:
                sid,expected=candidates[0]
                sector['loo_cases'].append(dict(excluded_target_id=sid,non_target_member_count=expected['non_target_member_count'],stock_returns={k:core[sid]['fields'][k]['value'] for k in ('ret1','ret5')},expected_relative_substitutions=expected['relative_substitutions'],source_binding=owners['relative_sector']))
            sector['source_binding']=owners['sector']
            sector['scope']='complete ret1/ret5 contributors; target-excluded relative return substitutions; full relative state NOT_VERIFIABLE'
        market=load(checked(owners['market']))
        data['market_participation']=dict(contract='MARKET_REGIME_V1_PRIMITIVES@1.0.0',parameter_binding=dict(path='config/v4_03_parameter_registry_v1.json',sha256=hashlib.sha256((ROOT/'config/v4_03_parameter_registry_v1.json').read_bytes()).hexdigest()),thresholds=dict(expanding=1.2,thin=.8),accepted_pool_count=len(core),contributions=[dict(security_id=s,amount_ratio20=core[s]['fields']['amount_ratio20']['value']) for s in sorted(core)],expected_axis=market['axes']['participation_axis'],source_binding=owners['market'],scope='participation median and classification only; other axes NOT_VERIFIABLE')
        for sample in data['core']:
            sample['expected']={k:core[sample['security_id']]['fields'][k] for k in sample['expected']}
        atomic_json(ROOT,OUT/'numerical'/f'{day}.json',data)
    sessions=official_sessions(ROOT)
    atomic_json(ROOT,OUT/'periods/CALENDAR_STATE_INPUT.json',dict(contract='V4_02_FORMAL_RAW_QFQ_PERIODS_V1',session_dates=sessions,coverage_end=max(sessions),scope='calendar closure only; historical missing-day status counts not independently verified'))
    fixture_sessions=['2026-09-29','2026-09-30','2026-10-08','2026-10-09','2026-10-12','2026-10-13']
    def bar(day,known=True):return dict(trade_date=day,raw_ohlc=[10,12,9,11],qfq_ohlc=[5,6,4.5,5.5] if known else [],volume=10,amount=100)
    fixtures=[]
    for name,history,statuses,target,start in [
        ('CLOSED_WEEK_PARTIAL_MONTH',[bar('2026-10-08'),bar('2026-10-09')],{},'2026-10-09','2026-10-08'),
        ('SUSPENDED_NO_FAKE_BAR',[bar('2026-10-08')],{'2026-10-09':'SUSPENDED'},'2026-10-09','2026-10-08'),
        ('DATA_GAP',[bar('2026-10-08')],{'2026-10-09':'DATA_GAP'},'2026-10-09','2026-10-08'),
        ('UNKNOWN_STATUS',[bar('2026-10-08')],{},'2026-10-09','2026-10-08'),
        ('QFQ_UNREADY',[bar('2026-10-08'),bar('2026-10-09',False)],{},'2026-10-09','2026-10-08'),
        ('ALL_SUSPENDED',[],{'2026-10-08':'SUSPENDED','2026-10-09':'SUSPENDED'},'2026-10-09','2026-10-08')]:
        member=dict(security_id='FIXTURE_SECURITY',source_security_key='SH.600000')
        expected=derive_periods(member,history,statuses,fixture_sessions,target,'2026-10-31',start_session=start)
        fixtures.append(dict(case=name,evidence_kind='FIXTURE',history=history,statuses=statuses,target=target,start=start,session_dates=fixture_sessions,coverage_end='2026-10-31',expected=expected))
    atomic_json(ROOT,OUT/'periods/STATE_BOUNDARY_FIXTURES.json',fixtures)
    print('COMPACT_SUPPLEMENT_WRITTEN_WITH_VERIFIED_OWNER_BINDINGS')
if __name__=='__main__':main()
