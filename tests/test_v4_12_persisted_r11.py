"""Persistence boundaries, exact readback and immutable revision rejection."""
import json,gzip,tempfile
from pathlib import Path
import pytest
from scripts.v4_11_promotion_contract_r1 import ROOT
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore,exact_json,digest
from workbench_analysis.v4_12_input_binder import InputBinder
from workbench_analysis.v4_12_frozen_snapshot import FrozenSnapshotLoader

C=FrozenContracts(ROOT)
BASE='reports/v4_12_runtime_r11/a_persisted_chain_synthetic/2026-09-29/r1/'
REF=json.loads((ROOT/(BASE+'snapshot_ref.json')).read_bytes())

def test_exact_prior_bundle_security_row():
    b=InputBinder(C,'2026-09-30','2026-10-02T06:00:00+00:00');row,ref=b.prior({'frozen_manifest':REF},'SYNTHETIC')
    assert row['trade_date']=='2026-09-29' and ref['row_digest']==digest(row)
    assert row['counter_state']['post_creation_evaluable_sessions']==2

@pytest.mark.parametrize('date',['2026-09-29','2026-09-28'])
def test_same_day_and_future_session_rejected(date):
    with pytest.raises(ValueError,match='SAME_DAY_OR_FOREIGN_PRIOR_D1'):
        InputBinder(C,date,'2026-10-02T06:00:00+00:00').prior({'frozen_manifest':REF},'SYNTHETIC')

def test_future_availability_rejected():
    with pytest.raises(ValueError,match='FUTURE_SOURCE'):FrozenSnapshotLoader(C,REF,'2026-09-30T00:00:00+00:00')

def test_exact_security_required():
    with pytest.raises(ValueError,match='MISSING_FROZEN_SECURITY_ROW'):FrozenSnapshotLoader(C,REF,'2026-10-02T06:00:00+00:00').read('OTHER','2026-09-29')

@pytest.mark.parametrize('mutation',['manifest','bundle','row','lineage','counter'])
def test_tampering_rejected(mutation):
    (ROOT/'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
        store=CandidateStore(ROOT,Path(directory).relative_to(ROOT).as_posix());m=exact_json(ROOT,REF)
        if mutation=='manifest':ref={**REF,'sha256':'0'*64}
        else:
            if mutation=='lineage':m['formal_accepted']=True
            else:
                rows=[json.loads(x) for x in gzip.decompress((ROOT/m['snapshot_bundle']['path']).read_bytes()).splitlines()]
                if mutation=='bundle':m['snapshot_bundle']['sha256']='0'*64
                else:
                    rows[0]['counter_state']['held_count']=99
                    if mutation=='counter':
                        index={'rows':{'SYNTHETIC':{'row_digest':digest(rows[0])}}};m['security_index']=store.json('index.json',index)
                    m['snapshot_bundle']=store.jsonl('bundle.jsonl.gz',rows,True)
            ref=store.json('manifest.json',m)
        with pytest.raises((ValueError,AssertionError)):
            FrozenSnapshotLoader(C,ref,'2026-10-02T06:00:00+00:00').read('SYNTHETIC','2026-09-29')

def test_snapshot_revision_conflict_is_rejected():
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
        store=CandidateStore(ROOT,Path(directory).relative_to(ROOT).as_posix());a=store.json('snapshot.json',{'held_count':1})
        assert a==store.json('snapshot.json',{'held_count':1})
        with pytest.raises(ValueError,match='IMMUTABLE_REVISION_CONFLICT'):store.json('snapshot.json',{'held_count':2})

def test_persisted_independent_a_oracle():
    from scripts.validate_v4_12_r11_chain import validate
    assert validate('a')['status']=='PASS'

def test_persisted_independent_b_oracle():
    from scripts.validate_v4_12_r11_chain import validate
    assert validate('b')['status']=='PASS'

def test_projection_known_missing_resume_and_hard_invalidation():
    from scripts.verify_v4_12_r11_projection_paths import validate
    assert validate()['status']=='PASS'

def test_new_anchor_retest_zero_and_same_day_predecessor_isolated():
    base=ROOT/'reports/v4_12_runtime_r11/b_closure_chain_synthetic'
    first=json.loads(gzip.decompress((base/'2026-09-23/r1/runtime_observations.jsonl.gz').read_bytes()))
    assert first['frozen_output_envelope']['retest_count']==0 and first['outputs']['support']['state']=='IDLE'
    rows=[json.loads(gzip.decompress((base/f'2026-09-29/{revision}/runtime_observations.jsonl.gz').read_bytes())) for revision in ['r1','r2','r3']]
    assert rows[0]['prior_state_ref']==rows[1]['prior_state_ref']==rows[2]['prior_state_ref']
    assert all(r['frozen_output_envelope']['retest_count']==1 for r in rows)

def test_fresh_process_quality_correction_does_not_accumulate_revisions():
    from scripts.verify_v4_12_r11_revision_correction import validate
    assert validate()['independent_expected']==[2,1,2]
