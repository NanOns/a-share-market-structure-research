import json
import pytest
from workbench_analysis import operational_sealed_resume_r1 as module
from workbench_analysis.r43_owner_replay import ref


def fixture(tmp_path,monkeypatch):
    def write(name,value):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return ref(tmp_path,p)
    head=write('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',dict(accepted_trade_date='2026-10-12'))
    raw=write('raw.json',dict());native=write('native.json',dict());gb=write('gbbq',dict())
    gp=write('generation_policy.json',dict());rp=write('runtime_policy.json',dict())
    freeze=write('freeze.json',dict(target_session='2026-10-13',native_baostock=raw,tdx=native))
    gate=write('gate.json',dict(source_ready=True,source_freeze=freeze,dependency_bindings=dict(parent_head=head,gbbq=dict(gb,path=str(tmp_path/gb['path'])))))
    generation=write('generation.json',dict(parent_head=head['sha256'],source_freeze=freeze['sha256'],adjustment_contract=dict(policy=gp)))
    candidate=write('candidate.json',dict(accepted_trade_date='2026-10-13',predecessor=head,exact_daily_generation_scope=generation,release_policy=rp))
    passgate=write('pass.json',dict(acceptance='PASS',errors=[]))
    m=dict(contract_id=module.CONTRACT,target_session='2026-10-13',allowed_modes=['CATCH_UP'],candidate=candidate,predecessor=head,generation=generation,source_freeze=freeze,source_readiness=gate,generation_policy=gp,runtime_policy=rp,gates={k:passgate for k in ('G1','G2','G3','G4_PREPUBLICATION')},period_verifier=raw)
    m['gate_attestation']=write('attestation.json',dict(contract_id='SEALED_RESUME_GATE_ATTESTATION_R1',acceptance='PASS',candidate=candidate,generation=generation,source_freeze=freeze,predecessor=head,gates=m['gates'],target_session='2026-10-13'))
    manifest=write('manifest.json',m);write(module.POINTER,dict(target_session='2026-10-13',allowed_modes=['CATCH_UP'],manifest=manifest))
    from workbench_analysis import operational_successor_v1,operational_successor_release_v1
    monkeypatch.setattr(operational_successor_v1,'validate',lambda *a:None)
    monkeypatch.setattr(operational_successor_release_v1,'verify_policy',lambda *a:None)
    return m


def test_exact_manifest_preflight_accepts_and_nonmatching_job_never_resumes(tmp_path,monkeypatch):
    m=fixture(tmp_path,monkeypatch)
    assert module.verify(tmp_path,m)['accepted_trade_date']=='2026-10-13'
    assert module.selected(tmp_path,'2026-10-13','CATCH_UP')[0]==m
    assert module.selected(tmp_path,'2026-10-14','CATCH_UP') is None
    assert module.selected(tmp_path,'2026-10-13','PROBE') is None


def test_mutated_candidate_rejected_without_head_or_producer_writes(tmp_path,monkeypatch):
    m=fixture(tmp_path,monkeypatch);head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes()
    (tmp_path/'candidate.json').write_text('{}')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):module.verify(tmp_path,m)
    assert head.read_bytes()==before


def test_already_accepted_target_is_noop_never_republished(tmp_path,monkeypatch):
    m=fixture(tmp_path,monkeypatch);head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head.write_text(json.dumps(dict(accepted_trade_date='2026-10-13')))
    assert module.verify(tmp_path,m) is None


def test_pass_gates_from_different_final_candidate_cannot_resume(tmp_path,monkeypatch):
    m=fixture(tmp_path,monkeypatch)
    p=tmp_path/'attestation.json';doc=json.loads(p.read_text());doc['candidate']=dict(path='other.json',sha256='a'*64);p.write_text(json.dumps(doc));m['gate_attestation']=ref(tmp_path,p)
    with pytest.raises(ValueError,match='GATE_CANDIDATE_MISMATCH'):module.verify(tmp_path,m)


def test_source_parent_archive_alias_requires_same_checked_bytes(tmp_path,monkeypatch):
    m=fixture(tmp_path,monkeypatch)
    original=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';archive=tmp_path/'parent_archive.json';archive.write_bytes(original.read_bytes())
    m['predecessor']=ref(tmp_path,archive)
    # Regenerate candidate and attestation with archived formal predecessor.
    c=tmp_path/'candidate.json';doc=json.loads(c.read_text());doc['predecessor']=m['predecessor'];c.write_text(json.dumps(doc));m['candidate']=ref(tmp_path,c)
    a=tmp_path/'attestation.json';ad=json.loads(a.read_text());ad.update(candidate=m['candidate'],predecessor=m['predecessor']);a.write_text(json.dumps(ad));m['gate_attestation']=ref(tmp_path,a)
    assert module.verify(tmp_path,m)['predecessor']==m['predecessor']
    archive.write_text(json.dumps(dict(accepted_trade_date='2026-10-11')))
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):module.verify(tmp_path,m)


def test_wrong_append_mode_pointer_fails_closed_instead_of_falling_into_full_producer(tmp_path,monkeypatch):
    fixture(tmp_path,monkeypatch);p=tmp_path/module.POINTER;pointer=json.loads(p.read_text());pointer['allowed_modes']=['APPEND'];p.write_text(json.dumps(pointer))
    with pytest.raises(ValueError,match='JOB_MODE_CONTRACT_REQUIRED'):module.selected(tmp_path,'2026-10-13','CATCH_UP')
