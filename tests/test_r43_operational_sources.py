import json
import gzip
import hashlib
from pathlib import Path
import pytest
from workbench_analysis.r43_operational_sources import checked,date_valid_identity
from workbench_analysis.r43_operational_publication import validate,POLICY,_validate_owner_identity_conservation
from workbench_service.core_product_bff_r1 import CoreProductBFFR1,_missing_adjusted_close
from types import SimpleNamespace

def test_source_hash_refuses_mutated_bytes(tmp_path):
    path=tmp_path/'source.json';path.write_text('{}')
    with pytest.raises(ValueError,match='SOURCE_DIGEST_MISMATCH'):
        checked(tmp_path,dict(path='source.json',sha256='0'*64))

def test_date_effective_identity_uses_exclusive_delist_boundary():
    identity=dict(security_id='SEC-test',list_date='2026-09-29',delist_date='2026-10-08')
    assert not date_valid_identity(identity,'2026-09-28')
    assert date_valid_identity(identity,'2026-09-29')
    assert date_valid_identity(identity,'2026-09-30')
    assert not date_valid_identity(identity,'2026-10-08')
    assert not date_valid_identity(dict(identity,security_id=None),'2026-09-30')

def test_operational_owner_requires_exact_core_profile_lifecycle_identity_set(tmp_path):
    day='test-day'
    def bind(name,content):
        path=tmp_path/name
        if name.endswith('.gz'):
            with gzip.open(path,'wt',encoding='utf-8') as stream:
                for row in content:stream.write(json.dumps(row)+'\n')
        else:path.write_text(json.dumps(content),encoding='utf-8')
        raw=path.read_bytes()
        return {'path':name,'sha256':hashlib.sha256(raw).hexdigest()}
    lifecycle=bind('lifecycle.json',{'trade_date':day,'active_security_ids':['SEC-A','SEC-B']})
    core=bind('core.jsonl.gz',[{'security_id':'SEC-A','trade_date':day},{'security_id':'SEC-B','trade_date':day}])
    profile=bind('profile.jsonl.gz',[{'security_id':'SEC-A','trade_date':day},{'security_id':'SEC-B','trade_date':day}])
    _validate_owner_identity_conservation(tmp_path,day,{'lifecycle':lifecycle,'core':core,'profile':profile})

    wrong_core=bind('wrong-core.jsonl.gz',[{'security_id':'SEC-A','trade_date':day},
        {'security_id':'SEC-B','trade_date':day},{'security_id':'SEC-C','trade_date':day}])
    with pytest.raises(ValueError,match='OWNER_LIFECYCLE_IDENTITY_SET_MISMATCH:core:test-day:active=2:owner=3'):
        _validate_owner_identity_conservation(tmp_path,day,
            {'lifecycle':lifecycle,'core':wrong_core,'profile':profile})

def test_operational_owner_rejects_duplicate_or_cross_date_identity_rows(tmp_path):
    day='test-day'
    def bind(name,content):
        path=tmp_path/name
        if name.endswith('.gz'):
            with gzip.open(path,'wt',encoding='utf-8') as stream:
                for row in content:stream.write(json.dumps(row)+'\n')
        else:path.write_text(json.dumps(content),encoding='utf-8')
        return {'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    lifecycle=bind('lifecycle.json',{'trade_date':day,'active_security_ids':['SEC-A']})
    profile=bind('profile.jsonl.gz',[{'security_id':'SEC-A','trade_date':day}])
    duplicate=bind('duplicate-core.jsonl.gz',[{'security_id':'SEC-A','trade_date':day},
        {'security_id':'SEC-A','trade_date':day}])
    with pytest.raises(ValueError,match='OWNER_IDENTITY_DUPLICATE:core:test-day'):
        _validate_owner_identity_conservation(tmp_path,day,
            {'lifecycle':lifecycle,'core':duplicate,'profile':profile})
    wrong_date=bind('wrong-date-core.jsonl.gz',[{'security_id':'SEC-A','trade_date':'other-day'}])
    with pytest.raises(ValueError,match='OWNER_IDENTITY_TRADE_DATE_MISMATCH:core:test-day'):
        _validate_owner_identity_conservation(tmp_path,day,
            {'lifecycle':lifecycle,'core':wrong_date,'profile':profile})

def test_bff_security_owner_scope_filters_only_lifecycle_excess_and_caches_scope(tmp_path):
    day='test-day';lifecycle={'trade_date':day,'active_security_ids':['SEC-A','SEC-B']}
    path=tmp_path/'lifecycle.json';path.write_text(json.dumps(lifecycle),encoding='utf-8')
    binding={'path':'lifecycle.json','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    reader=SimpleNamespace(root=tmp_path,token='candidate-token',candidate={'owners':{day:{'lifecycle':binding}}},cache={})
    bff=object.__new__(CoreProductBFFR1);bff.api=reader
    content=[{'security_id':'SEC-A','trade_date':day},{'security_id':'SEC-B','trade_date':day},
        {'security_id':'SEC-C','trade_date':day}]
    assert bff._scope_security_owner_rows('core',day,content)==content[:2]
    assert ('lifecycle-identity-scope-v1','candidate-token',day) in reader.cache

def test_bff_security_owner_scope_rejects_duplicate_and_wrong_date(tmp_path):
    day='test-day';lifecycle={'trade_date':day,'active_security_ids':['SEC-A']}
    path=tmp_path/'lifecycle.json';path.write_text(json.dumps(lifecycle),encoding='utf-8')
    binding={'path':'lifecycle.json','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    reader=SimpleNamespace(root=tmp_path,token='candidate-token',candidate={'owners':{day:{'lifecycle':binding}}},cache={})
    bff=object.__new__(CoreProductBFFR1);bff.api=reader
    with pytest.raises(ValueError,match='OWNER_IDENTITY_DUPLICATE_OR_MISSING:focus:test-day'):
        bff._scope_security_owner_rows('focus',day,[{'entity_id':'SEC-A'},{'entity_id':'SEC-A'}])
    with pytest.raises(ValueError,match='OWNER_IDENTITY_TRADE_DATE_MISMATCH:prewatch:test-day'):
        bff._scope_security_owner_rows('prewatch',day,[{'entity_id':'SEC-A','trade_date':'other-day'}])

def test_missing_adjustment_owner_and_row_are_explicit_source_gaps():
    owner_gap=_missing_adjusted_close('test-day',False)
    row_gap=_missing_adjusted_close('test-day',True)
    assert owner_gap['quality']=='SOURCE_INCOMPLETE'
    assert owner_gap['reason']=='DATED_ADJUSTED_OWNER_MISSING'
    assert row_gap['quality']=='SOURCE_INCOMPLETE'
    assert row_gap['reason']=='DATED_ADJUSTED_SECURITY_ROW_MISSING'
    assert owner_gap['value'] is None and row_gap['value'] is None

@pytest.mark.parametrize('change,error',[
    ({'historical_PIT_permission':True},'PIT_ESCALATION'),
    ({'AS_RECORDED':True},'PIT_ESCALATION'),
    ({'taxonomy':'BAO_CSRC'},'TDX_LATEST_PRIMARY'),
    ({'dates':['2026-10-09']},'FOUR_SESSION_DATE'),
])
def test_operational_type_rejection(tmp_path,change,error):
    c=dict(contract_id=POLICY,dates=['2026-09-28','2026-09-29','2026-09-30','2026-10-08'],AS_RECORDED=False,historical_PIT_permission=False,taxonomy='TDX_INDUSTRY_CONCEPT',membership_mode='TDX_LATEST_MEMBER_RETRO_V1')
    c.update(change)
    with pytest.raises(ValueError,match=error):validate(tmp_path,c)
