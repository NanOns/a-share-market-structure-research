import pytest
from validation.phase0_2b import FrozenRun, read_frozen, atomic

def test_no_overwrite_or_postfreeze_write(tmp_path):
    run = FrozenRun(tmp_path/'reports',tmp_path/'tdx')
    run.put('success.json', {'v':1})
    with pytest.raises(FileExistsError):
        run.put('success.json', {'v':0})
    run.freeze()
    with pytest.raises(FileExistsError):
        run.put('later.json', {})
    later = FrozenRun(tmp_path/'reports',tmp_path/'tdx')
    assert later.path != run.path
    assert read_frozen(run.path,'success.json') == {'v':1}

def test_tamper_and_source_write_rejected(tmp_path):
    run = FrozenRun(tmp_path/'reports',tmp_path/'tdx')
    run.put('data.json',{})
    run.freeze()
    (run.path/'data.json').write_text('null')
    with pytest.raises(ValueError):
        read_frozen(run.path,'data.json')
    with pytest.raises(ValueError):
        atomic(tmp_path/'tdx'/'file',b'bad',tmp_path/'tdx')
