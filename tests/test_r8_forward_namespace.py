import json
from pathlib import Path

import pytest

from workbench_db.forward_r7_store import ForwardR7Store
from workbench_db.v4_native import workspace_schema
from workbench_analysis.r43_owner_replay import ref


def candidate(tmp_path,monkeypatch,present=True):
    namespace=workspace_schema(tmp_path,'r8_forward')
    snapshot=dict(count=217,sha256='baseline')
    receipt=tmp_path/'baseline.json'
    receipt.write_text(json.dumps(dict(contract_id='R8_FORWARD_ISOLATED_BASELINE_COPY_R1',
        candidate_schema=namespace,candidate_root=str(tmp_path),source_unchanged=True,
        source_before=snapshot,source_after=snapshot,candidate_baseline=snapshot)))
    binding=dict(contract_id='R8_ISOLATED_FORWARD_NAMESPACE_R1',scope='CANDIDATE_ONLY',
        candidate_root=str(tmp_path),schema=namespace,baseline_receipt=ref(tmp_path,receipt))
    path=tmp_path/'config/r8_forward_candidate_namespace_r1.json'
    path.parent.mkdir();path.write_text(json.dumps(binding))
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,query,params):
            assert params==(namespace,'forward_facts')
            return self
        def fetchone(self):return (1,) if present else None
    monkeypatch.setattr('workbench_db.forward_r7_store.psycopg.connect',lambda *a,**kw:Connection())
    store=ForwardR7Store.__new__(ForwardR7Store);store.root=tmp_path.resolve();store.dsn='unused'
    return store,path,binding,receipt


def test_candidate_uses_verified_non_discoverable_namespace(tmp_path,monkeypatch):
    store,path,binding,receipt=candidate(tmp_path,monkeypatch)
    result=store._resolve_existing_schema()
    assert result==workspace_schema(tmp_path,'r8_forward')
    assert not result.startswith('v4_forward_')


@pytest.mark.parametrize('field,value',[
    ('schema','v4_forward_production'),('candidate_root','G:/codex_tmp/another-root'),('scope','PRODUCTION'),
])
def test_bad_candidate_pointer_never_falls_back_to_production(tmp_path,monkeypatch,field,value):
    store,path,binding,receipt=candidate(tmp_path,monkeypatch)
    binding[field]=value;path.write_text(json.dumps(binding))
    with pytest.raises(RuntimeError,match='NAMESPACE_BINDING_INVALID'):store._resolve_existing_schema()


def test_missing_candidate_table_never_falls_back(tmp_path,monkeypatch):
    store,*_=candidate(tmp_path,monkeypatch,present=False)
    with pytest.raises(RuntimeError,match='FACTS_TABLE_MISSING'):store._resolve_existing_schema()


def test_changed_baseline_receipt_fails_hash_check(tmp_path,monkeypatch):
    store,path,binding,receipt=candidate(tmp_path,monkeypatch)
    receipt.write_text('{}')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):store._resolve_existing_schema()
