"""R26 vectors are engineering only; never accepted real Shadow evidence."""
import copy
import hashlib
import json
import os
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from workbench_service.shadow_context import COMPONENTS, PREFIX, ShadowContextReader, context_token, unknown

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'config/v4_17_shadow_ui_contract_v1.json').read_bytes())


def known(value):
    return {'value': value, 'quality': 'KNOWN', 'reason': None, 'source': {'test_vector': 'R26_NOT_REAL_EVIDENCE'}}


def fixture():
    context = dict(namespace='SHADOW_V4', trade_date='2026-10-08', publication_id='r26-sim-publication', publication_revision=2,
                   model_contract_id='RESEARCH_STATE_V1', parameter_set_id='R26_VECTOR', state_lineage_id='r26-vector-lineage',
                   daily_input_digest='d'*64, source_manifest_digest='s'*64, evidence_origin='ACTIVATION_SIMULATION')
    token = context_token(context)
    values = {
        'summary': dict(entity_id='SIM_STOCK_A', current_state='PREWATCH', reason_codes=['ENROLLED']),
        'radar': dict(entity_id='SIM_STOCK_A', entity_type='STOCK', eligibility='TRUE', state='PREWATCH', priority_primitives='ELIGIBLE'),
        'entity': dict(entity_id='SIM_STOCK_A', entity_type='STOCK', trend='OBSERVED_VECTOR_ONLY'),
        'cohort': dict(entity_id='SIM_STOCK_A', enrollment_id='SIM_ENROLLMENT', T0='2026-10-08', cohort_namespace='FIRST_OBSERVED', horizon=5, due_date='2026-10-15', outcome_status='PENDING', benchmark_ids={'market':'SIM_MARKET'}, control_assignment_ids={'A':'SIM_A'}),
        'settlement': dict(enrollment_id='SIM_ENROLLMENT', horizon=5, outcome_status='PENDING', outcome_revision='SIM_REV_2', bound_outcome_revision='SIM_REV_2', right_censor='RIGHT_CENSORED', revision_reason='ACCEPTED_EVALUATION_SOURCE_REVISION'),
        'health': dict(slot_status='ACCEPTED_ON_TIME', source_receipts=['SIM_RECEIPT'], publication_lineage='r26-sim-publication/rev2', capability_scope=['PURE_CORE_STOCK'], blocked_capabilities=['A04_H21_CONSUMER'], stop_state=False, rollback=True)
    }
    components = {}
    for name in COMPONENTS:
        fields = {key: known(value) if (value := values[name].get(key)) is not None else unknown() for key in CONTRACT['components'][name]['fields']}
        if name == 'settlement':
            fields['outcome'] = dict(value=None, quality='RIGHT_CENSORED', reason='PENDING_ENDPOINT', source=None)
        components[name] = dict(context_token=token, context=copy.deepcopy(context), source_quality='DEGRADED', items=[{'fields':fields}])
    return dict(context=context, context_token=token, source_quality='DEGRADED', real_sample_count=0,
                evidence_label='NOT_REAL_EVIDENCE', components=components)


def reader(bundle=None):
    return ShadowContextReader(ROOT, simulation_fixture=bundle)


def test_current_no_real_data_never_opens_database(monkeypatch):
    monkeypatch.setattr('sqlite3.connect', lambda *a, **k: pytest.fail('NO_REAL_DATA_MUST_NOT_OPEN_DB'))
    for name in ('context', *COMPONENTS):
        status, data = reader().handle(PREFIX+name, {})
        assert status == 200 and data['status'] == 'NO_REAL_SHADOW_DATA'
        assert data['context'] is None and data['real_sample_count'] == 0 and data['items'] == []


def test_all_components_same_token_refresh_deeplink_filter_pagination_unknown():
    bundle=fixture(); r=reader(bundle)
    assert r.handle(PREFIX+'context', {}) == r.handle(PREFIX+'context', {'context_token':bundle['context_token']})
    for name in COMPONENTS:
        query={'context_token':bundle['context_token']}
        status, data=r.handle(PREFIX+name, query)
        assert status == 200 and data['evidence_label'] == 'NOT_REAL_EVIDENCE' and data['real_sample_count'] == 0
        assert data['context_token'] == bundle['context_token'] and data['context'] == bundle['context']
        for filters in ({'q':'absent'}, {'page':'2'}, {'page_size':'1'}, {'entity_id':'absent'}):
            result=r.handle(PREFIX+name, query|filters)
            assert result[0]==200 and result[1]['context_token']==data['context_token']
    assert r.handle(PREFIX+'entity',query)[1]['items'][0]['fields']['position']['value'] is None
    assert r.handle(PREFIX+'settlement',query)[1]['items'][0]['fields']['outcome']['quality']=='RIGHT_CENSORED'
    bundle['context']['publication_id']='mutated_after_injection'
    assert r.handle(PREFIX+'context',{})[0]==200  # defensive copy


def test_corrected_observed_outcome_is_exact_revision():
    bundle=fixture(); fields=bundle['components']['settlement']['items'][0]['fields']
    fields.update(outcome_status=known('OBSERVED'), outcome=known(0.01), right_censor=known(False))
    status,data=reader(bundle).handle(PREFIX+'settlement',{'context_token':bundle['context_token']})
    assert status==200 and data['items'][0]['fields']['outcome_revision']['value']=='SIM_REV_2'


@pytest.mark.parametrize('case', [f'U{i:02}' for i in range(1,19)])
def test_negative_matrix(case):
    bundle=fixture(); query={'context_token':bundle['context_token']}; name='entity'; r=None
    if case in ('U01','U18'): query['context_token']='shadow-wrong'
    elif case in ('U02','U03','U04','U05','U06','U17'):
        key={'U02':'publication_id','U03':'publication_revision','U04':'trade_date','U05':'namespace','U06':'evidence_origin','U17':'model_contract_id'}[case];query[key]='mismatch'
    elif case=='U07':bundle['components'][name]['context_token']='other'
    elif case=='U08':r=reader();query={'simulation':'1'}
    elif case=='U09':r=reader();query={'source':'V3_PRODUCTION'}
    elif case=='U10':r=reader();query={'latest':'1','mtime':'newest'}
    elif case=='U11':bundle['components'][name]['items'][0]['fields']['position']=dict(value=0,quality='UNKNOWN',reason='MISSING',source=None)
    elif case=='U12':del bundle['components'][name]['source_quality']
    elif case=='U13':name='settlement';bundle['components'][name]['items'][0]['fields']['outcome_revision']=known('SIM_REV_1')
    elif case=='U14':name='settlement';bundle['components'][name]['items'][0]['fields']['outcome']=known(.1)
    elif case=='U15':query['pin_focus']='1'
    elif case=='U16':query['activate_production']='1'
    status,data=(r or reader(bundle)).handle(PREFIX+name,query)
    assert status==409 and data['status']=='BLOCKED' and data['items']==[]
    # scope failure preserves an unrelated component in the same context.
    if case in ('U07','U11','U12','U13','U14'):
        assert reader(bundle).handle(PREFIX+'health',{'context_token':bundle['context_token']})[0]==200


@pytest.mark.parametrize('change', ['lineage','namespace','origin','missing_quality','unknown_known','pending_known','unregistered_field','pagination'])
def test_extra_scope_guards(change):
    bundle=fixture(); name='entity';query={'context_token':bundle['context_token']}
    if change in ('lineage','namespace','origin'):
        key={'lineage':'state_lineage_id','namespace':'namespace','origin':'evidence_origin'}[change]
        bundle['components'][name]['context'][key]='wrong'
    elif change=='missing_quality':del bundle['source_quality']
    elif change=='unknown_known':bundle['components'][name]['items'][0]['fields']['position']=known('UNKNOWN')
    elif change=='pending_known':name='settlement';bundle['components'][name]['items'][0]['fields'].update(right_censor=known(False),outcome=known(0))
    elif change=='unregistered_field':bundle['components'][name]['items'][0]['fields']['BUY']=known(True)
    else:query['page']='0'
    assert reader(bundle).handle(PREFIX+name,query)[0]==409


def test_http_shared_service_read_only_and_existing_pages(tmp_path):
    import workbench_service.app as app
    from workbench_db import WorkbenchRepository
    db=tmp_path/'api.duckdb'
    with WorkbenchRepository(ROOT,db):pass
    handler=app.make_handler(ROOT,db)
    before=hashlib.sha256(db.read_bytes()).hexdigest()
    server=ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        for path in ('/v3','/v3/focus-tracker','/v4/shadow','/v4/shadow.js'):
            response=urllib.request.urlopen(base+path);assert response.status==200 and response.read()
        for method in ('POST','PUT','PATCH','DELETE'):
            for target in ('context','radar','focus/pin','production/activate','cohort','settlement'):
                req=urllib.request.Request(base+PREFIX+target,data=b'{}',method=method)
                with pytest.raises(urllib.error.HTTPError) as caught:urllib.request.urlopen(req)
                assert caught.value.code==405 and json.loads(caught.value.read())['code']=='SHADOW_READ_ONLY'
        assert json.loads(urllib.request.urlopen(base+PREFIX+'context').read())['status']=='NO_REAL_SHADOW_DATA'
        with pytest.raises(urllib.error.HTTPError) as caught:urllib.request.urlopen(base+PREFIX+'context?context_token=a&context_token=b')
        assert caught.value.code==409
        assert hashlib.sha256(db.read_bytes()).hexdigest()==before
    finally:server.shutdown();server.server_close();thread.join(2)


def test_browser_code_contract_and_unknown_guard(tmp_path):
    bundle=fixture(); vector=tmp_path/'vector.json';vector.write_text(json.dumps(bundle),encoding='utf8')
    js=ROOT/'src/workbench_service/static/shadow-v4.js'
    code="""
const assert=require('node:assert/strict');const ui=require(process.argv[1]);const b=JSON.parse(require('node:fs').readFileSync(process.argv[2],'utf8'));
(async()=>{assert.equal(await ui.tokenFor(b.context),b.context_token);assert.deepEqual(Object.keys(ui.registry),Object.keys(b.components));
for(const [k,c] of Object.entries(b.components)){assert.deepEqual(Object.keys(ui.registry[k][1]),Object.keys(c.items[0].fields));await ui.validate({...b,status:'ACTIVATION_SIMULATION',...c},b);}
assert.match(ui.cellText({value:null,quality:'UNKNOWN',reason:'MISSING'}),/UNKNOWN/);assert.throws(()=>ui.cellText({value:0,quality:'UNKNOWN'}));
assert.throws(()=>ui.cellText({value:'UNKNOWN',quality:'KNOWN',source:'x'}));await assert.rejects(ui.validate({...b,status:'READY'},b));
await assert.rejects(ui.validate({...b,status:'ACTIVATION_SIMULATION',context_token:'wrong'},b));
console.log('PASS_JS_CONTEXT_QUALITY_ORIGIN_REGISTRY');})().catch(e=>{console.error(e);process.exit(1)});
"""
    result=subprocess.run(['node','-e',code,str(js),str(vector)],capture_output=True,text=True,check=True)
    assert 'PASS_JS_CONTEXT' in result.stdout


def test_readback_config_has_no_real_acceptance():
    config=json.loads((ROOT/'config/v4_17_shadow_ui_source_v1.json').read_bytes())
    assert config['accepted_readback'] is None and config['external_acceptance'] is None
    for name in ('V4_16_ACCEPTED_HEAD.json','V4_17_ACCEPTED_HEAD.json'):
        assert not (ROOT/'config'/name).exists()


def native_vector(tmp_path):
    """Synthetic read-only storage proof, never repository real evidence."""
    import sqlite3
    from workbench_service.shadow_context import canonical,digest
    root=tmp_path/'native-vector';(root/'config').mkdir(parents=True)
    (root/'config/v4_17_shadow_ui_contract_v1.json').write_bytes((ROOT/'config/v4_17_shadow_ui_contract_v1.json').read_bytes())
    context=fixture()['context'];context['evidence_origin']='PIT_OBSERVED';token=context_token(context)
    common=dict(publication_id=context['publication_id'],revision=2,trade_date=context['trade_date'])
    records={'publication':dict(common,slot_id='SIM_SLOT',source_manifest_digest=context['source_manifest_digest']),
             'slot':dict(common,slot_id='SIM_SLOT',slot_status='ACCEPTED_ON_TIME',source_manifest_digest=context['source_manifest_digest'],parameter_set_id=context['parameter_set_id'],model_contract_id=context['model_contract_id'],state_lineage_id=context['state_lineage_id']),
             'state':dict(common,model_contract_id=context['model_contract_id'],state_lineage_id=context['state_lineage_id']),
             'daily_input':dict(daily_input_digest=context['daily_input_digest'],target_trade_date=context['trade_date']),
             'health':dict(publication_id=context['publication_id'],PIT_OBSERVED_REAL_SAMPLES=0)}
    db=root/'synthetic.sqlite';facts={}
    with sqlite3.connect(db) as con:
        con.executescript((ROOT/'migrations/v4_16_r24_real_shadow_v1.sql').read_text())
        con.execute("INSERT INTO storage_identity VALUES(1,'REAL','PIT_OBSERVED')")
        for kind,value in records.items():
            value.update(namespace='SHADOW_V4',execution_mode='SHADOW',evidence_origin='PIT_OBSERVED')
            sha=digest(value);con.execute('INSERT INTO facts VALUES(?,?,?,?,?,?,?)',(kind,kind,'SHADOW_V4','SHADOW','PIT_OBSERVED',canonical(value).decode(),sha))
            facts[kind]=dict(kind=kind,id=kind,sha256=sha)
    manifest=dict(context=context,database_path='synthetic.sqlite',facts=facts,components={k:[{}] for k in COMPONENTS},source_quality='UNKNOWN')
    manifest['components']['health']=[{'slot_status':dict(fact='slot',path='slot_status',quality='KNOWN')}]
    def save(name,value):
        raw=canonical(value);(root/name).write_bytes(raw);return dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    binding=save('manifest.json',manifest)
    receipt=save('receipt.json',dict(decision='PASS_REAL_SHADOW_UI_READBACK',readback_sha256=binding['sha256'],context_token=token))
    config=dict(contract_id='V4_17_EXACT_READBACK_SOURCE_V1',accepted_readback=binding,external_acceptance=receipt)
    save('config/v4_17_shadow_ui_source_v1.json',config)
    return root,manifest,config,save


def test_native_exact_readonly_storage_projection(tmp_path):
    root,manifest,config,save=native_vector(tmp_path)
    db=root/'synthetic.sqlite';before=db.read_bytes();r=ShadowContextReader(root)
    for name in ('context',*COMPONENTS):
        status,data=r.handle(PREFIX+name,{} if name=='context' else {'context_token':context_token(manifest['context'])})
        assert status==200 and data['status']=='READY' and data['real_sample_count']==0
    assert db.read_bytes()==before
    assert not (root/'synthetic.sqlite-journal').exists()
    health=r.handle(PREFIX+'health',{'context_token':context_token(manifest['context'])})[1]['items'][0]['fields']
    assert health['slot_status']['value']=='ACCEPTED_ON_TIME' and health['source_receipts']['quality']=='UNKNOWN'


@pytest.mark.parametrize('change',['receipt','fact_digest','slot_model','storage_origin','path_escape','absent_db','field_path','field_kind'])
def test_native_readback_fail_closed(tmp_path,change):
    root,manifest,config,save=native_vector(tmp_path)
    if change=='receipt':config['external_acceptance']=save('receipt.json',dict(decision='NOT_ACCEPTED'))
    elif change=='fact_digest':manifest['facts']['slot']['sha256']='0'*64
    elif change=='slot_model':manifest['context']['model_contract_id']='different'
    elif change=='storage_origin':
        # different explicitly pinned database; origin mismatch cannot fall back.
        import sqlite3
        path=root/'other.sqlite'
        with sqlite3.connect(path) as con:
            con.execute('CREATE TABLE storage_identity(singleton,environment,evidence_origin)');con.execute("INSERT INTO storage_identity VALUES(1,'ACTIVATION_SIMULATION','ACTIVATION_SIMULATION')")
        manifest['database_path']='other.sqlite'
    elif change=='path_escape':manifest['database_path']='../outside.sqlite'
    elif change=='absent_db':manifest['database_path']='missing.sqlite'
    elif change=='field_path':manifest['components']['health'][0]['slot_status']['path']='not_registered'
    elif change=='field_kind':manifest['components']['health'][0]['slot_status']['fact']='health'
    if change!='receipt':
        config['accepted_readback']=save('manifest.json',manifest)
        config['external_acceptance']=save('receipt.json',dict(decision='PASS_REAL_SHADOW_UI_READBACK',readback_sha256=config['accepted_readback']['sha256'],context_token=context_token(manifest['context'])))
    save('config/v4_17_shadow_ui_source_v1.json',config)
    status,data=ShadowContextReader(root).handle(PREFIX+'context',{})
    if change in ('field_path','field_kind'):
        assert status==200
        status,data=ShadowContextReader(root).handle(PREFIX+'health',{'context_token':context_token(manifest['context'])})
        assert ShadowContextReader(root).handle(PREFIX+'entity',{'context_token':context_token(manifest['context'])})[0]==200
    assert status==409 and data['items']==[]
    if change=='absent_db':assert not (root/'missing.sqlite').exists()


def test_legacy_module_ast_identical_after_removing_additive_shadow_routes():
    import ast
    baseline=subprocess.check_output(['git','show','60b17524596918b66456fdd48dbc1beb068ab28a:src/workbench_service/app.py'],cwd=ROOT).decode()
    before=ast.parse(baseline);after=ast.parse((ROOT/'src/workbench_service/app.py').read_text(encoding='utf8'))
    function=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='make_handler')
    function.args.kwonlyargs=[];function.args.kw_defaults=[];function.body=function.body[3:]
    handler=next(n for n in function.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
    handler.body=[n for n in handler.body if not (isinstance(n,ast.FunctionDef) and n.name=='_shadow_write_rejected') and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('do_PUT','do_PATCH','do_DELETE') for t in n.targets))]
    for name,count in [('do_GET',3),('do_POST',1)]:
        method=next(n for n in handler.body if isinstance(n,ast.FunctionDef) and n.name==name)
        method.body=method.body[:1]+method.body[1+count:] if name=='do_GET' else method.body[count:]
    assert ast.dump(before)==ast.dump(after)


def test_bad_shadow_contract_preserves_existing_v3_http(monkeypatch,tmp_path):
    from workbench_service import app,shadow_context
    from workbench_service.research_context import ResearchContextError
    from workbench_db import WorkbenchRepository
    def bad(*a,**k):raise ResearchContextError('BROKEN_SHADOW_CONTRACT')
    monkeypatch.setattr(shadow_context,'ShadowContextReader',bad)
    db=tmp_path/'bad-contract.duckdb'
    with WorkbenchRepository(ROOT,db):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),app.make_handler(ROOT,db));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base=f'http://127.0.0.1:{server.server_port}'
        assert urllib.request.urlopen(base+'/v3').status==200
        with pytest.raises(urllib.error.HTTPError) as caught:urllib.request.urlopen(base+PREFIX+'context')
        assert caught.value.code==409
        assert json.loads(caught.value.read())['code']=='SHADOW_CONTRACT_INVALID'
    finally:server.shutdown();server.server_close();thread.join(2)
