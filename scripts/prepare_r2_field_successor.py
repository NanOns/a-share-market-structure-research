"""Independent full-member MA20-width oracle and an immutable field successor."""
import copy,gzip,json,math,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,build_snapshot
from workbench_service.joint_release import AUTHORITY,validate,checked_path
from workbench_service.current_v4_context import SourceInvalid
OUT=ROOT/'docs/evidence/r2_field_continuation_20261008'

def main():
    if (OUT/'CANDIDATE.json').exists():raise SourceInvalid('FIELD_SUCCESSOR_ALREADY_FROZEN')
    before=(ROOT/AUTHORITY).read_bytes();candidate=json.loads(before);reader=ProductionV4ResearchReader(ROOT);day=candidate['trade_date']
    sector=json.loads((ROOT/'data/v4/r2_daily_candidates/width_v2_20261008/v4_sector_operational_authority_v1.json').read_bytes())
    factors={r['security_id']:r for r in (json.loads(l) for l in gzip.open(checked_path(ROOT,sector['factors']),'rt',encoding='utf8'))}
    native=[json.loads(l) for l in gzip.open(checked_path(ROOT,sector['native']),'rt',encoding='utf8')]
    ma_verified={};unknown=[]
    series=checked_path(ROOT,reader.manifest['sources']['stock_series'])
    with sqlite3.connect(series.as_uri()+'?mode=ro',uri=True) as db:
        for sid,factor in factors.items():
            cell=factor['fields']['ma20']
            if cell['quality_state']!='OBSERVED':unknown.append(sid);continue
            bars=[json.loads(r[0]) for r in db.execute('SELECT payload FROM bars WHERE security=? AND day<=? ORDER BY day DESC LIMIT 20',(sid,day))]
            assert len(bars)==20 and all(b['qfq_ohlc'] for b in bars)
            mean=sum(float(b['qfq_ohlc'][3]) for b in bars)/20
            assert math.isclose(mean,cell['value'],rel_tol=1e-12,abs_tol=1e-9)
            # A real target bar is required; a suspended last quote is not a
            # current close for the width denominator.
            if bars[0]['trade_date']==day:ma_verified[sid]=(float(bars[0]['qfq_ohlc'][3]),mean)
    comparisons=[]
    for row in native:
        endpoints=[ma_verified[sid] for sid in row['member_ids'] if sid in ma_verified]
        expected=sum(close>ma for close,ma in endpoints)/len(endpoints) if endpoints else None
        cell=row['fields']['ma20_width']
        assert cell['known_count']==len(endpoints)
        assert cell['value']==expected
        comparisons.append(dict(sector_id=row['sector_id'],members=len(row['member_ids']),denominator=len(endpoints),
            numerator=sum(close>ma for close,ma in endpoints),value=expected,source=sector['native']))
    write(OUT/'WIDTH_ORACLE.json',dict(result='PASS',ma20_windows_verified=len(ma_verified),unknown_ma20=len(unknown),
        sectors=len(comparisons),comparisons=comparisons,actual_series=reader.manifest['sources']['stock_series'],
        factors=sector['factors'],native=sector['native'],formula='COUNT(QFQ_CLOSE > SAME_BASIS_MA20) / COUNT(KNOWN_TARGET_ENDPOINTS)',
        historical_membership_backfilled=False))
    owners=copy.deepcopy(candidate['daily_owner_authorities']);owners['sector']=sector
    snapshot=build_snapshot(ROOT,publish=False,focus_override=dict(trade_date=day,input_data_head=sector['input_data_head'],
        publication=reader.manifest['sources']['focus_operational'],journal=reader.manifest['sources']['focus_journal']),authority_overrides=owners)
    candidate.update(snapshot=snapshot['pointer'],daily_owner_authorities=owners)
    manifest=validate(ROOT,candidate)
    staged=ProductionV4ResearchReader(ROOT,snapshot_authority=snapshot['pointer'])
    assert staged.query('sectors',{'limit':1})['items'][0]['fields']['ma20_width']['denominator']>0
    assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/'CANDIDATE.json',candidate);write(OUT/'SNAPSHOT.json',snapshot)
    print(json.dumps(dict(result='WIDTH_SOURCE_ORACLE_PASS',sectors=len(comparisons),ma20_windows=len(ma_verified))))

if __name__=='__main__':main()
