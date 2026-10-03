import json
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.v4_14_rollback_oracle import RollbackOracle
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def evidence():return RollbackOracle(ROOT),json.loads((ROOT/'reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json').read_bytes())
def test_eight_actual_sandbox_scenarios(evidence):
    o,r=evidence;assert o.validate(r)
@pytest.mark.parametrize('mutation',['wrong_predecessor_sha','wrong_predecessor_bytes','wrong_candidate_sha','candidate_missing','activation_with_stale_parent','rollback_to_wrong_parent','rollback_receipt_drops_reason_codes','rollback_receipt_drops_previous_head','rollback_receipt_claims_v4_14_accepted','rollback_receipt_claims_algorithm_replay_pass','rollback_deletes_candidate_evidence','rollback_mutates_real_stage_head','second_rollback_changes_bytes','sandbox_path_escape'])
def test_mandatory_rollback_mutations(evidence,mutation):
    o,r=evidence;r=deepcopy(r)
    if mutation=='wrong_predecessor_sha':r['previous_accepted_head']['sha256']='0'*64
    elif mutation=='wrong_predecessor_bytes':r['previous_accepted_head']['bytes']+=1
    elif mutation=='wrong_candidate_sha':r['candidate_seal']['sha256']='0'*64
    elif mutation=='candidate_missing':r['candidate_seal']['path']='reports/missing_candidate.json'
    elif mutation=='activation_with_stale_parent':r['scenarios'][1]['cas_expected']['sha256']='0'*64
    elif mutation=='rollback_to_wrong_parent':r['scenarios'][1]['first_rollback_snapshot']=r['scenarios'][1]['activation']
    elif mutation=='rollback_receipt_drops_reason_codes':r.pop('reason_codes')
    elif mutation=='rollback_receipt_drops_previous_head':r.pop('previous_accepted_head')
    elif mutation=='rollback_receipt_claims_v4_14_accepted':r['V4_14_ACCEPTED_HEAD']='CREATED'
    elif mutation=='rollback_receipt_claims_algorithm_replay_pass':r['ALGORITHM_STATE_REPLAY_PASS']='PASS'
    elif mutation=='rollback_deletes_candidate_evidence':r['candidate_artifacts_preserved'].pop()
    elif mutation=='rollback_mutates_real_stage_head':r['protected_heads_after'][-1]['sha256']='0'*64
    elif mutation=='second_rollback_changes_bytes':r['scenarios'][1]['second_rollback_snapshot']=r['scenarios'][1]['activation']
    elif mutation=='sandbox_path_escape':r['scenarios'][1]['sandbox_path']='data/v4'
    with pytest.raises(ValueError):o.validate(r)
@pytest.mark.parametrize('permission',['production','shadow','focus','V4_15','Stage_advance','Data_advance'])
def test_no_permission_grant(evidence,permission):
    o,r=evidence;r=deepcopy(r);r[permission]=True
    with pytest.raises(ValueError):o.validate(r)
def test_oracle_does_not_import_rollback_implementation():
    text=(ROOT/'scripts/v4_14_rollback_oracle.py').read_text();assert 'v4_14_candidate_rollback_drill' not in text and 'Sandbox(' not in text

@pytest.fixture
def box(tmp_path):
    from workbench_analysis.v4_14_candidate_rollback_drill import Sandbox
    from workbench_analysis.v4_13_io import atomic,file_ref
    atomic(tmp_path,'parent.json',b'{"accepted_stage_range":"V4_00_TO_V4_13_ACCEPTED"}\n',True)
    atomic(tmp_path,'candidate.json',b'{"candidate_only":true}\n',True)
    return Sandbox(tmp_path,'reports/r18r1r1r1a/sandbox/unit',file_ref(tmp_path,'parent.json'),file_ref(tmp_path,'candidate.json'),[])

def test_actual_stale_head_cas_rejects_without_overwrite(box):
    p=box.root/box.head;p.write_bytes(b'stale')
    with pytest.raises(ValueError,match='STALE_PREDECESSOR'):box.activate()
    assert p.read_bytes()==b'stale'

def test_actual_evidence_mutation_blocks_rollback(box):
    box.activate();before=(box.root/box.head).read_bytes();(box.root/box.candidate['path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='DIGEST'):box.rollback()
    assert (box.root/box.head).read_bytes()==before

def test_rollback_rejects_unrelated_current_head(box):
    box.activate();p=box.root/box.head;p.write_bytes(b'unrelated')
    with pytest.raises(ValueError,match='CURRENT_HEAD_CAS'):box.rollback()
    assert p.read_bytes()==b'unrelated'

def test_sandbox_escape_rejected_before_creation(box):
    from workbench_analysis.v4_14_candidate_rollback_drill import Sandbox
    with pytest.raises(ValueError,match='PATH_ESCAPE'):Sandbox(box.root,'reports/r18r1r1r1a/sandbox/../../../../data/v4',box.parent,box.candidate,[])
