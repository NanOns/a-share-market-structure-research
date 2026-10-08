"""Compare both dated projections with actual RAW and check temporal boundaries."""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from workbench_service.production_v4 import ProductionV4ResearchReader
OUT=ROOT/'docs/evidence/r2_continuous_daily_20261008'

def main():
    proof=[]
    for day in ['2026-09-29','2026-09-30']:
        candidate=json.loads((OUT/('REPLAY_'+day+'.json')).read_bytes())
        reader=ProductionV4ResearchReader(ROOT,snapshot_authority=candidate['snapshot'])
        binding=reader.manifest['sources']['RAW_DAILY'];raw=json.loads((ROOT/binding['path']).read_bytes())['rows']
        lookup={v['security_id']:v for v in raw};cells=0;bad=[];prices=0;later_capture=0
        with sqlite3.connect(reader.path) as db:
            for domain,payload in db.execute('SELECT domain,payload FROM objects'):
                row=json.loads(payload)
                for key,value in row.get('fields',{}).items():
                    cells+=1
                    if value.get('quality')=='KNOWN' and value.get('value')=='UNKNOWN':bad.append([domain,row['entity_id'],key,'LITERAL_UNKNOWN_KNOWN'])
                    asof=value.get('source_as_of') or ''
                    if len(asof)==10 and asof>day:bad.append([domain,row['entity_id'],key,'FUTURE_VALUE_DATE'])
                    elif len(asof)>10 and asof[:10]>day:later_capture+=1
                if domain=='stocks':
                    for key in ['open','high','low','close']:
                        assert row['fields'][key]['value']==lookup[row['entity_id']][key];prices+=1
        focus=reader.manifest['domain_features']['focus'];observed=0
        for episode in focus['episodes']:
            assert episode['T0']<=day
            assert all(o['trade_date']<=day for o in episode['observations'])
            for outcome in episode['outcomes']:
                if outcome['outcome_status']=='OBSERVED':
                    assert outcome['target_trade_date']<=day;observed+=1
        assert not bad,bad[:10]
        proof.append(dict(day=day,actual_raw_oracle_comparisons=prices,field_cells_checked=cells,invalid_cells=bad,
            corrected_cells_with_later_capture_timestamp=later_capture,as_recorded=False,
            observed_outcomes=observed,focus_episodes=len(focus['episodes']),
            historical_membership='NOT_BACKFILLED' if day.endswith('29') else 'EXACT_DATED_ACCEPTED'))
    write(OUT/'TWO_DATE_SOURCE_QA.json',dict(result='PASS',per_day=proof,strict_pit=False,full_product_release=False))
    print(json.dumps(proof))

if __name__=='__main__':main()
