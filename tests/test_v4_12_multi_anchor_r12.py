"""Contract V2, cardinality, deterministic selector and persisted ownership gates."""
from copy import deepcopy
import gzip,json,tempfile
from pathlib import Path
import pytest
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_snapshot_v2_contract import gate,validate_shape
from scripts.verify_v4_12_r12_selector_vectors import run as selector_vectors
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore,digest
from workbench_analysis.v4_12_frozen_snapshot_v2 import load_contract,FrozenSnapshotLoaderV2,InputBinderV2
from workbench_analysis.v4_12_multi_anchor_state import validate_state_set,active_selector
from workbench_analysis.v4_12_multi_anchor_engine import MultiAnchorEngine
from scripts.run_v4_12_r12_day import SyntheticBinderV2,CUTOFF

C=FrozenContracts(ROOT);CONTRACT,_=load_contract(C)
REF=json.loads((ROOT/'reports/v4_12_runtime_r12/final_synthetic/2026-09-29/r1/snapshot_ref.json').read_bytes())
ROWS=selector_vectors()['rows']

@pytest.mark.parametrize('row',ROWS,ids=lambda r:r['id'])
def test_independent_selector_vectors(row):assert row['status']=='PASS'

def test_contract_local_gate_and_negative_vectors():assert len(gate()['negative_vectors'])==8

def test_v2_loader_retains_all_four_episodes():
    row,ref=FrozenSnapshotLoaderV2(C,REF,CUTOFF).read('SYNTHETIC','2026-09-29')
    assert len(row['anchor_states'])==4 and ref['row_digest']==digest(row)

@pytest.mark.parametrize('date',['2026-09-29','2026-09-28'])
def test_same_day_and_future_set_rejected(date):
    with pytest.raises(ValueError,match='SAME_DAY_OR_FOREIGN_PRIOR_D1'):InputBinderV2(C,date,CUTOFF).prior({'frozen_manifest_v2':REF},'SYNTHETIC')

def test_v1_cannot_be_r12_formal_candidate_source():
    old=json.loads((ROOT/'reports/v4_12_runtime_r11/b_closure_chain_synthetic/2026-09-29/r1/snapshot_ref.json').read_bytes())
    with pytest.raises(ValueError,match='V2_PRIOR_MANIFEST_REQUIRED'):FrozenSnapshotLoaderV2(C,old,CUTOFF)
    with pytest.raises(ValueError,match='V2_PRIOR_MANIFEST_REQUIRED'):InputBinderV2(C,'2026-09-30',CUTOFF).prior({'frozen_manifest':old},'SYNTHETIC')

def test_common_F0_bind_once_and_all_prior_overlays_evaluated():
    engine=MultiAnchorEngine(C,'2026-09-30',CUTOFF);fixture=json.loads((ROOT/'reports/v4_12_runtime_r12/fixtures/closure/2026-09-30.json').read_bytes());engine.binder=SyntheticBinderV2(C,'2026-09-30',fixture)
    result=engine.evaluate('SYNTHETIC',{'frozen_manifest_v2':REF})
    assert engine.binder.calls==1 and len(result['anchor_states'])==len(result['contexts'])==4
    ids={s['anchor_id'] for s in result['anchor_states']}
    assert all(o['outputs']['support']['anchor_ref']['anchor_id'] in ids for o in result['contexts'])

@pytest.mark.parametrize('mutation',['duplicate','owning','event','counter','new_self_confirm','scalar'])
def test_state_set_rejects_cardinality_and_ownership_mutation(mutation):
    row,_=FrozenSnapshotLoaderV2(C,REF,CUTOFF).read('SYNTHETIC','2026-09-29');r=deepcopy(row)
    state=next(s for s in r['anchor_states'] if s['created_this_session'])
    if mutation=='duplicate':r['anchor_states'].append(deepcopy(state))
    elif mutation=='owning':state['owning_anchor_id']='OTHER'
    elif mutation=='event':state['event']['anchor_id']='OTHER'
    elif mutation=='counter':state['counter_state']['test_count']=99
    elif mutation=='scalar':r.pop('anchor_states');r['anchor']=state['anchor']
    else:state['counter_state']['held_count']=1;state['counter_state_digest']=digest(state['counter_state'])
    with pytest.raises(ValueError):validate_state_set(CONTRACT,r)

def test_active_sole_bad_coordinate_direct_multiple_unknown_not_first():
    book=json.loads((ROOT/'config/v4_12_active_selector_vectors_r12.json').read_bytes())['vectors']
    single=next(v for v in book if v['id']=='SOLE_BAD_COORDINATE');multiple=next(v for v in book if v['id']=='UNKNOWN_COORDINATE')
    assert active_selector(CONTRACT,C,single['states'],single['common'],'2026-09-30','r1')['active_anchor_id']=='A'
    assert active_selector(CONTRACT,C,multiple['states'],multiple['common'],'2026-09-30','r1')['reason']=='ACTIVE_ANCHOR_SELECTION_UNKNOWN'

def test_immutable_revision_rerun_and_conflict():
    (ROOT/'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
        store=CandidateStore(ROOT,Path(directory).relative_to(ROOT).as_posix());first=store.json('snapshot.json',{'anchor_states':['A','B']})
        assert first==store.json('snapshot.json',{'anchor_states':['A','B']})
        with pytest.raises(ValueError,match='IMMUTABLE_REVISION_CONFLICT'):store.json('snapshot.json',{'anchor_states':['A']})

def test_full_independent_persisted_multi_anchor_oracle():
    from scripts.validate_v4_12_r12_runtime import validate
    assert validate()['status']=='PASS'
