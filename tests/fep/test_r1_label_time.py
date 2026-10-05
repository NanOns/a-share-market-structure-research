"""Independent receipt knowledge-time counterfactuals; fixture evidence only."""
import json
from pathlib import Path

import pytest

from workbench_analysis.fep_e1.contracts import atomic_json, digest
from workbench_analysis.fep_e1.labels import project_with_owner_time
from workbench_analysis.v4_15_fep_label_time import CONTRACT, identity, resolve


def fixture(root):
    import hashlib
    row = dict(enrollment_id='ENTRY-A', horizon=5, outcome_contract_id='V4_15_OUTCOME_V1',
               outcome_revision_id='r1', evaluation_revision=1, evaluation_source_digest='facts',
               evidence_class='ENGINEERING_VECTOR', outcome_status='OBSERVED', R_N=.1)
    key = identity(row)
    def write(name, value):
        atomic_json(root/name, value)
        raw=(root/name).read_bytes()
        return dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    allocation = dict(identity=key, upstream_row=write('row.json', row), consumed_fact_ids=['a','b'])
    for kind, days in [('source',[1,2]),('maturity',[5]),('revision',[6])]:
        allocation[kind]=[]
        for index, day in enumerate(days):
            receipt=dict(identity=key, evidence_class='ENGINEERING_FIXTURE', status='ACCEPTED',
                         kind=kind, available_at=f'2030-01-{day:02}T00:00:00Z')
            if kind=='source':receipt['fact_id']='ab'[index]
            if kind=='maturity':receipt.update(full_window_complete=True, required_quality_complete=True, horizon=5)
            allocation[kind].append(write(f'{kind}{index}.json', receipt))
    contract=dict(contract_id=CONTRACT,allocations=[allocation])
    atomic_json(root/'config/v4_15_fep_label_time_authority_v1.json',contract)
    return row, contract, write


@pytest.mark.parametrize('day,eligible', [(3,False),(5,False),(6,True)])
def test_source_t2_mature_t5_revision_t6(tmp_path,day,eligible):
    row,_,_=fixture(tmp_path)
    result=project_with_owner_time(tmp_path,row,dict(family='ABS_RETURN_N',horizon=5),
                                   authority_head={'PROVED_HORIZONS':[]},cutoff=f'2030-01-{day:02}T00:00:00Z')
    assert result['training_allowed'] is eligible
    if eligible: assert result['numeric_value']==.1
    else: assert result['time_authority']['binding'] is None


@pytest.mark.parametrize('case', ['missing_source','missing_maturity','missing_revision','tampered_bytes',
                                   'wrong_row','wrong_class','revision_before_source','incomplete_window',
                                   'naive_time','missing_fact','duplicate_fact'])
def test_time_authority_counterfactuals(tmp_path,case):
    row, contract, write=fixture(tmp_path)
    a=contract['allocations'][0]
    expected_error=True
    if case.startswith('missing_') and case!='missing_fact':
        a[case[8:]]=[]; expected_error=False
    elif case=='tampered_bytes':
        (tmp_path/'source0.json').write_bytes(b'{}')
    elif case=='wrong_row': row['evaluation_revision']=2;expected_error=False
    elif case=='missing_fact': a['source']=a['source'][:1]
    else:
        kind='revision' if case=='revision_before_source' else 'maturity' if case=='incomplete_window' else 'source'
        i=1 if case=='duplicate_fact' else 0
        name=f'{kind}{i}.json';receipt=json.loads((tmp_path/name).read_bytes())
        if case=='wrong_class': receipt['evidence_class']='REAL_ACCEPTED_EVIDENCE'
        if case=='revision_before_source':receipt['available_at']='2030-01-01T00:00:00Z'
        if case=='incomplete_window':receipt['full_window_complete']=False;expected_error=False
        if case=='naive_time':receipt['available_at']='2030-01-01'
        if case=='duplicate_fact':receipt['fact_id']='a'
        a[kind][i]=write(name,receipt)
    atomic_json(tmp_path/'config/v4_15_fep_label_time_authority_v1.json',contract)
    if expected_error:
        with pytest.raises(ValueError):resolve(tmp_path,row,'2030-01-06T00:00:00Z')
    else:
        result=resolve(tmp_path,row,'2030-01-06T00:00:00Z')
        assert not result['training_allowed'] and result['binding'] is None


def test_real_pending_never_binds_calendar_or_caller_times(tmp_path):
    row,contract,_=fixture(tmp_path)
    row.update(evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED', outcome_status='PENDING',
               report_cutoff='2030-01-20', due_date='2030-01-05')
    atomic_json(tmp_path/'config/v4_15_fep_label_time_authority_v1.json',contract)
    result=resolve(tmp_path,row,'2030-01-20T00:00:00Z')
    assert result['binding'] is None and set(result['times'].values())=={'NOT_PROVEN'}


def test_unaccepted_real_time_sidecars_cannot_grant_training(tmp_path):
    row,contract,write=fixture(tmp_path)
    row['evidence_class']='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED'
    a=contract['allocations'][0]
    a['identity']=identity(row)
    a['upstream_row']=write('row.json',row)
    for kind in ('source','maturity','revision'):
        for i,ref in enumerate(a[kind]):
            receipt=json.loads((tmp_path/ref['path']).read_bytes())
            receipt.update(identity=identity(row),evidence_class='REAL_ACCEPTED_EVIDENCE')
            a[kind][i]=write(ref['path'],receipt)
    contract['accepted_owner_head']=write('head.json',{'PROVED_HORIZONS':[5]})
    atomic_json(tmp_path/'config/v4_15_fep_label_time_authority_v1.json',contract)
    result=resolve(tmp_path,row,'2030-01-20T00:00:00Z')
    assert not result['training_allowed'] and result['binding'] is None
    assert result['reason']=='REAL_TIME_RECEIPT_ACCEPTANCE_NOT_GRANTED'


def test_namespace_successor_preserves_v1_and_permissions():
    import hashlib
    root=Path(__file__).resolve().parents[2]
    c=json.loads((root/'config/v4_18_migration_replay_contract_v1_1.json').read_bytes())
    old=(root/c['supersedes']['path']).read_bytes()
    assert hashlib.sha256(old).hexdigest()==c['supersedes']['sha256']
    original=json.loads(old)
    assert c['namespace_matrix'][:len(original['namespace_matrix'])]==original['namespace_matrix']
    assert c['permissions']==original['permissions']
    fep=[r for r in c['namespace_matrix'] if r['read_source']=='FEP_E1_ENGINEERING']
    assert len(fep)==33 and all(r['write_target'] is None and not r['production_cutover'] for r in fep)
