from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from copy import deepcopy
import json,hashlib
import pytest
from workbench_analysis import dm01_publication_history_reader_v1 as old
from workbench_analysis import dm01_publication_history_reader_v2 as new
from workbench_analysis.dm01_accepted_chain_v1 import HEAD_PATH,ANCHOR_SHA

ROOT=Path(__file__).resolve().parents[2]

def test_exact_outputs_and_two_history_plus_current_concurrency():
    from scripts import promote_v4_09_accepted_head as v9,validate_v4_10_promotion_r1 as v10
    original=(v9.ROOT,v10.ROOT)
    before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['scripts/promote_v4_09_accepted_head.py','scripts/validate_v4_10_promotion_r1.py','src/workbench_analysis/dm01_publication_history_reader_v1.py',HEAD_PATH]}
    expected9=old.validate_v4_09_history();expected10=old.validate_v4_10_history()
    barrier=Barrier(3)
    def run(which):
        barrier.wait()
        if which==9:return new.validate_v4_09_history(project_root=ROOT)
        if which==10:return new.validate_v4_10_history(project_root=ROOT)
        return v10.validate()
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(run,x) for x in [9,10,0]];results=[f.result() for f in jobs]
    assert results[0]==expected9 and results[1]==expected10
    assert results[2]['status']=='FAIL' and results[2]['checks']['P19_protected']=='FAIL'
    assert (v9.ROOT,v10.ROOT)==original
    assert json.loads((ROOT/HEAD_PATH).read_bytes())['accepted_trade_date']=='2026-09-30'
    assert before=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in before}

def test_wrong_candidate_hash_behavior_exact():
    from scripts import validate_v4_10_promotion_r1 as v10
    candidate=json.loads((ROOT/v10.CANDIDATE).read_bytes());candidate['protected_head_bindings']=deepcopy(candidate['protected_head_bindings'])
    candidate['protected_head_bindings'][0]['sha256']='0'*64
    assert old.validate_v4_10_history(candidate)==new.validate_v4_10_history(candidate,project_root=ROOT)
    assert new.validate_v4_10_history(candidate,project_root=ROOT)['status']=='FAIL'

def test_exact_view_cannot_arbitrarily_remap_or_wrong_sha():
    view=new.HistoricalBindingResolver(ROOT)
    assert view.resolve(HEAD_PATH,ANCHOR_SHA).read_bytes()==(ROOT/'data/v4/data_head_archive/V4_DATA_ACCEPTED_HEAD_20260924_ORIGINAL_BYTES_R1.json').read_bytes()
    for path,sha in [(HEAD_PATH,'0'*64),('../outside.json',None),('data/v4/../../outside.json',None),('C:/outside.json',None)]:
        with pytest.raises(ValueError):view.resolve(path,sha)
    current=ROOT/'data/v4/V4_10_ACCEPTED_HEAD.json'
    assert view.resolve('data/v4/V4_10_ACCEPTED_HEAD.json')==current

def test_candidate_cannot_masquerade_as_accepted_archive(tmp_path):
    h=json.loads((ROOT/HEAD_PATH).read_bytes());h['parent_archive']['path']='candidate.json'
    (tmp_path/HEAD_PATH).parent.mkdir(parents=True);(tmp_path/HEAD_PATH).write_text(json.dumps(h))
    (tmp_path/'candidate.json').write_text('{"accepted_trade_date":"2026-09-24"}')
    with pytest.raises((ValueError,OSError)):new.HistoricalBindingResolver(tmp_path)
