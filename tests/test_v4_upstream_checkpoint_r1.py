"""Synthetic layer negatives; never source or publication acceptance."""
import hashlib,json
from pathlib import Path
import pytest
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.operational_upstream_checkpoint_r1 import install
from workbench_analysis.operational_daily_exact_policy_v2 import verify_loaded_versions
from workbench_analysis import exact_operational_core_candidate_r3 as algorithm

def fixture(root):
    old=root/'old';new=root/'new';old.mkdir();new.mkdir()
    generation=dict(source_freeze='freeze',parent_head='head',identity='identity',gbbq='gbbq',member_sources={},adjustment_contract={'contract':'exact'})
    for folder in (old,new):(folder/'GENERATION_SCOPE.json').write_text(json.dumps(generation))
    dates=['2026-10-12']
    docs={'CORE_REPLAY.json':dict(owners=[{'trade_date':dates[0]}],oracle=[dict(result='PASS',errors=[])]),
        'PROFILE_STRUCTURE_REPLAY.json':dict(owners=[{'owner':{'trade_date':dates[0]}}])}
    for name,value in docs.items():(old/name).write_text(json.dumps(value))
    policy=root/'policy.json';policy.write_text(json.dumps({'accepted_algorithm_bindings':[]}))
    checkpoint=dict(contract_id='V4_EXACT_CORE_PROFILE_REUSABLE_CHECKPOINT_R1',publication=False,original_generation=ref(root,old/'GENERATION_SCOPE.json'),completed_dates=dates,unchanged_component_sources=[],documents={name:ref(root,old/name) for name in docs})
    path=root/'checkpoint.json';path.write_text(json.dumps(checkpoint))
    return dict(folder=new,dates=dates,exact_daily_policy=ref(root,policy)),path


@pytest.mark.parametrize('mutation',['none','input','coordinate','oracle','dates','producer'])
def test_sector_checkpoint_rejects_changed_inputs_or_unverified_output(tmp_path,mutation):
    context,path=fixture(tmp_path)
    checkpoint=json.loads(path.read_bytes())
    generation=json.loads((context['folder']/'GENERATION_SCOPE.json').read_bytes())
    if mutation=='input':generation['gbbq']='changed'
    if mutation=='coordinate':generation['adjustment_contract']['contract']='changed'
    original=tmp_path/'sector_generation.json';original.write_text(json.dumps(generation))
    document=tmp_path/'sector.json'
    document.write_text(json.dumps(dict(owners=[dict(trade_date='changed' if mutation=='dates' else '2026-10-12')],oracle=[dict(passed=mutation!='oracle')])))
    producer=Path(algorithm.__file__).resolve()
    checkpoint['completed_sector']=dict(generation=ref(tmp_path,original),document=ref(tmp_path,document),
        producer=dict(module_path='src/workbench_analysis/exact_operational_core_candidate_r3.py',
            sha256='changed' if mutation=='producer' else hashlib.sha256(producer.read_bytes()).hexdigest()))
    path.write_text(json.dumps(checkpoint))
    if mutation=='none':
        receipt=install(tmp_path,context,ref(tmp_path,path))
        assert receipt['sector_reused'] and receipt['publication'] is False
        assert (context['folder']/'sector_v3/SECTOR_REPLAY.json').is_file()
    else:
        with pytest.raises(ValueError):install(tmp_path,context,ref(tmp_path,path))

@pytest.mark.parametrize('mutation',['none','input','coordinate','artifact','numeric','dates'])
def test_reuse_conserves_inputs_and_bound_outputs(tmp_path,mutation):
    context,path=fixture(tmp_path)
    if mutation in ('input','coordinate'):
        p=context['folder']/'GENERATION_SCOPE.json';x=json.loads(p.read_bytes())
        if mutation=='input':x['gbbq']='changed'
        else:x['adjustment_contract']['contract']='rounded'
        p.write_text(json.dumps(x))
    elif mutation=='artifact':(tmp_path/'old/CORE_REPLAY.json').write_bytes(b'tampered')
    elif mutation=='dates':context['dates']=['2026-10-13']
    elif mutation=='numeric':
        p=tmp_path/'old/CORE_REPLAY.json';x=json.loads(p.read_bytes());x['oracle'][0]['errors']=['real failure'];p.write_text(json.dumps(x))
        x=json.loads(path.read_bytes());x['documents']['CORE_REPLAY.json']=ref(tmp_path,p);path.write_text(json.dumps(x))
    if mutation=='none':
        result=install(tmp_path,context,ref(tmp_path,path));assert result['numerical_recomputed'] is False and result['publication'] is False
    else:
        with pytest.raises(ValueError):install(tmp_path,context,ref(tmp_path,path))
        assert not (context['folder']/'CORE_PROFILE_REUSE_RECEIPT_R1.json').exists()

def test_loaded_source_identity_rejects_archive_only_claim():
    source=Path(algorithm.__file__)
    binding=dict(path='unused/archive.py',module_path='src/workbench_analysis/exact_operational_core_candidate_r3.py',sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    verify_loaded_versions([binding]);binding['sha256']='0'*64
    with pytest.raises(ValueError,match='LOADED_ALGORITHM_VERSION_MISMATCH'):verify_loaded_versions([binding])
