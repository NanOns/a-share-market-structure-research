"""Independent publication oracle: never imports a V4-13 calculation helper."""
import sys,json,gzip,hashlib,subprocess
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
BASE='dcbfe610b5cb0a8d94dc743963a1fa80f7f71f32'


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


def validate(revisions=('r5',),clean=False):
    before=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    if clean:assert not before
    stage=read('reports/v4_13_runtime_r16/STAGE_CONTRACT.json');protected=[]
    for r in stage['protected']:
        b=exact(r);assert b==subprocess.check_output(['git','show',BASE+':'+r['path']],cwd=ROOT)
        protected.append(dict(path=r['path'],before=r['sha256'],after=hashlib.sha256(b).hexdigest(),byte_identical=True))
    for r in stage['contracts']:
        b=exact(r);assert b==subprocess.check_output(['git','show',BASE+':'+r['path']],cwd=ROOT)
    raw=[]
    for binding in stage['raw_qualification_protected']:
        payload=exact(binding);raw.append(dict(role=binding['role'],path=binding['path'],before=binding['sha256'],after=hashlib.sha256(payload).hexdigest(),unchanged=True))
    assert read('data/v4/V4_STAGE_ACCEPTED_HEAD.json')['accepted_stage_range']=='V4_00_TO_V4_12_ACCEPTED'
    assert read('data/v4/V4_DATA_ACCEPTED_HEAD.json')['accepted_trade_date']=='2026-09-30'
    assert not (ROOT/'data/v4/V4_13_ACCEPTED_HEAD.json').exists()
    member=read('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json');relations=defaultdict(list);sector_members=defaultdict(set)
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
        prior.append(m['prior_session_ref']);assert m['prior_session_ref']['trade_date']=='2026-09-29'
        projection=read('config/v4_13_projection_v1_1.json');owner=read('data/v4/V4_12_ACCEPTED_HEAD.json');structure={}
        source=next(r for r in owner['publication_authority']['authorized_manifests'] if r['sha256']==m['structure_source_digest'])
        source_manifest=json.loads(exact(source));assert source_manifest['trade_date']=='2026-09-30'
        artifact=next(r for r in source_manifest['artifacts'] if 'runtime_security' in r['path'])
        for original in records(artifact):
            active=original['active_selection']['active_anchor_id']
            selected=next((a for a in original['anchor_states'] if a.get('anchor_id')==active),None) if active else None
            original['selected_anchor_state']=selected;expected={}
            for name,source_path in projection['source_field_paths'].items():
                value=original
                for part in source_path.split('.'):value=value.get(part) if isinstance(value,dict) else None
                expected[name]=dict(value=value.get('value') if isinstance(value,dict) and 'quality' in value and 'value' in value else value)
                if isinstance(value,dict) and 'quality' in value:expected[name]['quality']=value['quality']
            expected['active_anchor_id']['quality']=original['active_selection']['quality']
            expected['basic_breakout_state']['quality']=original['breakout_projection_quality']
            expected['basic_breakout_state']['reason']=original['breakout_projection_reason']
            structure[original['identity']['security_id']]=expected
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
                f=row['fields'][name];assert f['value']==expected['value'],(sid,name,'VALUE_COPY')
                if 'quality' in expected:assert f['quality']==expected['quality'],(sid,name,'QUALITY_COPY')
                if 'reason' in expected:assert f['reason']==expected['reason'],(sid,name,'REASON_COPY')
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
    return dict(V4_13_R16_RUNTIME_CANDIDATE='READY_FOR_EXTERNAL_AUDIT',V4_13_RUNTIME='IMPLEMENTED_SCOPED_ENGINEERING_CANDIDATE',V4_13_ACCEPTED_HEAD='NOT_CREATED',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT',baseline=BASE,source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),independent_runtime_oracle='PASS',persisted_synthetic_oracle=synthetic,publication_results=publication_results,raw_qualification_byte_proofs=raw,protected=protected,frozen_contracts='EXACT_UNCHANGED',clean_before=clean,clean_after=clean,stage='V4_00_TO_V4_12_ACCEPTED',data='2026-09-30',production=False,shadow=False,focus=False,global_mandatory_adoption=False,migration=False)


if __name__=='__main__':print(json.dumps(validate(tuple(sys.argv[1].split(',')) if len(sys.argv)>1 and not sys.argv[1].startswith('--') else ('r5',),'--clean' in sys.argv),sort_keys=True))
