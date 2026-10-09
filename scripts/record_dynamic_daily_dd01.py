"""Record real calendar reads separately from simulated-clock acceptance cases."""
from pathlib import Path
from datetime import datetime
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from workbench_analysis.operational_daily_calendar_v2 import gap_plan, plan_sessions
from workbench_analysis.dm01_runtime_r4 import calendar
from workbench_analysis.scoped_successor_r421 import atomic, canonical, sha

OUT=ROOT/'docs/evidence/dynamic_daily_20261009'
if __name__=='__main__':
    cal=calendar(ROOT)
    heads=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
    before={p:sha(ROOT/p) for p in heads}
    actual=gap_plan(ROOT)
    cases=[]
    for clock in ['16:00','18:34','18:35','22:10']:
        cases.append(dict(evidence_kind='REAL_CALENDAR_SIMULATED_CLOCK',result=plan_sessions(
            '2026-09-30',datetime.fromisoformat('2026-10-09T'+clock+'+08:00'),cal)))
    sessions=cal['session_dates']
    for n in [1,2,5,10,20]:
        result=plan_sessions(sessions[0],datetime.fromisoformat(sessions[n]+'T22:10+08:00'),cal)
        assert result['eligible_sessions']==sessions[1:n+1]
        cases.append(dict(evidence_kind='REAL_CALENDAR_SIMULATED_DOWNTIME',count=n,result=result))
    assert before=={p:sha(ROOT/p) for p in heads}
    atomic(OUT/'DD01_REAL_CALENDAR_READBACK.json',canonical(dict(actual=actual,cases=cases,protected=before)))
    print(json.dumps(actual,ensure_ascii=False))
