"""Isolated BFF contract tests. Synthetic rows never enter production snapshots."""
import json
import sqlite3
import pytest
from workbench_service.production_v4 import ProductionV4ResearchReader,reference,value_projection,frozen_current_reader,REQUIRED_METADATA,rollback_snapshot,POINTER
from workbench_service.current_v4_context import canonical,SourceInvalid,digest
from workbench_service.v4_daily_refresh import atomic_bytes
from workbench_service.research_bff import ResearchBFF

@pytest.fixture
def reader(tmp_path):
    path=tmp_path/'research.sqlite';db=sqlite3.connect(path)
    db.executescript('CREATE TABLE objects(domain,id,name,symbol,state,payload,PRIMARY KEY(domain,id)); CREATE TABLE aliases(alias,id);CREATE TABLE members(sector,security);')
    for i in range(7):
        row=dict(entity_id='SEC'+str(i),display_name='公司'+str(i),symbol='SH.'+str(i),fields={'close':dict(value=i,quality='KNOWN'),'state':dict(value='INELIGIBLE',quality='KNOWN')})
        db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',('stocks',row['entity_id'],row['display_name'],row['symbol'],'INELIGIBLE',canonical(row).decode()))
        db.execute('INSERT INTO aliases VALUES(?,?)',('old'+str(i),row['entity_id']))
    db.execute('INSERT INTO members VALUES(?,?)',('sector1','SEC2'));db.commit();db.close()
    manifest=dict(database=reference(tmp_path,path),context=dict(accepted_trade_date='2026-09-30',data_updated_at='2026-10-01T00:00:00Z'),release_id='unit-test-only',source_contract_digest='a'*64,sources={'advanced':{'sha256':'b'*64}},quality='QUALITY_DEGRADED',gaps=[],counts={'stocks':7})
    # Contract fixtures are isolated to pytest's E: temporary root.
    manifest['metadata']={k:'unit-test-only' for k in REQUIRED_METADATA}
    manifest['metadata'].update(trading_date='2026-09-30',evidence_origin='REAL_ACCEPTED_SOURCE')
    atomic_bytes(tmp_path/'manifest.json',canonical(manifest));atomic_bytes(tmp_path/'config/v4_research_snapshot_authority_v1.json',canonical({'manifest':reference(tmp_path,tmp_path/'manifest.json')}))
    return ProductionV4ResearchReader(tmp_path)

def test_stable_pagination_and_sort(reader):
    ids=[]
    for offset in (0,3,6):
        page=reader.query('stocks',{'offset':str(offset),'limit':'3','sort':'-name,id'})
        assert page['total']==7;ids.extend(r['entity_id'] for r in page['items'])
    assert len(set(ids))==7 and ids==['SEC'+str(i) for i in range(6,-1,-1)]

@pytest.mark.parametrize('key,value',[('context_token','stale'),('trade_date','2026-09-28'),('release_id','other'),('model_namespace','other')])
def test_context_conflicts(reader,key,value):
    with pytest.raises(SourceInvalid):reader.query('stocks',{key:value})

@pytest.mark.parametrize('query',[{'limit':'0'},{'limit':'201'},{'offset':'-1'},{'q':'x'*81},{'sort':'id; DROP TABLE objects'},{'sort':'id,id,id,id,id'},{'bogus':'1'}])
def test_query_bounds(reader,query):
    with pytest.raises(ValueError):reader.query('stocks',query)

def test_alias_and_member_lookup(reader):
    assert reader.query('stocks',{'q':'old2'})['items'][0]['entity_id']=='SEC2'
    assert reader.query('stocks',sector='sector1')['total']==1
    assert reader.query('stocks',entity='absent')['total']==0

def test_immutable_database_tamper_fails_closed(reader):
    with reader.path.open('ab') as f:f.write(b'changed')
    with pytest.raises(SourceInvalid,match='IMMUTABLE_DATABASE_CHANGED'):reader.query('stocks')

def test_projection_preserves_values_null_quality_and_reasons():
    value={'value':None,'quality':'UNKNOWN','reason':'NO_HISTORY','source_refs':['large graph'],'nested':{'value':0,'quality':'KNOWN'}}
    assert value_projection(value)=={'value':None,'quality':'UNKNOWN','reason':'NO_HISTORY','nested':{'value':0,'quality':'KNOWN'}}

def test_bff_error_semantics_and_pool_ineligibility(reader,monkeypatch):
    bff=ResearchBFF(reader.root);monkeypatch.setattr(bff,'current',lambda:reader)
    assert bff.get('/api/v4/stocks',{'context_token':'old'})[0]==409
    assert bff.get('/api/v4/stocks',{'limit':'201'})[0]==400
    assert bff.get('/api/v4/stocks/missing',{})[0]==404
    assert bff.get('/api/v4/stocks/SEC2',{})[0]==200
    code,data=bff.get('/api/v4/compare',{})
    assert code==200 and data['status']=='PIT_NOT_AVAILABLE' and data['items']==[]

def test_rate_limit_does_not_reject_other_client(reader):
    bff=ResearchBFF(reader.root)
    assert all(bff.allowed('one') for _ in range(240))
    assert not bff.allowed('one') and bff.allowed('two')

def test_build_reader_remains_pinned_when_runtime_moves(tmp_path):
    for name in ('old','new'):
        atomic_bytes(tmp_path/(name+'.json'),canonical(dict(contract_id='V4_CURRENT_ACCEPTED_READ_CONTRACT_V1',source_discovery=False,fallback='NONE',namespace=name)))
    authority=tmp_path/'config/v4_production_runtime_authority_v1.json'
    runtime=dict(contract_id='V4_PRODUCTION_RUNTIME_AUTHORITY_V1',ui_read_only=True,tdx_write_authorized=False,trading_action_authorized=False,read_authority=reference(tmp_path,tmp_path/'old.json'))
    atomic_bytes(authority,canonical(runtime));frozen,binding=frozen_current_reader(tmp_path)
    runtime['read_authority']=reference(tmp_path,tmp_path/'new.json');atomic_bytes(authority,canonical(runtime))
    contract,sha=frozen._contract()
    assert contract['namespace']=='old' and sha==binding['sha256'] and not frozen.follow_runtime

def test_build_reader_rejects_unsafe_runtime_authority(tmp_path):
    atomic_bytes(tmp_path/'config/v4_production_runtime_authority_v1.json',canonical({'contract_id':'WRONG','ui_read_only':True}))
    with pytest.raises(SourceInvalid,match='RUNTIME_AUTHORITY_INVALID'):frozen_current_reader(tmp_path)

def test_reader_rejects_fixture_or_missing_release_metadata(reader):
    path=reader.root/'manifest.json';manifest=json.loads(path.read_bytes())
    for metadata in ({},dict(manifest['metadata'],evidence_origin='FIXTURE')):
        manifest['metadata']=metadata;atomic_bytes(path,canonical(manifest))
        atomic_bytes(reader.root/'config/v4_research_snapshot_authority_v1.json',canonical({'manifest':reference(reader.root,path)}))
        with pytest.raises(SourceInvalid,match='RELEASE_METADATA_INCOMPLETE_OR_NON_REAL'):ProductionV4ResearchReader(reader.root)

def test_rollback_rejects_ineligible_draft_before_pointer_swap(reader):
    manifest=json.loads((reader.root/'manifest.json').read_bytes());manifest.pop('metadata')
    draft=reader.root/'draft.json';atomic_bytes(draft,canonical(manifest))
    path=reader.root/POINTER;authority=json.loads(path.read_bytes());authority['previous']={'manifest':reference(reader.root,draft)}
    raw=canonical(authority);atomic_bytes(path,raw)
    with pytest.raises(SourceInvalid,match='RELEASE_METADATA_INCOMPLETE_OR_NON_REAL'):rollback_snapshot(reader.root,digest(raw))
    assert path.read_bytes()==raw

def test_alias_search_finds_multiple_event_objects_for_one_security(reader):
    with sqlite3.connect(reader.path) as db:
        for suffix in ('event1','event2'):
            row=dict(entity_id='SEC2',display_name='公司2',symbol='SH.2',fields={})
            db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',('events','SEC2:'+suffix,'公司2','SH.2','',canonical(row).decode()))
        db.commit()
    stat=reader.path.stat();reader.file_signature=(stat.st_size,stat.st_mtime_ns)
    assert reader.query('events',{'q':'old2'})['total']==2
    assert reader.query('events',{'q':'old'})['total']==2


def test_staged_reader_verifies_candidate_while_live_joint_stays_old(reader):
    live=json.loads((reader.root/POINTER).read_bytes())
    joint=reader.root/'config/v4_joint_release_authority_v1.json'
    atomic_bytes(joint,canonical(dict(contract_id='V4_JOINT_RELEASE_V1',snapshot=live,
        operational_release_scope=['stocks_daily'],full_product_release=False,trading=False)))
    original=joint.read_bytes()
    manifest=json.loads((reader.root/live['manifest']['path']).read_bytes())
    manifest['release_id']='candidate';manifest['metadata']['release_id']='candidate'
    path=reader.root/'candidate_manifest.json';atomic_bytes(path,canonical(manifest))
    candidate=dict(manifest=reference(reader.root,path))
    staged=ProductionV4ResearchReader(reader.root,snapshot_authority=candidate)
    assert staged.context['release_id']=='candidate'
    assert staged.context['scoped_release'] is False
    assert ProductionV4ResearchReader(reader.root).token!=staged.token
    assert joint.read_bytes()==original
    manifest.pop('metadata');atomic_bytes(path,canonical(manifest));candidate['manifest']=reference(reader.root,path)
    with pytest.raises(SourceInvalid,match='METADATA'):
        ProductionV4ResearchReader(reader.root,snapshot_authority=candidate)
    assert joint.read_bytes()==original


def test_active_joint_forbids_legacy_pointer_only_build(reader):
    from workbench_service.production_v4 import build_snapshot
    joint=reader.root/'config/v4_joint_release_authority_v1.json'
    atomic_bytes(joint,b'{}');before=(reader.root/POINTER).read_bytes()
    with pytest.raises(SourceInvalid,match='STAGED_BUILD_AND_JOINT_CAS'):
        build_snapshot(reader.root)
    with pytest.raises(SourceInvalid,match='JOINT_ROLLBACK'):
        rollback_snapshot(reader.root,digest(before))
    assert (reader.root/POINTER).read_bytes()==before


def test_compact_projection_keeps_explicit_numeric_denominator():
    from workbench_service.production_v4 import compact_cell
    binding={'sha256':'accepted'}
    for source,expected in [({'n':20,'denominator':30,'known_count':40},20),({'denominator':30,'known_count':40},30),({'known_count':40},40),({},None)]:
        cell=compact_cell(dict(value=0.5,quality='ACCEPTED',**source),binding,'ma20_width','2026-09-30')
        assert cell['value']==0.5 and cell['denominator']==expected
