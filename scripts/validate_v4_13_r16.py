"""Independent publication oracle: never imports a V4-13 calculation helper."""
import sys,json,gzip,hashlib,subprocess
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
BASE='92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff'

# Independent owner-schema mapping, deliberately not imported from runtime/config.
VALUE_PATHS={'active_anchor_id':'active_selection.active_anchor_id','anchor_view_asof_t':'selected_anchor_state.output_envelope.anchor_view_asof_t','basic_breakout_state':'basic_breakout_state','basic_pullback_state':'active_projection.basic_pullback_state','basic_recovery_state':'active_projection.basic_recovery_state','support_state':'active_projection.support_state','acceptance_state':'active_projection.acceptance_state','retest_count':'active_projection.retest_count','structure_events':'events','structure_health':'selected_anchor_state.output_envelope.structure_health'}
METADATA_PATHS={'active_anchor_id':'active_selection','anchor_view_asof_t':'selected_anchor_state.output_envelope.anchor_view_asof_t','basic_pullback_state':'selected_anchor_state.state_observations.pullback','basic_recovery_state':'selected_anchor_state.state_observations.recovery','support_state':'selected_anchor_state.state_observations.support','acceptance_state':'selected_anchor_state.state_observations.acceptance','retest_count':'selected_anchor_state.facts.prior_test_count','structure_health':'selected_anchor_state.output_envelope.structure_health'}
Q=['KNOWN','UNKNOWN','NOT_IMPLEMENTED','NOT_APPLICABLE','DEGRADED']
PAIR=[['KNOWN','DEGRADED','DEGRADED','DEGRADED','DEGRADED'],['DEGRADED','UNKNOWN','UNKNOWN','UNKNOWN','DEGRADED'],['DEGRADED','UNKNOWN','NOT_IMPLEMENTED','NOT_IMPLEMENTED','DEGRADED'],['DEGRADED','UNKNOWN','NOT_IMPLEMENTED','NOT_APPLICABLE','DEGRADED'],['DEGRADED']*5]
def quality_fold(items):
    result=items[0]
    for item in items[1:]:result=PAIR[Q.index(result)][Q.index(item)]
    return result

def source_value(row,path):
    for key in path.split('.'):
        if not isinstance(row,dict) or key not in row:return None,False
        row=row[key]
    return row,True

def structure_expected(original,source_ref):
    from copy import deepcopy
    row=deepcopy(original);active=row['active_selection']['active_anchor_id']
    row['selected_anchor_state']=next((s for s in row['anchor_states'] if s['anchor_id']==active),None) if active else None
    result={}
    for name,path in VALUE_PATHS.items():
        value,_=source_value(row,path);metadata=METADATA_PATHS.get(name)
        qpath='breakout_projection_quality' if name=='basic_breakout_state' else metadata+'.quality' if metadata else None
        rpath='breakout_projection_reason' if name=='basic_breakout_state' else metadata+'.reason' if metadata else None
        quality,qexists=source_value(row,qpath) if qpath else (None,False)
        reason,rexists=source_value(row,rpath) if rpath else (None,False)
        if not qexists or not rexists:quality='UNKNOWN';reason='UNKNOWN_ACCEPTED_SOURCE_METADATA_UNAVAILABLE'
        original_envelope=value if isinstance(value,dict) and 'value' in value and 'quality' in value else None
        if original_envelope and name in ['anchor_view_asof_t','structure_health']:value=original_envelope['value']
        provenance=dict(publication_contract_id='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST',value_source=path,quality_source=qpath,reason_source=rpath,selected_anchor_id=active,row_identity=row.get('identity'),source_ref=source_ref)
        result[name]=dict(value=value,quality=quality,reason=reason,source_identity=[source_ref] if source_ref else [],producer_identity=provenance,projection_provenance=provenance)
        if original_envelope:
            for key in ['producer_identity','source_identity','producer_contract_id']:
                if key in original_envelope:result[name][key]=original_envelope[key]
    return result

def assert_structure(actual,original,ref):
    for name,expected in structure_expected(original,ref).items():
        for key,value in expected.items():assert actual[name][key]==value,(name,key,'EXACT_OWNER_COPY')

def validate_witnesses(w=None):
    w=read('reports/v4_13_runtime_r16r1/runtime_witnesses.json') if w is None else w
    gates={};evidence={}
    assert {c['label'] for c in w['context_cases']}=={'complete','minimum','incomplete'}
    parameters=read('config/v4_08_algorithm_parameter_set_r5.json')
    parameters={p['parameter_id']:p['value'] for p in parameters['parameters']}
    from statistics import median
    for case in w['context_cases']:
        i=case['input'];a=case['actual'];members=sorted(r['security_id'] for r in i['memberships'] if r['sector_id']=='I' and r['security_id']!='target')
        assert a['primary_industry']['value']=='I' and a['supporting_concepts']['quality']=='NOT_APPLICABLE'
        row=a['contexts'][0];assert row['member_ids']==members and 'target' not in members
        known=[i['current'][s]['fields']['ret1']['value'] for s in members if s in i['current']]
        coverage=len(known)/len(members);assert row['native_fields']['sector_quote_coverage']['value']==coverage
        assert row['native_fields']['sector_rs1']['value']==median(known) # incomplete members never zero-filled
        assert row['native_fields']['sector_member_count']['value']==len(members)
        eligible=len(members)>=parameters['V4_08_SECTOR_MIN_MEMBERS'] and coverage>=parameters['V4_08_SECTOR_MIN_QUOTE_COVERAGE']
        assert a['relative_sector_state']['quality']==('KNOWN' if eligible else 'UNKNOWN')
        if case['label']=='complete':
            assert a['relative_sector_state']['value']=='LEADING_ACCELERATING'
            assert a['relative_sector_state']['relative_substitutions']==dict(rps5=70,rps20=85,rps20_delta3=1,rel_market_1=98,rel_market_5=98)
            assert row['native_fields']['seed_width']['value']==0 and row['native_fields']['seed_width']['n']==5
    for code in ['O01','O02','O03','O05']:gates[code]='PASS'
    assert len(w['selector_cases'])==12
    for c in w['selector_cases']:
        ordered=sorted(c['input'],key=lambda r:(-int(r['confirmed_raw']),-int(r['warm_raw']),{'HIGH':0,'MEDIUM':1,'LOW':2}[r['emergence']],-r['adjusted_seed_width'],r['sector_id']))
        assert c['actual']['quality']=='KNOWN' and c['actual']['value']==ordered[0]['sector_id']
    gates['O04']='PASS'
    assert {(c['input'][0],c['input'][1]) for c in w['quality_cases']}=={(a,b) for a in Q for b in Q}
    for c in w['quality_cases']:assert c['actual']==quality_fold(c['input'])
    gates['O06']='PASS'
    assert len(w['structure_cases'])>=12
    for c in w['structure_cases']:assert_structure(c['actual'],c['input'],c['source_ref'])
    assert len(w['authorized_structure_cases'])>=10
    for c in w['authorized_structure_cases']:
        manifest=json.loads(exact(c['manifest_ref']));assert c['artifact_ref'] in manifest['artifacts']
        assert c['input']==next(records(c['artifact_ref']))
        assert_structure(c['actual'],c['input'],c['artifact_ref'])
    gates['O07']='PASS'
    assert {(c['rotation']['quality'],c['structure']['quality']) for c in w['dual_cases']} >= {('KNOWN','UNKNOWN'),('UNKNOWN','KNOWN')}
    for c in w['dual_cases']:
        a=c['actual'];r=c['rotation'];s=c['structure']
        assert a==dict(rotation_core_state=r['value'],rotation_quality=r['quality'],rotation_source_ref=r['source_identity'],structure_component=s['value'],structure_quality=s['quality'],structure_source_ref=s['source_identity'],combined_quality=quality_fold([r['quality'],s['quality']]),reasons=[r['reason'],s['reason']])
    gates['O08']='PASS'
    for method in ['publish','publish_stream']:
        c=w[method+'_append_only'];assert c['before']==c['after'] and c['initial']==c['idempotent']
        assert c['manifest']['prior_session_ref']=={'trade_date':'2026-09-29'}
        assert c['manifest']['revision']=='r1'
    gates['O09']='PASS'
    cases={c['label']:c for c in w['negative_cases']}
    required={'producer_mismatch','path_mismatch','hash_mismatch','write_escape','revision_r0','revision_r01','revision_rX','revision_r1/../r2','publish_append_only_conflict','publish_stream_append_only_conflict'}
    assert required <= set(cases) and all(c['rejected'] for c in cases.values())
    for label in ['publish_append_only_conflict','publish_stream_append_only_conflict']:assert cases[label]['reason']=='APPEND_ONLY_REVISION_CONFLICT'
    assert w['revision_ordinals']=={'r9':9,'r10':10,'r11':11}
    gates['O10']='PASS'
    validate_provenance(w['provenance_cases'],'S','I','WITNESS_LOO')
    evidence['fresh_process_append_only_boundary']=independent_publication_probe()
    evidence.update(context_cases=len(w['context_cases']),selector_cases=len(w['selector_cases']),quality_cases=len(w['quality_cases']),structure_perturbations=len(w['structure_cases']),authorized_owner_cases=len(w['authorized_structure_cases']),dual_source_cases=len(w['dual_cases']),negative_cases=len(cases))
    assert set(gates)=={'O%02d'%i for i in range(1,11)} and set(gates.values())=={'PASS'}
    return dict(categories=gates,witness_evidence=evidence,status='PASS')

def independent_publication_probe():
    """Exercise actual writers in fresh processes; expected bytes use stdlib only."""
    import tempfile,os
    code="""import sys,json
from workbench_analysis.v4_13_publication import publish,publish_stream
root,method,value=sys.argv[1:];row=dict(security_id='ORACLE',trade_date='2026-09-30',revision='r1',value=int(value))
meta=dict(source_refs=[],diagnostics={},prior_session_ref={'trade_date':'2026-09-29'})
writer=publish if method=='publish' else publish_stream
try:
 ref=writer(root,method,'2026-09-30','r1',[row],[],meta) if method=='publish' else writer(root,method,'2026-09-30','r1',[(row,[])],meta)
 print(json.dumps(ref))
except ValueError as e:print(str(e));sys.exit(3)
"""
    proof=[]
    with tempfile.TemporaryDirectory(prefix='v4-13-independent-oracle-') as td:
        for method in ['publish','publish_stream']:
            def execute(value):return subprocess.run([sys.executable,'-c',code,td,method,str(value)],capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
            a=execute(1);assert a.returncode==0,a.stderr
            reference=json.loads(a.stdout);manifest=json.loads((Path(td)/reference['path']).read_bytes())
            profile=next(r for r in manifest['artifacts'] if 'profile_advanced' in r['path'])
            payload=(Path(td)/profile['path']).read_bytes()
            row=json.loads(gzip.decompress(payload));assert row==dict(security_id='ORACLE',trade_date='2026-09-30',revision='r1',value=1)
            initial={p.relative_to(td).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(td).rglob('*') if p.is_file()}
            same=execute(1);assert same.returncode==0 and json.loads(same.stdout)==reference
            conflict=execute(2);assert conflict.returncode==3 and conflict.stdout.strip()=='APPEND_ONLY_REVISION_CONFLICT'
            after={p.relative_to(td).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(td).rglob('*') if p.is_file()}
            assert after==initial
            proof.append(dict(method=method,manifest_sha256=reference['sha256'],initial=initial,after=after,conflict='REJECTED_IN_FRESH_PROCESS',idempotent='EXACT_SAME_BYTES'))
    return proof

VERIFIED=set()
PROVENANCE_VERIFIED=set()
def validate_provenance(components,sid,sector,loo):
    expected={'loo_b0_raw':('config/v4_08_sector_prewatch_contract_r5.json','V4_08_SECTOR_PREWATCH_B0_V2'), 'loo_confirmed_raw':('config/v4_08_b2_machine_ast_r5.json','V4_08_SECTOR_LEGACY_ADAPTER_B2_R5'),'loo_warm_raw':('config/v4_08_b2_machine_ast_r5.json','V4_08_SECTOR_LEGACY_ADAPTER_B2_R5'),'adjusted_seed_width':('config/v4_08_sector_native_contract_r5.json','V4_08_SECTOR_NATIVE_V1'),'rotation_core_state':('config/v4_08_rotation_core_contract_r5.json','ROTATION_CORE_V1_R3'),'relative_sector_state':('config/v4_04_algorithm_contracts_v3.json','RELATIVE_STATE_V1'),'emergence':('data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json','V4_08_ACCEPTED_EMERGENCE_CAPABILITY_UNAVAILABLE')}
    assert set(components)==set(expected)
    for name,refs in components.items():
        assert (refs[0]['path'],refs[0]['producer_contract_id'])==expected[name]
        for r in refs:
            key=(r['path'],r['sha256'],r['bytes'])
            if key not in VERIFIED:exact(r);VERIFIED.add(key)
            assert r['target_security_id']==sid and r['sector_id']==sector
            assert r['derivation_identity']==dict(contract_id='LOO_CONTEXT_V1',loo_identity=loo,excluded_target_id=sid,trade_date='2026-09-30')
            assert r['source_revision'] and r['availability_identity']
            identity=json.dumps({k:v for k,v in r.items() if k not in ['target_security_id','sector_id','derivation_identity']},sort_keys=True)
            if identity in PROVENANCE_VERIFIED:continue
            if r['source_role']=='EXACT_PIT_MEMBERSHIP':
                member=read('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json');snap=json.loads(exact(member['snapshot']))
                assert r['available_at']==snap['cutoff'] and r['source_revision']==snap['source_revision_id'] and r['trade_date']==snap['target_trade_date']
            else:
                assert r['available_at'] is None
                owner=r['availability_identity']['owner_ref'];h=json.loads(exact(owner))
                assert r['source_revision']['owner_sha256']==owner['sha256']
                assert r['source_revision']['owner_contract_id']==h['contract_id']
                assert r['source_revision']['artifact_sha256']==r['sha256']
                if r['source_role']=='UNDERLYING_ACCEPTED_PRIMITIVE_PUBLICATION':
                    artifact=h['accepted_artifact'] if h['stage']=='V4-04' else h['accepted_artifacts']['full_scope_factors'] if h['stage']=='V4-05' else h['candidate_artifact']
                    assert r['path']==artifact['path'] and r['sha256']==artifact['sha256'] and r['producer_contract_id']==h['contract_id']
                    date=h.get('target_trade_date',h.get('source_cutoff')) if h['stage']!='V4-07' else h['accepted_input']['trade_date']
                    assert r['trade_date']==date
            PROVENANCE_VERIFIED.add(identity)


def read(path):return json.loads((ROOT/path).read_bytes())
def exact(binding):
    path=(ROOT/binding['path']).resolve();assert path.is_relative_to(ROOT.resolve())
    b=path.read_bytes();assert hashlib.sha256(b).hexdigest()==binding['sha256']
    size=binding.get('bytes',binding.get('byte_count'));assert size is None or len(b)==size
    return b
def records(binding):
    exact(binding)
    with gzip.open(ROOT/binding['path'],'rt',encoding='utf8') as f:
        for line in f:yield json.loads(line)


def validate(revisions=('r6',),clean=False):
    before=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    if clean:assert not before
    stage=read('reports/v4_13_runtime_r16r1/STAGE_CONTRACT.json');protected=[]
    for r in stage['protected']:
        b=exact(r);assert b==subprocess.check_output(['git','show',BASE+':'+r['path']],cwd=ROOT)
        protected.append(dict(path=r['path'],before=r['sha256'],after=hashlib.sha256(b).hexdigest(),byte_identical=True))
    for r in stage['contracts']:
        b=exact(r)
        if r['path']=='config/v4_13_projection_v1_2.json':
            amendment=json.loads(b);old=json.loads(exact(amendment['supersedes']))
            assert amendment['contract_id']==old['contract_id'] and amendment['version']=='1.2.0'
            for key,value in old.items():
                if key not in ['version','supersedes','reason']:assert amendment[key]==value
            for name,spec in amendment['projection_mapping'].items():
                assert spec['value_source']==VALUE_PATHS[name]
                qpath='breakout_projection_quality' if name=='basic_breakout_state' else METADATA_PATHS[name]+'.quality' if name in METADATA_PATHS else None
                rpath='breakout_projection_reason' if name=='basic_breakout_state' else METADATA_PATHS[name]+'.reason' if name in METADATA_PATHS else None
                assert (spec['quality_source'],spec['reason_source'])==(qpath,rpath)
        else:assert b==subprocess.check_output(['git','show',BASE+':'+r['path']],cwd=ROOT)
    raw=[]
    for binding in stage['raw_qualification_protected']:
        payload=exact(binding);raw.append(dict(role=binding['role'],path=binding['path'],before=binding['sha256'],after=hashlib.sha256(payload).hexdigest(),unchanged=True))
    assert read('data/v4/V4_STAGE_ACCEPTED_HEAD.json')['accepted_stage_range']=='V4_00_TO_V4_12_ACCEPTED'
    assert read('data/v4/V4_DATA_ACCEPTED_HEAD.json')['accepted_trade_date']=='2026-09-30'
    assert not (ROOT/'data/v4/V4_13_ACCEPTED_HEAD.json').exists()
    old_manifest='reports/v4_13_runtime_r16/real/2026-09-30/r5/manifest.json'
    old_bytes=(ROOT/old_manifest).read_bytes()
    assert old_bytes==subprocess.check_output(['git','show',BASE+':'+old_manifest],cwd=ROOT)
    old=json.loads(old_bytes)
    for ref in old['artifacts']+[old['publication_index']]:exact(ref)
    member=read('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json');relations=defaultdict(list);sector_members=defaultdict(set)
    calendar_head=json.loads(exact(member['calendar_head']));calendar=json.loads(exact(calendar_head['accepted_extension']))
    sessions=calendar.get('sessions',calendar.get('trade_dates',[]));sessions=[s['trade_date'] if isinstance(s,dict) else s for s in sessions]
    previous_session=max(s for s in sessions if s<'2026-09-30')
    for row in records(member['facts']):
        if row['identity_status']=='MAPPED':
            relations[row['security_id']].append(row);sector_members[row['sector_id']].add(row['security_id'])
    prior=[];publication_results=[]
    for revision in revisions:
        path=f'reports/v4_13_runtime_r16/real/2026-09-30/{revision}/manifest.json';m=read(path)
        assert m['formal_accepted'] is False and m['AS_RECORDED'] is False and m['knowledge_lineage']=='RECONSTRUCTED_CORRECTED'
        assert not any(m[k] for k in ['production','shadow','focus','global_mandatory_adoption'])
        assert m['contract_refs']==stage['contracts']
        for r in m['runtime_source_refs']:
            source_bytes=exact(r)
            assert source_bytes==(ROOT/r['original_path']).read_bytes()
        for r in m['input_accepted_head_refs']:exact(r)
        prior.append(m['prior_session_ref']);assert m['prior_session_ref']['trade_date']==previous_session=='2026-09-29'
        assert m['prior_session_ref']['calendar_head']==member['calendar_head'] and m['prior_session_ref']['calendar']==calendar_head['accepted_extension']
        owner=read('data/v4/V4_12_ACCEPTED_HEAD.json');structure={}
        source=next(r for r in owner['publication_authority']['authorized_manifests'] if r['sha256']==m['structure_source_digest'])
        source_manifest=json.loads(exact(source));assert source_manifest['trade_date']=='2026-09-30'
        artifact=next(r for r in source_manifest['artifacts'] if 'runtime_security' in r['path'])
        source_ref=dict(**artifact,producer_contract_id=source_manifest['contract_id'],trade_date=source_manifest['trade_date'],available_at=source_manifest['available_at'],availability_identity=dict(kind='AUTHORIZED_MANIFEST_AVAILABLE_AT',manifest_ref=source),source_revision=source_manifest['revision'],authorized_manifest_ref=source,accepted_owner_ref=next(r for r in m['input_accepted_head_refs'] if r['path']=='data/v4/V4_12_ACCEPTED_HEAD.json'))
        for original in records(artifact):
            structure[original['identity']['security_id']]=structure_expected(original,source_ref)
        fields={r['field'] for r in read('config/v4_13_field_registry_v1_1.json')['fields']};seen=set();counts=Counter()
        bindings={Path(r['path']).name:r for r in m['artifacts']}
        exact(m['publication_index'])
        for r in m['artifacts']:exact(r)
        for row in records(bindings['profile_advanced.jsonl.gz']):
            sid=row['security_id'];assert sid not in seen;seen.add(sid)
            assert row['revision']==revision and row['trade_date']=='2026-09-30' and row['prior_session_ref']==m['prior_session_ref']
            assert set(row['fields'])==fields and row['raw_qualification_before']==row['raw_qualification_after']
            industry=sorted({r['sector_id'] for r in relations[sid] if r['sector_type']=='INDUSTRY'})
            concepts=sorted({r['sector_id'] for r in relations[sid] if r['sector_type']=='THEME'})
            assert len(industry)==1
            assert row['fields']['primary_industry']['value']==industry[0] and row['fields']['primary_industry']['quality']=='KNOWN'
            assert row['fields']['supporting_concepts']['value']==concepts
            assert row['fields']['supporting_concepts']['quality']==('KNOWN' if concepts else 'NOT_APPLICABLE')
            assert row['fields']['algorithmic_support_sector']['quality']=='UNKNOWN'
            assert row['fields']['sector_context_state']['value']['loo_confirmed_raw']['quality']=='NOT_IMPLEMENTED'
            for name,expected in structure[sid].items():
                f=row['fields'][name]
                for key,value in expected.items():assert f[key]==value,(sid,name,key,'OWNER_EXACT_COPY')
            context=row['fields']['sector_context_state'];components=read('config/v4_13_sector_context_state_schema_v1_1.json')['components']
            validate_provenance({n:context['value'][n]['source_refs'] for n in components},sid,None,row['loo_identity'])
            assert context['quality']==context['value']['context_quality']==quality_fold([context['value'][n]['quality'] for n in components])
            enrichment=row['fields']['rotation_structure_enrichment'];e=enrichment['value']
            for name in structure[sid]:
                for key,value in e['structure_component'][name].items():assert row['fields'][name][key]==value
            assert e['structure_quality']==quality_fold([row['fields'][n]['quality'] for n in VALUE_PATHS])
            assert enrichment['quality']==e['combined_quality']==quality_fold([e['rotation_quality'],e['structure_quality']])
            assert e['structure_source_ref']==[source_ref]
            validate_provenance({'rotation_core_state':e['rotation_source_ref'],**{n:context['value'][n]['source_refs'] for n in components if n!='rotation_core_state'}},sid,None,row['loo_identity'])
            for name,f in row['fields'].items():
                assert f['source_identity'] and f['producer_contract_id']
                counts[name+':'+f['quality']]+=1
        assert len(seen)==m['profile_count']==member['formal_rows_by_type']['INDUSTRY']==5224
        total=0
        for row in records(bindings['loo_context.jsonl.gz']):
            total+=1;sid=row['security_id'];assert sid==row['excluded_target_id'] and sid not in row['member_ids']
            expected=sorted(sector_members[row['sector_id']]-{sid})
            assert row['member_ids']==expected
            assert row['b2']['confirmed_raw']=='UNKNOWN' and row['b2']['warm_raw']=='UNKNOWN'
            assert row['native_fields']['sector_member_count']['value']==len(expected)
            assert row['native_fields']['sector_quote_coverage']['value'] is None
            assert row['native_fields']['sector_rs1']['value'] is None
            assert row['relative_sector_state']['quality']=='UNKNOWN'
        assert total==m['context_count']
        diagnostics=read(bindings['diagnostics.json']['path']);assert set(diagnostics['authority_counters'].values())=={0};assert dict(counts)==diagnostics['field_quality_counts']
        publication_results.append(dict(revision=revision,path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),profiles=len(seen),contexts=total,field_quality_counts=dict(counts),authority_counters=diagnostics['authority_counters']))
    synthetic=[]
    for revision in ['r1','r2','r3']:
        sm=read(f'reports/v4_13_runtime_r16/synthetic_closed/2026-09-30/{revision}/manifest.json')
        expected=json.loads(exact(sm['independent_expected_ref']))
        pb=next(r for r in sm['artifacts'] if 'profile_advanced' in r['path']);cb=next(r for r in sm['artifacts'] if 'loo_context' in r['path'])
        profile=next(records(pb));context=next(r for r in records(cb) if r['sector_id']=='I')
        for field in ['primary_industry','supporting_concepts','relative_sector_state']:assert profile['fields'][field]['value']==expected[field]
        assert profile['fields']['algorithmic_support_sector']['quality']==expected['algorithmic_support_quality']
        assert context['member_ids']==expected['loo_member_ids'] and context['native_fields']['sector_rs1']['value']==expected['sector_rs1']
        assert context['native_fields']['seed_width']['value']==expected['seed_width']
        assert sm['prior_session_ref']['trade_date']==expected['prior_session']=='2026-09-29'
        synthetic.append(dict(revision=revision,status='PASS',source_digest=sm['membership_digest'],prior_session_ref=sm['prior_session_ref']))
    assert synthetic[0]['source_digest']!=synthetic[1]['source_digest']
    assert all(p==prior[0] for p in prior)
    changes=subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=ROOT,text=True).splitlines()
    assert not any('migration' in p or p.startswith('data/') for p in changes)
    assert all(not p.startswith('src/') or p in stage['runtime_files'] for p in changes)
    assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)==before
    oracle=validate_witnesses()
    return dict(R16R1_PROJECTION_PROVENANCE_ORACLE_REPAIR='PASS',V4_13_R16R1_RUNTIME_CANDIDATE='READY_FOR_EXTERNAL_AUDIT',V4_13_RUNTIME='IMPLEMENTED_SCOPED_ENGINEERING_CANDIDATE_REPAIRED',V4_13_ACCEPTED_HEAD='NOT_CREATED',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT',baseline=BASE,source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),independent_runtime_oracle=oracle['status'],independent_oracle_O01_O10=oracle,persisted_synthetic_oracle=synthetic,publication_results=publication_results,raw_qualification_byte_proofs=raw,protected=protected,prior_r5_protection=dict(manifest_sha256=hashlib.sha256(old_bytes).hexdigest(),all_artifacts='EXACT_UNCHANGED'),runtime_source_refs=m['runtime_source_refs'],contract_amendment_decision=read('reports/v4_13_runtime_r16r1/contract_amendment_decision.json'),clean_before=clean,clean_after=clean,stage='V4_00_TO_V4_12_ACCEPTED',data='2026-09-30',production=False,shadow=False,focus=False,global_mandatory_adoption=False,migration=False)


if __name__=='__main__':print(json.dumps(validate(tuple(sys.argv[1].split(',')) if len(sys.argv)>1 and not sys.argv[1].startswith('--') else ('r6',),'--clean' in sys.argv),sort_keys=True))
