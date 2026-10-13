"""Scoped metadata retains entry bytes; only the pinned two Git representations resolve."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from workbench_analysis.parallel_scoped_consolidation_r3 import (
    REGISTRY, DISPOSITIONS, PROTECTED_REPRESENTATIONS, protected_bindings,
    validate_consolidation, validate_scoped_protected_binding,
)
from workbench_analysis.parallel_scoped_acceptance_r1 import AUDIT as PRIOR_AUDIT

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT/path).read_bytes())


def put(root,path,raw):
    target=root/path
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)


def representation(root,index):
    metadata=read(PROTECTED_REPRESENTATIONS['path'])
    row=deepcopy(metadata['representations'][index])
    raw=(ROOT/row['original_bytes_archive']['path']).read_bytes()
    put(root,PROTECTED_REPRESENTATIONS['path'],(ROOT/PROTECTED_REPRESENTATIONS['path']).read_bytes())
    put(root,row['original_bytes_archive']['path'],raw)
    put(root,row['original_binding']['path'],raw.replace(b'\r\n',b'\n'))
    return row


@pytest.mark.parametrize('index',[0,1])
def test_scoped_proof_reopens_exact_pinned_original_bytes_in_git_lf_checkout(tmp_path,index):
    row=representation(tmp_path,index)
    result=validate_scoped_protected_binding(tmp_path,row['original_binding'],approved_representation_map=PROTECTED_REPRESENTATIONS)
    assert result == tmp_path/row['original_bytes_archive']['path']
    assert result.read_bytes() == (ROOT/row['original_bytes_archive']['path']).read_bytes()


@pytest.mark.parametrize('index',[0,1])
@pytest.mark.parametrize('fault',['actual_content','archive_content','map_content','unregistered_hash','unregistered_size','unapproved_map'])
def test_actual_drift_and_unapproved_mapping_remain_fail_closed(tmp_path,index,fault):
    row=representation(tmp_path,index)
    ref=deepcopy(row['original_binding'])
    approved=deepcopy(PROTECTED_REPRESENTATIONS)
    if fault == 'actual_content':
        p=tmp_path/row['git_representation']['path']
        p.write_bytes(p.read_bytes()+b' ')
    elif fault == 'archive_content':
        p=tmp_path/row['original_bytes_archive']['path']
        p.write_bytes(p.read_bytes()+b' ')
    elif fault == 'map_content':
        p=tmp_path/PROTECTED_REPRESENTATIONS['path']
        p.write_bytes(p.read_bytes()+b' ')
    elif fault == 'unregistered_hash':
        ref['sha256']='0'*64
    elif fault == 'unregistered_size':
        ref['bytes']+=1
    else:
        approved['sha256']='0'*64
    with pytest.raises(ValueError):
        validate_scoped_protected_binding(tmp_path,ref,approved_representation_map=approved)


def test_real_consolidation_retains_batch_refs_and_passes_only_exact_clean_representations(tmp_path):
    registry=read(REGISTRY)
    refs=[registry['external_authority']['document'],registry['stage_contract'],registry['master'],
          registry['supersedes'],PRIOR_AUDIT,*registry['protected_bindings']]
    for package in DISPOSITIONS:
        record_ref=registry['entries'][package]['prior_acceptance_record']
        refs.append(record_ref)
        record=read(record_ref['path'])
        refs.extend([*record['evidence_bindings'],*record['runtime_bindings'],*record['protected_heads']])
    for ref in refs:
        put(tmp_path,ref['path'],(ROOT/ref['path']).read_bytes())
    put(tmp_path,'reports/next_round_r3/BATCH_STAGE_ENTRY_R1.json',
        (ROOT/'reports/next_round_r3/BATCH_STAGE_ENTRY_R1.json').read_bytes())
    rows=[representation(tmp_path,index) for index in (0,1)]
    assert protected_bindings(tmp_path) == registry['protected_bindings']
    result=validate_consolidation(tmp_path,registry)
    assert result['engineering_tasks_closed'] == 5 and result['blocks_v4_11_mainline'] is False
    p=tmp_path/rows[0]['git_representation']['path']
    p.write_bytes(p.read_bytes()+b' ')
    # Stable expected references do not hide changed content: reopening rejects.
    assert protected_bindings(tmp_path) == registry['protected_bindings']
    with pytest.raises(ValueError):
        validate_consolidation(tmp_path,registry)
