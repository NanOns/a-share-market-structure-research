"""Check real Forward API episodes for target-date leakage."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.r43_operational_publication import CandidateReadV2
from workbench_analysis.corrected_owner_replay import load
from workbench_analysis.market_source_acquisition import write
OUT=ROOT/'docs/evidence/r4_3_four_session_closeout_20261009'
candidate=load(OUT/'R43_OPERATIONAL_SUCCESSOR_CANDIDATE.json')
api=CandidateReadV2(ROOT,candidate)
results=[]
for day in candidate['dates']:
    payload=api.read('forward',day,api.token)['rows'];checks=0
    for episode in payload['episodes']:
        assert episode['start_date']<=day
        assert episode['end_date'] is None or episode['end_date']<=day
        checks+=2
        for collection in ['observations','anchors','outcomes']:
            for row in episode[collection]:
                assert row['trade_date']<=day
                checks+=1
        assert episode['membership']==episode['observations'][-1]['membership']
        checks+=1
    for event in payload['events']:
        assert event.get('trade_date',event.get('event_date'))==day
        checks+=1
    results.append(dict(trade_date=day,episodes=len(payload['episodes']),checks=checks))
write(OUT/'FORWARD_API_EXACT_DATE_CUTOFF_ORACLE.json',dict(status='PASS',candidate_digest=api.token,scope='Actual owner bytes through CandidateReadV2; no future episodes/observations/anchors/outcomes/end-date or latest membership leakage',results=results))
print(json.dumps(results))
