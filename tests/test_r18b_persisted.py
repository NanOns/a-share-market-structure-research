"""Real OS processes plus complete persisted lifecycle evidence."""
import json
from pathlib import Path
import pytest
from scripts.run_r18b import invoke,ROOT
from scripts.v4_14_independent_oracle import Oracle,read
from workbench_analysis.v4_14_authority import ReplayAuthority

def test_full_persisted_owner_lifecycle():
    o=Oracle(ROOT);g=json.loads((ROOT/'reports/v4_14_replay_r18/full_dag_r3/completion_gate.json').read_bytes());assert o.gate(ROOT,g)
    rows={r['date']:r for r in g['trajectory']};p=lambda date:rows[date]['state']
    assert p('2026-09-16')['maturity']=='PREWATCH' and p('2026-09-16')['downgrade_count']==1
    assert p('2026-09-17')['maturity']=='NONE' and p('2026-09-17')['downgrade_count']==2
    assert p('2026-09-10')['expiry_count']==9 and p('2026-09-11')['expiry_count']==10 and p('2026-09-11')['maturity']=='NONE'
    assert p('2026-09-14')['parent_episode_id']==p('2026-09-11')['episode_id']
    assert p('2026-09-18')['episode_id']==p('2026-09-21')['episode_id']==p('2026-09-23')['episode_id']
    assert p('2026-09-24')['validity']=='INVALIDATED'
    assert p('2026-09-28')['final_eligibility']=='UNKNOWN' and p('2026-09-28')['expiry_count']==p('2026-09-24')['expiry_count']
    assert {'TESTING','RECLAIMED','RETESTING','BROKEN','UNKNOWN'}<=set(r['structure'] for r in g['trajectory'])

def test_fresh_process_pair_revision_and_determinism(tmp_path):
    a=ReplayAuthority(ROOT);o=Oracle(ROOT);ns='proof'
    prior,pr,producer=invoke(a,tmp_path,ns,'2026-09-29',dict(confirmation=True),None,0)
    r1,one,consumer=invoke(a,tmp_path,ns,'2026-09-30',dict(confirmation=True),prior,1)
    o.cross_process(producer,consumer);assert o.manifest(tmp_path,read(tmp_path,r1))
    r2,two,second=invoke(a,tmp_path,ns,'2026-09-30',dict(confirmation=True),prior,2,'r2')
    repeat,three,third=invoke(a,tmp_path,ns,'2026-09-30',dict(confirmation=True),prior,3)
    assert r1==repeat and consumer['pid']!=third['pid']
    x=read(tmp_path,r1);y=read(tmp_path,r2);assert x['previous_state_publication']==y['previous_state_publication']==prior
    assert x['output']['d2']['rows']==y['output']['d2']['rows']
    assert x['output']['logical_events']==y['output']['logical_events']
    assert x['output']['events'][0]['primary_event']=='PERSISTENT_CONFIRMED'
