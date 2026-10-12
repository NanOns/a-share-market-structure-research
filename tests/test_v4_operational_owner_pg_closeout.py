"""Real PG owner invariants; small fixtures are not full numeric acceptance."""
import hashlib
import json
import pytest
from workbench_db.v4_operational_owner_pg_closeout import prepare,read,load_authority,OWNER

def source(root):
    path=root/'source.json';path.write_text('{"rows":[{"security_id":"600000","trade_date":"2026-10-09","value":3}]}')
    return {'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},json.loads(path.read_bytes())['rows']

def test_complete_native_read_and_reject_cross_date_domain_head(tmp_path):
    binding,rows=source(tmp_path);ref=prepare(tmp_path,'abc','2026-10-09','core',binding,rows)
    assert read(tmp_path,ref,'abc','2026-10-09','core',binding)==rows
    for token,day,domain in [('wrong','2026-10-09','core'),('abc','2026-10-08','core'),('abc','2026-10-09','raw')]:
        with pytest.raises(ValueError):read(tmp_path,ref,token,day,domain,binding)

def test_missing_dsn_and_changed_archive_evidence_reject(tmp_path,monkeypatch):
    binding,rows=source(tmp_path);ref=prepare(tmp_path,'abc','2026-10-09','core',binding,rows)
    monkeypatch.delenv('V4_NATIVE_PG_DSN')
    with pytest.raises(RuntimeError):read(tmp_path,ref,'abc','2026-10-09','core',binding)
    monkeypatch.setenv('V4_NATIVE_PG_DSN','host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres')
    (tmp_path/'source.json').write_text('{}')
    with pytest.raises(ValueError):read(tmp_path,ref,'abc','2026-10-09','core',binding)

def test_authority_requires_complete_unchanged_source_mapping(tmp_path):
    binding,rows=source(tmp_path);ref=prepare(tmp_path,'abc','2026-10-09','core',binding,rows)
    candidate={'owners':{'2026-10-09':{'core':binding}}}
    folder=tmp_path/'config';folder.mkdir()
    authority={'contract_id':OWNER,'head_token':'abc','source_owners':candidate['owners'],'owners':{'2026-10-09':{'core':ref}},'historical_PIT_permission':False,'PIT_ELIGIBLE':False,'AS_RECORDED':False}
    path=folder/'v4_operational_owner_pg_closeout_r1.json';path.write_text(json.dumps(authority))
    assert load_authority(tmp_path,candidate,'abc')==authority
    authority['owners']['2026-10-09']={};path.write_text(json.dumps(authority))
    with pytest.raises(ValueError,match='DOMAINS_INCOMPLETE'):load_authority(tmp_path,candidate,'abc')
