from copy import deepcopy
from pathlib import Path
import json
import pytest
from workbench_analysis.parallel_scoped_acceptance_r1 import (
    PROTECTED_REPRESENTATIONS,validate_protected_binding,validate_record,record_path,
)

ROOT=Path(__file__).resolve().parents[2]

def metadata():return json.loads((ROOT/PROTECTED_REPRESENTATIONS['path']).read_bytes())

def write(root,path,raw):
    target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)

def clean_representation(root,index):
    write(root,PROTECTED_REPRESENTATIONS['path'],(ROOT/PROTECTED_REPRESENTATIONS['path']).read_bytes())
    row=metadata()['representations'][index]
    original=(ROOT/row['original_bytes_archive']['path']).read_bytes()
    write(root,row['original_bytes_archive']['path'],original)
    write(root,row['git_representation']['path'],original.replace(b'\r\n',b'\n'))
    return deepcopy(row)

@pytest.mark.parametrize('index',[0,1])
def test_actual_pinned_lf_clean_checkout_representation(index,tmp_path):
    row=clean_representation(tmp_path,index)
    result=validate_protected_binding(tmp_path,row['original_binding'])
    assert result==tmp_path/row['original_bytes_archive']['path']
    assert result.read_bytes()==(ROOT/row['original_bytes_archive']['path']).read_bytes()
    assert (tmp_path/row['git_representation']['path']).read_bytes()==result.read_bytes().replace(b'\r\n',b'\n')

@pytest.mark.parametrize('index',[0,1])
@pytest.mark.parametrize('fault',['current_bytes','archive_bytes','metadata_bytes','caller_hash','caller_size','caller_path','archive_removed'])
def test_no_unregistered_or_rewritten_representation(index,fault,tmp_path):
    row=clean_representation(tmp_path,index);ref=row['original_binding']
    if fault=='current_bytes':write(tmp_path,row['git_representation']['path'],(tmp_path/row['git_representation']['path']).read_bytes()+b'\n')
    elif fault=='archive_bytes':write(tmp_path,row['original_bytes_archive']['path'],(tmp_path/row['original_bytes_archive']['path']).read_bytes()+b'\n')
    elif fault=='metadata_bytes':
        document=metadata();document['representations'][index]['git_representation']['sha256']='0'*64
        write(tmp_path,PROTECTED_REPRESENTATIONS['path'],json.dumps(document).encode('utf8'))
    elif fault=='caller_hash':ref['sha256']='0'*64
    elif fault=='caller_size':ref['bytes']+=1
    elif fault=='caller_path':ref['path']='data/v4/OTHER_HEAD.json'
    elif fault=='archive_removed':(tmp_path/row['original_bytes_archive']['path']).unlink()
    with pytest.raises((ValueError,OSError)):validate_protected_binding(tmp_path,ref)

def test_other_modified_protected_file_has_no_fallback(tmp_path):
    from hashlib import sha256
    raw=b'{"original":true}\r\n';ref=dict(path='data/v4/V4_STAGE_ACCEPTED_HEAD.json',sha256=sha256(raw).hexdigest(),bytes=len(raw))
    write(tmp_path,ref['path'],raw.replace(b'\r\n',b'\n'))
    write(tmp_path,PROTECTED_REPRESENTATIONS['path'],(ROOT/PROTECTED_REPRESENTATIONS['path']).read_bytes())
    with pytest.raises(ValueError):validate_protected_binding(tmp_path,ref)

def test_runtime_and_evidence_do_not_use_protected_representation_resolver():
    record=json.loads((ROOT/record_path('A03')).read_bytes());original=metadata()['representations'][0]['original_binding']
    record['runtime_bindings'][0]=original
    # The current workspace can retain original CRLF bytes; force the strict
    # runtime proof to reject an altered hash even when a protected mapping exists.
    record['runtime_bindings'][0]=dict(original,sha256='0'*64)
    with pytest.raises(ValueError):validate_record(ROOT,record,'A03')

def test_real_validate_record_in_lf_checkout_and_strict_nonprotected_refs(tmp_path):
    from workbench_analysis.parallel_scoped_acceptance_r1 import AUDIT
    record=json.loads((ROOT/record_path('A03')).read_bytes())
    rows={r['original_binding']['path']:r for r in metadata()['representations']}
    refs=[AUDIT,*record['evidence_bindings'],*record['runtime_bindings'],*record['protected_heads']]
    for ref in refs:
        if ref['path'] in rows:
            row=rows[ref['path']];raw=(ROOT/row['original_bytes_archive']['path']).read_bytes()
            write(tmp_path,row['original_bytes_archive']['path'],raw)
            write(tmp_path,ref['path'],raw.replace(b'\r\n',b'\n'))
        else:write(tmp_path,ref['path'],(ROOT/ref['path']).read_bytes())
    write(tmp_path,PROTECTED_REPRESENTATIONS['path'],(ROOT/PROTECTED_REPRESENTATIONS['path']).read_bytes())
    assert validate_record(tmp_path,record,'A03')['status']=='PASS_EXACT_SCOPED_EXTERNAL_ACCEPTANCE'
    for group in ['evidence_bindings','runtime_bindings']:
        changed=deepcopy(record);changed[group][0]=rows['data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json']['original_binding']
        with pytest.raises(ValueError):validate_record(tmp_path,changed,'A03')
