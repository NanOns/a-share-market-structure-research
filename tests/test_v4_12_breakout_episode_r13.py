"""Episode boundary, exact persistence and independently specified path regression."""
import json,gzip
from copy import deepcopy
import pytest
from scripts.v4_11_promotion_contract_r1 import ROOT
from workbench_analysis.v4_12_structure_io import FrozenContracts,digest
from workbench_analysis.v4_12_breakout_episode import BreakoutEpisodeEngine,validate_episodes
from workbench_analysis.v4_12_breakout_snapshot import EpisodeSnapshotLoader,EpisodeBinder
from scripts.run_v4_12_r13_day import SyntheticBinderEpisode,CUTOFF
from scripts.validate_v4_12_r13_runtime import EXPECTED,load,OUT

@pytest.mark.parametrize('name',list(EXPECTED))
def test_literal_persisted_paths(name):
    for date,rev,state,count in EXPECTED[name]:
        r=load(OUT+'synthetic/'+name+'/'+date+'/'+rev)['runs'][0]
        assert r['basic_breakout_state']==state and len(r['breakout_episodes'])==count

@pytest.mark.parametrize('mutation',['alias','duplicate','no_prior','self_confirm','bad_id','multiple_active'])
def test_episode_shape_rejects(mutation):
    row=deepcopy(load(OUT+'synthetic/holds/2026-09-24/r1')['rows'][0]);e=row['breakout_episodes'][0]
    if mutation=='alias':e['owning_anchor_id']='active_anchor'
    elif mutation=='duplicate':row['breakout_episodes'].append(deepcopy(e))
    elif mutation=='no_prior':e['prior_episode_ref']=None
    elif mutation=='self_confirm':e['created_trade_date']=row['trade_date'];e['state']='BREAKOUT_ACCEPTED'
    elif mutation=='bad_id':e['breakout_episode_id']='invalid'
    else:row['active_breakout_episode_id']='wrong'
    with pytest.raises(ValueError):validate_episodes(row)

def test_unknown_absence_is_not_false():
    c=FrozenContracts(ROOT);engine=BreakoutEpisodeEngine(c,'2026-09-23',CUTOFF)
    fixture=json.loads((ROOT/(OUT+'fixtures/holds/2026-09-23/r1.json')).read_bytes());engine.binder=SyntheticBinderEpisode(c,'2026-09-23',fixture)
    r=engine.evaluate('SYNTHETIC')
    assert r['basic_breakout_state']=='UNKNOWN' and r['breakout_episode_set_quality']=='UNKNOWN' and not r['breakout_episodes'] and not r['anchors'] and engine.binder.calls==1

def test_unknown_evaluability_cannot_bypass_machine_with_true_trigger():
    c=FrozenContracts(ROOT);engine=BreakoutEpisodeEngine(c,'2026-09-23',CUTOFF,engineering_empty_seed=True)
    fixture=json.loads((ROOT/(OUT+'fixtures/holds/2026-09-23/r1.json')).read_bytes());fixture['values']['evaluable']=None
    engine.binder=SyntheticBinderEpisode(c,'2026-09-23',fixture);r=engine.evaluate('SYNTHETIC')
    assert r['basic_breakout_state']=='UNKNOWN' and not r['breakout_episodes'] and not r['anchors']

def test_exact_previous_session_and_same_day_rejection():
    c=FrozenContracts(ROOT);ref=json.loads((ROOT/(OUT+'synthetic/holds/2026-09-23/r1/snapshot_ref.json')).read_bytes());loader=EpisodeSnapshotLoader(c,ref,CUTOFF)
    row,prior=loader.read('SYNTHETIC','2026-09-23');assert prior['row_digest']==digest(row)
    with pytest.raises(ValueError,match='SAME_DAY_OR_FOREIGN'):loader.read('SYNTHETIC','2026-09-24')
    with pytest.raises(ValueError):EpisodeBinder(c,'2026-09-24',CUTOFF).prior(dict(frozen_manifest_v2=ref),'SYNTHETIC')

def test_corrected_revisions_are_not_predecessors():
    rows=[load(OUT+'synthetic/revisions/2026-09-24/'+r)['rows'][0] for r in ['r1','r2','r3']]
    assert rows[0]['breakout_episodes'][0]['prior_episode_ref']==rows[1]['breakout_episodes'][0]['prior_episode_ref']==rows[2]['breakout_episodes'][0]['prior_episode_ref']
    assert [r['breakout_episodes'][0]['state'] for r in rows]==['TESTING','UNKNOWN','BREAKOUT_TENTATIVE']

def test_no_second_breakout_rules():
    c=FrozenContracts(ROOT)
    from workbench_analysis.v4_12_ast_runtime import ASTEngine
    for name in ['holds','retained','terminal','duplicate']:
        for date,rev,state,_ in EXPECTED[name]:
            run=load(OUT+'synthetic/'+name+'/'+date+'/'+rev)['runs'][0]
            assert ASTEngine(c.config,run['breakout_input_bindings']).target('breakout').value==state
