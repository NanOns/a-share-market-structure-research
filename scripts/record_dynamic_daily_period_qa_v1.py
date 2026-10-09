"""Real owner-byte period replay evidence, without touching accepted owners."""
import gzip
import json
from pathlib import Path
from workbench_analysis.operational_daily_periods_v1 import derive_periods
from workbench_analysis.market_source_acquisition import official_sessions
from workbench_analysis.r43_owner_replay import checked, ref, gzwrite
from workbench_analysis.operational_daily_storage_v1 import atomic_json


def main():
    root=Path(__file__).resolve().parents[1]
    head=json.loads((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    day=head['accepted_trade_date']; owner=head['owners'][day]
    receipt=json.loads(checked(root,owner['diagnostic']).read_bytes())['owner']
    sessions=official_sessions(root)
    statuses={}
    with gzip.open(checked(root,receipt['status']),'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line);statuses[row['security_id']]=row['status']
    artifacts={'PERIOD_RAW':[],'PERIOD_ADJUSTED':[]};sample=[]
    with gzip.open(checked(root,receipt['history']),'rt',encoding='utf8') as stream:
        for index,line in enumerate(stream):
            row=json.loads(line);sid=row['security_id']; history=row['bars']
            # Full saved history for 32 securities; all market for current month.
            window=history if index<32 else [b for b in history if b['trade_date'][:7]==day[:7]]
            member=dict(security_id=sid,source_security_key=sid)
            status={day:statuses[sid]}
            outputs=derive_periods(member,window,status,sessions,day,sessions[-1])
            if index<32:
                assert outputs==derive_periods(member,window,status,sessions,day,sessions[-1])
                sample.append(dict(security_id=sid,full_window_days=len(history)))
            for cap,rows in outputs.items():artifacts[cap].extend(rows)
    folder=root/'docs/evidence/dynamic_daily_20261009/periods'
    bindings={cap:gzwrite(root,folder/(cap+'.jsonl.gz'),rows) for cap,rows in artifacts.items()}
    evidence=dict(contract_id='OPERATIONAL_DAILY_PERIOD_REPLAY_V1',acceptance='PASS_REAL_OWNER_PERIOD_REPLAY',
        input_history=receipt['history'],input_status=receipt['status'],target_session=day,
        kernel=ref(root,root/'src/workbench_analysis/dm01_incremental_component_builders_r3_3.py'),
        formal_contract=ref(root,root/'config/v4_02_formal_period_contract_v1.json'),
        artifacts=bindings,row_counts={k:len(v) for k,v in artifacts.items()},full_history_determinism_samples=sample,
        scope='All saved current-month rows plus 32 full saved windows; not a new operational publication',
        next_stage='DD03_BIND_FULL_DYNAMIC_OWNER_PERIODS',AS_RECORDED=False,PIT_ELIGIBLE=False)
    atomic_json(root,folder/'QA.json',evidence)
    print(json.dumps({k:evidence[k] for k in ('acceptance','target_session','row_counts')}))


if __name__=='__main__':main()
