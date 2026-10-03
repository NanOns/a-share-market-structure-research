from pathlib import Path
from copy import deepcopy
import json,hashlib
import pytest
from workbench_analysis import historical_stage_governance_r17 as g
from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
ROOT=Path(__file__).resolve().parents[1]
def test_dm01_exact_promotion_state_and_current_state():
    head=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    assert validate_head_v2(ROOT,head)['status']=='PASS'
    archive=g.resolve(ROOT,head['stage_head'])
    assert json.loads(archive.read_bytes())['accepted_stage_range']=='V4_00_TO_V4_10_ACCEPTED'
    assert g.current_state(ROOT)['status']=='PASS'
@pytest.mark.parametrize('mutation',['missing','hash','range','current_archive','current_binding','bytes'])
def test_historical_negatives_fail_closed(tmp_path,monkeypatch,mutation):
    book=deepcopy(g.registry(ROOT));row=next(row for row in book['entries'] if row['accepted_stage_range']=='V4_00_TO_V4_10_ACCEPTED');ref=deepcopy(row['original_namespace'])
    target=tmp_path/row['archive']['path'];target.parent.mkdir(parents=True);target.write_bytes((ROOT/row['archive']['path']).read_bytes())
    monkeypatch.setattr(g,'registry',lambda root:book)
    # Keep Git source verification tied to the actual recorded commit, even for a fixture root.
    original=g.subprocess.check_output
    monkeypatch.setattr(g.subprocess,'check_output',lambda args,**kw:original(args,cwd=ROOT))
    if mutation=='missing':target.unlink()
    if mutation=='hash':target.write_bytes(target.read_bytes()+b' ')
    if mutation=='range':row['accepted_stage_range']='V4_00_TO_V4_12_ACCEPTED'
    if mutation=='current_archive':row['archive']=dict(ref)
    if mutation=='current_binding':ref['sha256']=hashlib.sha256((ROOT/g.STAGE).read_bytes()).hexdigest()
    if mutation=='bytes':ref['bytes']+=1
    with pytest.raises(g.HistoricalBindingError):g.resolve(tmp_path,ref)
def test_historical_head_cannot_be_rebound_to_current_stage():
    head=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    raw=(ROOT/g.STAGE).read_bytes();head['stage_head'].update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));head['stage_accepted_head_sha256']=head['stage_head']['sha256']
    with pytest.raises(g.HistoricalBindingError):validate_head_v2(ROOT,head)
@pytest.mark.parametrize('mutation',['missing_archive','archive_sha','current_content','binding_sha'])
def test_static_byte_representation_never_hides_content_changes(tmp_path,monkeypatch,mutation):
    book=deepcopy(g.registry(ROOT));row=book['static_byte_archives'][0];ref=deepcopy(row['original_namespace'])
    for path in [row['archive']['path'],ref['path']]:
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/row['archive']['path']).read_bytes() if path==row['archive']['path'] else (ROOT/ref['path']).read_bytes())
    monkeypatch.setattr(g,'registry',lambda root:book)
    original=g.subprocess.check_output
    monkeypatch.setattr(g.subprocess,'check_output',lambda args,**kw:original(args,cwd=ROOT))
    assert g.accepted_static_binding(tmp_path,ref).read_bytes()==(ROOT/row['archive']['path']).read_bytes()
    if mutation=='missing_archive':(tmp_path/row['archive']['path']).unlink()
    if mutation=='archive_sha':(tmp_path/row['archive']['path']).write_bytes(b'{}')
    if mutation=='current_content':(tmp_path/ref['path']).write_bytes(b'{}')
    if mutation=='binding_sha':ref['sha256']='0'*64
    with pytest.raises(g.HistoricalBindingError):g.accepted_static_binding(tmp_path,ref)
def test_protected_heads_unchanged_at_r17a():
    contract=json.loads((ROOT/'reports/r17a/stage_contract.json').read_bytes())
    for ref in contract['protected'].values():
        if ref['path']==g.STAGE and g.current_state(ROOT)['stage_range']=='V4_00_TO_V4_13_ACCEPTED':
            # Later B is independently authorized; its exact immutable parent is still the A baseline.
            head=json.loads((ROOT/'data/v4/V4_13_ACCEPTED_HEAD.json').read_bytes());g.exact(ROOT,head['global_head_parent_archive'])
            assert head['global_head_parent']['sha256']==ref['sha256']
        else:g.exact(ROOT,ref)
