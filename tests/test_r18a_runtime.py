"""Every frozen case executes; persistence rejects changed-byte overwrite."""
from pathlib import Path
import json
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import pytest
from workbench_analysis.v4_14_authority import ReplayAuthority
from workbench_analysis.v4_14_replay_runtime import ReplayRuntime
from workbench_analysis.v4_14_replay_io import publish,exact,digest
ROOT=Path(__file__).resolve().parents[1]
BOOK=json.loads((ROOT/'config/v4_14_machine_vectors_v1_1.json').read_bytes())
@pytest.fixture(scope='module')
def runtime():return ReplayRuntime(ReplayAuthority(ROOT))
@pytest.mark.parametrize('vector',BOOK['vectors'],ids=lambda v:v['id'])
def test_frozen_case_executes_with_literal_expectation(runtime,vector):assert runtime.evaluate_case(vector['dimension'],vector['input'])==vector['expected']
def test_atomic_append_only_and_concurrent_same_bytes(tmp_path):
    with ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:publish(tmp_path,'replay/r1.json',{'state':'UNKNOWN'}),range(8)))
    assert len({r['sha256'] for r in results})==1
    before=exact(tmp_path,results[0])
    with pytest.raises(ValueError,match='OVERWRITE'):publish(tmp_path,'replay/r1.json',{'state':'FALSE'})
    assert exact(tmp_path,results[0])==before
def test_exact_ref_and_path_escape_fail_closed(tmp_path):
    r=publish(tmp_path,'replay/r1.json',{'a':1});r['sha256']='0'*64
    with pytest.raises(ValueError):exact(tmp_path,r)
    with pytest.raises(ValueError):publish(tmp_path,'../outside.json',{})
def test_previous_uses_accepted_market_calendar(runtime):assert runtime.authority.previous('2026-09-28')=='2026-09-24'
