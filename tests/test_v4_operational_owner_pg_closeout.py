"""Real PG owner invariants; small fixtures are not full numeric acceptance."""
import hashlib
import json
import pytest
from workbench_db.v4_operational_owner_pg_closeout import prepare,read,load_authority,attest_cached,OWNER

def source(root):
    path=root/'source.json';path.write_text('{"rows":[{"security_id":"600000","trade_date":"2026-10-09","value":3}]}')
    return {'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},json.loads(path.read_bytes())['rows']

def test_complete_native_read_and_reject_cross_date_domain_head(tmp_path):
    binding,rows=source(tmp_path);ref=prepare(tmp_path,'abc','2026-10-09','core',binding,rows)
    assert read(tmp_path,ref,'abc','2026-10-09','core',binding)==rows
    for token,day,domain in [('wrong','2026-10-09','core'),('abc','2026-10-08','core'),('abc','2026-10-09','raw')]:
        with pytest.raises(ValueError):read(tmp_path,ref,token,day,domain,binding)

def test_missing_dsn_fails_closed_and_reader_uses_pg_after_source_changes(tmp_path,monkeypatch):
    binding,rows=source(tmp_path);ref=prepare(tmp_path,'abc','2026-10-09','core',binding,rows)
    monkeypatch.delenv('V4_NATIVE_PG_DSN')
    with pytest.raises(RuntimeError):read(tmp_path,ref,'abc','2026-10-09','core',binding)
    monkeypatch.setenv('V4_NATIVE_PG_DSN','host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres')
    (tmp_path/'source.json').write_text('{}')
    assert read(tmp_path,ref,'abc','2026-10-09','core',binding)==rows

def test_pg_reader_requires_inline_descriptor_and_does_not_open_source_file(tmp_path,monkeypatch):
    import workbench_db.v4_operational_owner_pg_closeout as module
    binding={'path':'missing-source.json','sha256':'a'*64,'bytes':1}
    descriptor={'contract_id':module.CONTRACT,'engine':'postgresql','schema':'v4_forward_0000000000000000',
        'kind':'core','fact_key':'abc_2026-10-09_core','payload_sha256':'b'*64,
        'database_identity':{'system_identifier':'test'}}
    import hashlib
    raw=module.canonical(descriptor)
    descriptor_binding={'path':'data/v4/operational_owner_pg_closeout_r1/core/'+
        hashlib.sha256(descriptor['fact_key'].encode()).hexdigest()+'.pg.json',
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'pg_descriptor':descriptor}
    with pytest.raises(ValueError,match='INLINE_DESCRIPTOR_REQUIRED_NO_FILE_FALLBACK'):
        module.descriptor_metadata(tmp_path,{'path':descriptor_binding['path'],'sha256':descriptor_binding['sha256'],'bytes':descriptor_binding['bytes']})
    assert not (tmp_path/'missing-source.json').exists()

def test_authority_requires_complete_unchanged_source_mapping(tmp_path):
    binding,rows=source(tmp_path);ref=prepare(tmp_path,'abc','2026-10-09','core',binding,rows)
    candidate={'owners':{'2026-10-09':{'core':binding}}}
    folder=tmp_path/'config';folder.mkdir()
    authority={'contract_id':OWNER,'head_token':'abc','source_owners':candidate['owners'],'owners':{'2026-10-09':{'core':ref}},'historical_PIT_permission':False,'PIT_ELIGIBLE':False,'AS_RECORDED':False}
    path=folder/'v4_operational_owner_pg_closeout_r1.json';path.write_text(json.dumps(authority))
    assert load_authority(tmp_path,candidate,'abc')==authority
    authority['owners']['2026-10-09']={};path.write_text(json.dumps(authority))
    with pytest.raises(ValueError,match='DOMAINS_INCOMPLETE'):load_authority(tmp_path,candidate,'abc')

def test_cached_attestation_rehashes_actual_native_payload(tmp_path):
    from workbench_db.v4_native import connection
    binding,rows=source(tmp_path);ref=prepare(tmp_path,'abc','2026-10-09','core',binding,rows)
    assert read(tmp_path,ref,'abc','2026-10-09','core',binding)==rows
    attest_cached(tmp_path,ref,'core',binding)
    descriptor=json.loads((tmp_path/ref['path']).read_bytes())
    # Deliberately damage this test's own isolated schema, leaving the signed
    # descriptor and recorded SHA untouched. Cached reads must see corruption.
    with connection(descriptor['schema']) as pg:
        pg.execute('ALTER TABLE forward_facts DISABLE TRIGGER forward_append_only')
        pg.execute("UPDATE forward_facts SET payload='{}' WHERE kind=%s AND fact_key=%s",('core',descriptor['fact_key']))
        pg.execute('ALTER TABLE forward_facts ENABLE TRIGGER forward_append_only')
    with pytest.raises(ValueError,match='PAYLOAD_DIGEST_MISMATCH'):
        attest_cached(tmp_path,ref,'core',binding)
