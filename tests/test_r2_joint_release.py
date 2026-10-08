import json
import pytest
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.joint_release import activate,recover,validate,AUTHORITY

def candidate(root,version):
    def binding(name,data):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);raw=canonical(data);path.write_bytes(raw)
        return dict(path=name,sha256=digest(raw))
    db=binding(f'data/{version}/db',{'real_test':version})
    manifest=binding(f'data/{version}/manifest',dict(context={'accepted_trade_date':'2026-09-30'},database=db,sources={}))
    ui=binding(f'data/{version}/index.html',{'ui':version})
    return dict(contract_id='V4_JOINT_RELEASE_V1',snapshot={'manifest':manifest},ui_assets={'index.html':ui},trade_date='2026-09-30',operational_release_scope=['test'],trading=False)

def test_joint_health_failure_exact_restore_and_noop(tmp_path):
    a=candidate(tmp_path,'a');b=candidate(tmp_path,'b');health=lambda c:{'pass':True}
    receipt=activate(tmp_path,a,None,health);p=tmp_path/AUTHORITY;old=p.read_bytes()
    assert receipt['activation_performed']
    with pytest.raises(SourceInvalid,match='HEALTH'):activate(tmp_path,b,digest(old),lambda c:{'pass':False})
    assert p.read_bytes()==old
    assert activate(tmp_path,a,digest(old),health)['result']=='NOOP'
    with pytest.raises(SourceInvalid,match='CAS'):activate(tmp_path,b,'stale',health)
    assert p.read_bytes()==old

def test_concurrent_release_lock_and_digest_mismatch(tmp_path):
    a=candidate(tmp_path,'a');p=tmp_path/AUTHORITY;p.parent.mkdir(parents=True)
    lock=p.with_suffix('.lock');lock.write_text('held')
    with pytest.raises(SourceInvalid,match='BUSY'):activate(tmp_path,a,None,lambda c:{'pass':True})
    lock.unlink();a['ui_assets']['index.html']['sha256']='bad'
    with pytest.raises(SourceInvalid,match='DIGEST'):activate(tmp_path,a,None,lambda c:{'pass':True})
    assert not p.exists()

def test_power_interruption_recovers_previous_pair(tmp_path):
    a=candidate(tmp_path,'a');b=candidate(tmp_path,'b');p=tmp_path/AUTHORITY;p.parent.mkdir(parents=True)
    old=canonical(a);p.write_bytes(canonical(b));folder=tmp_path/'runtime/joint_release/interrupted';folder.mkdir(parents=True)
    (folder/'TRANSACTION.json').write_bytes(canonical(dict(state='PREPARED',candidate_digest=digest(p.read_bytes()))))
    (folder/'PREDECESSOR.json').write_bytes(canonical(dict(existed=True,raw=old.decode())))
    recover(tmp_path);assert p.read_bytes()==old


def test_unreadable_actual_predecessor_blocks_before_cas(tmp_path):
    a=candidate(tmp_path,'a');b=candidate(tmp_path,'b')
    activate(tmp_path,a,None,lambda c:{'pass':True})
    p=tmp_path/AUTHORITY;before=p.read_bytes()
    (tmp_path/a['snapshot']['manifest']['path']).write_text('changed')
    with pytest.raises(SourceInvalid,match='DIGEST_MISMATCH'):
        activate(tmp_path,b,digest(before),lambda c:pytest.fail('must reject before health'))
    assert p.read_bytes()==before


@pytest.mark.parametrize('failure',['day','head','binding'])
def test_actual_owner_snapshot_identity_checked_before_cas(tmp_path,failure):
    a=candidate(tmp_path,'a');p=tmp_path/AUTHORITY
    manifest_path=tmp_path/a['snapshot']['manifest']['path']
    manifest=json.loads(manifest_path.read_bytes());manifest['context']['data_head_digest']='input'
    owner=dict(trade_date=a['trade_date'],input_data_head=dict(path='data/head',sha256='input'))
    a['daily_owner_authorities']={n:dict(owner) for n in ('market','sector','stocks','market_center','forward')}
    (tmp_path/'data/head').write_bytes(b'input')
    head_digest=digest(b'input');manifest['context']['data_head_digest']=head_digest
    for o in a['daily_owner_authorities'].values():o['input_data_head']=dict(path='data/head',sha256=head_digest)
    manifest['domain_features']={}
    for name,keys in {'market':('market','history'),'sector':('native','factors','profiles'),'stocks':('series','factors','profiles')}.items():
        values={k:manifest['database'] for k in keys}
        manifest['domain_features'][name]=dict(values);a['daily_owner_authorities'][name].update(values)
    manifest_path.write_bytes(canonical(manifest));a['snapshot']['manifest']['sha256']=digest(manifest_path.read_bytes())
    if failure=='day':a['daily_owner_authorities']['stocks']['trade_date']='2026-09-29'
    elif failure=='head':a['daily_owner_authorities']['stocks']['input_data_head']={'sha256':'wrong'}
    else:a['daily_owner_authorities']['stocks']['series']={'path':'other','sha256':'other'}
    with pytest.raises(SourceInvalid,match='JOINT_OWNER_'):
        activate(tmp_path,a,None,lambda c:pytest.fail('must reject before health'))
    assert not p.exists()


def test_frozen_owner_identity_does_not_depend_on_moving_input_pointer(tmp_path):
    a=candidate(tmp_path,'healthy')
    manifest_path=tmp_path/a['snapshot']['manifest']['path']
    manifest=json.loads(manifest_path.read_bytes())
    manifest['context']['data_head_digest']='frozen_input_identity'
    manifest['domain_features']={}
    owners={n:dict(trade_date=a['trade_date'],input_data_head=dict(path='data/moving_head.json',sha256='frozen_input_identity'))
            for n in ('market','sector','stocks','market_center','forward')}
    for name,keys in {'sector':('native','factors','profiles'),'stocks':('series','factors','profiles')}.items():
        owners[name].update({k:manifest['database'] for k in keys})
        manifest['domain_features'][name]={k:manifest['database'] for k in keys}
    for name,key in [('market','market'),('market_center','publication'),('forward','publication')]:
        manifest['domain_features'][name]={'accepted_payload':name}
        path=tmp_path/('data/'+name+'.json');path.write_bytes(canonical(manifest['domain_features'][name]))
        owners[name][key]=dict(path=path.relative_to(tmp_path).as_posix(),sha256=digest(path.read_bytes()))
    a['daily_owner_authorities']=owners
    manifest_path.write_bytes(canonical(manifest));a['snapshot']['manifest']['sha256']=digest(manifest_path.read_bytes())
    (tmp_path/'data/moving_head.json').write_bytes(b'next_day_input')
    validate(tmp_path,a)
    owners['forward']['publication']=owners['market']['market']
    with pytest.raises(SourceInvalid,match='BINDING_MISMATCH:forward'):
        validate(tmp_path,a)
