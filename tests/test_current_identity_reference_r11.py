import json
import pytest
from workbench_analysis.r43_owner_replay import ref
from workbench_db import v4_membership_reference_pg_v1 as module


def setup(tmp_path,monkeypatch):
    old=dict(security_id='OLD',symbol='SZ.000001',aliases=['ORIGINAL'])
    new=dict(security_id='NEW',symbol='SZ.301660',first_seen_date='2026-10-13',confirmed_ipo_date='2026-10-13',code_status='CONFIRMED_IPO')
    def write(name,obj):
        p=tmp_path/name;p.write_text(json.dumps(obj));return ref(tmp_path,p)
    prior=write('prior.json',dict(rows=[old]));current=write('current.json',dict(rows=[old,new]));life=write('life.json',dict(trade_date='2026-10-13',identity=current));snapshot=write('snapshot.json',dict(identity_source=prior))
    candidate=dict(accepted_trade_date='2026-10-13',membership_snapshot=snapshot,owners={'2026-10-13':dict(lifecycle=life)})
    candidate[module.KEY]=write('authority.json',dict(contract_id=module.CONTRACT,T0='2026-10-13',membership_snapshot=snapshot,AS_RECORDED=False,PIT_ELIGIBLE=False))
    facts={}
    monkeypatch.setattr(module,'append',lambda root,token,day,kind,source,content: facts.setdefault(token,content) or {})
    monkeypatch.setattr(module,'read_fact',lambda root,descriptor,token,day,kind,source:facts[token])
    return candidate,old,new,current


def test_current_301660_metadata_reader_preserves_old_alias(tmp_path,monkeypatch):
    candidate,old,new,current=setup(tmp_path,monkeypatch)
    original_snapshot=candidate['membership_snapshot'].copy()
    module.prepare_identity(tmp_path,candidate)
    assert module.read_identity(tmp_path,candidate)==[old,new]
    assert module.identity_source(tmp_path,candidate)==current
    assert candidate['membership_snapshot']==original_snapshot


def test_changed_old_alias_rejected_even_current_lifecycle_hash_valid(tmp_path,monkeypatch):
    candidate,old,new,current=setup(tmp_path,monkeypatch)
    p=tmp_path/current['path'];changed=dict(old,aliases=['FAKE_ALIAS']);p.write_text(json.dumps(dict(rows=[changed,new])))
    current=ref(tmp_path,p);life=tmp_path/'life.json';life.write_text(json.dumps(dict(trade_date='2026-10-13',identity=current)))
    candidate['owners']['2026-10-13']['lifecycle']=ref(tmp_path,life)
    with pytest.raises(ValueError,match='CURRENT_IDENTITY_PREDECESSOR_CHANGED'):module.prepare_identity(tmp_path,candidate)


def test_current_reference_lifecycle_substitution_rejected(tmp_path,monkeypatch):
    candidate,_,_,_=setup(tmp_path,monkeypatch);module.prepare_identity(tmp_path,candidate)
    p=tmp_path/'alternate.json';p.write_text(json.dumps(dict(trade_date='2026-10-13',identity=candidate['membership_snapshot'])))
    candidate['owners']['2026-10-13']['lifecycle']=ref(tmp_path,p)
    with pytest.raises(ValueError,match='CURRENT_IDENTITY_REFERENCE_SOURCE_MISMATCH'):module.read_identity(tmp_path,candidate)


def test_real_frozen_301660_metadata_through_current_identity_reader(tmp_path,monkeypatch):
    from pathlib import Path
    from workbench_analysis.operational_new_listing_r1 import observed_identity
    production=Path('G:/codex work/v4-production-20261012/data/v4/dynamic_daily_sources/new_listing_r1/2026-10-13/SZ.301660.json')
    if not production.is_file():pytest.skip('Fixed real 13 metadata not present on this host')
    before=production.read_bytes();real=json.loads(before)
    row=observed_identity('SZ.301660','2026-10-13',real['rows'],set())
    candidate,old,_,current=setup(tmp_path,monkeypatch)
    p=tmp_path/current['path'];p.write_text(json.dumps(dict(rows=[old,row])))
    life=tmp_path/'life.json';life.write_text(json.dumps(dict(trade_date='2026-10-13',identity=ref(tmp_path,p))))
    candidate['owners']['2026-10-13']['lifecycle']=ref(tmp_path,life)
    module.prepare_identity(tmp_path,candidate)
    records=module.read_identity(tmp_path,candidate)
    assert records[1]['symbol']=='SZ.301660' and records[1]['code_status']=='CONFIRMED_IPO'
    assert records[1]['first_seen_date']==records[1]['confirmed_ipo_date']=='2026-10-13'
    assert records[0]==old and production.read_bytes()==before
