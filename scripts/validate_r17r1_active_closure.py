"""Independent recursive active-family authority validation, no runtime imports."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
HEAD='data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'
CLOSURE='config/v4_13_active_contract_family_closure_r17r1.json'
LINEAGE={'supersedes','derived_from','historical_lineage'}
def read(p,root=ROOT):return json.loads((root/p).read_bytes())
def exact(ref,root=ROOT):
    p=(root/ref['path']).resolve();assert p.is_relative_to(root.resolve())
    raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref['bytes'],ref['path'];return raw
def canon(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def walk(value,families,root=ROOT,lineage=False,seen=None):
    seen=set() if seen is None else seen
    if isinstance(value,list):
        for v in value:walk(v,families,root,lineage,seen)
    elif isinstance(value,dict):
        if {'path','sha256','bytes'}<=value.keys():
            path=value['path']
            # A publication and its embedded package are historical evidence,
            # never the active package authority; recurse only explicit contracts.
            if path.startswith(('config/v4_13_','config/v4_14_')):
                obj=json.loads(exact(value,root));family=obj.get('contract_id')
                if family in families and not lineage:assert value==families[family]['active'],'SUPERSEDED_CURRENT_BINDING: '+path
                key=(path,lineage)
                if key not in seen:seen.add(key);walk(obj,families,root,lineage,seen)
            elif path=='data/v4/V4_13_ACCEPTED_HEAD.json':
                assert lineage,'IMMUTABLE_PREDECESSOR_IS_NOT_CURRENT_AUTHORITY';exact(value,root)
            elif path=='data/v4/V4_STAGE_ACCEPTED_HEAD.json':
                from src.workbench_analysis.historical_stage_governance_r17 import resolve
                resolve(root,value)
            elif path.startswith('SYNTHETIC_ENGINEERING_ONLY/'):
                # Frozen literal identities in owner oracle inputs, not files
                # or accepted authority. Contract paths never use this namespace.
                assert value['sha256']=='0'*64 and value['bytes']==0
            else:exact(value,root)
            return
        for k,v in value.items():walk(v,families,root,lineage or k in LINEAGE,seen)
def validate(root=ROOT):
    root=Path(root);h=read(HEAD,root);old=read('data/v4/V4_13_ACCEPTED_HEAD.json',root)
    assert hashlib.sha256((root/'data/v4/V4_13_ACCEPTED_HEAD.json').read_bytes()).hexdigest()=='f9d48096162d6c6de9f353251cc24715fb017243596131e45e6fcbaa5abb373c'
    stage=read('data/v4/V4_STAGE_ACCEPTED_HEAD.json',root)
    assert stage['v4_13_binding']['path']==HEAD;assert json.loads(exact(stage['v4_13_binding'],root))==h
    assert h['amendment_scope']=='FORMAL_ACTIVE_BINDING_CONSISTENCY_REPAIR'
    assert h['supersedes']['path']=='data/v4/V4_13_ACCEPTED_HEAD.json';exact(h['supersedes'],root)
    for k in ['candidate','artifact_refs','runtime_source_bindings','input_accepted_head_refs','capabilities','production','shadow','focus','global_mandatory_adoption','ALGORITHM_STATE_REPLAY_PASS','knowledge_lineage','AS_RECORDED','accepted_trade_date']:assert h[k]==old[k],k
    assert h['candidate']['sha256']=='a02e7918826627c2b496d89e546d3f5a408e4c68a1a89bc93946e152e7ca42ec';exact(h['candidate'],root)
    for k in ['amendment_authority','amendment_task','amendment_master']:exact(h[k],root)
    assert h['amendment_authority']==dict(path='docs/evidence/r17r1/V4_R17_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md',sha256='43a0b9c9cc953acd07a86c1efd226c5379f14e6e809783c3d853ce2d016e6db5',bytes=3442)
    for ref in read('reports/r17r1a/stage_contract.json',root)['protected']:
        exact(ref,root)
        prior=subprocess.check_output(['git','show','204d799f26a7badbce3d6b09d3ceed722c522c91:'+ref['path']],cwd=root)
        if prior.startswith(b'version https://git-lfs.github.com/spec/v1'):
            assert ('oid sha256:'+ref['sha256']).encode() in prior and ('size '+str(ref['bytes'])).encode() in prior
        else:assert hashlib.sha256(prior).hexdigest()==ref['sha256'] and len(prior)==ref['bytes']
    for ref in h['runtime_source_bindings']:
        exact(ref,root);exact(dict(ref,path=ref['original_path']),root)
    parent=json.loads(exact(h['amendment_parent_stage_archive'],root))
    assert h['amendment_parent_stage_archive']['sha256']=='87cb66c9dc90b4bb727fc69626fa22899c4e1a20c7bf2aa0d163102e0f07bf21'
    assert stage['accepted_stage_range']=='V4_00_TO_V4_13_ACCEPTED'
    assert all(stage[k]==v for k,v in parent.items() if k!='v4_13_binding')
    assert set(stage)-set(parent)=={'v4_13_package_authority'}
    entry=json.loads(exact(h['formal_entry_contract'],root));closure=json.loads(exact(h['active_family_closure'],root))
    assert stage['v4_13_package_authority']==h['formal_entry_contract']
    assert entry['authority_namespace']==HEAD and entry['contract_refs']==h['contract_refs']
    assert hashlib.sha256(canon(h['contract_refs'])).hexdigest()==h['contract_digest']==entry['contract_digest']
    assert entry['active_family_closure']==h['active_family_closure']
    families=closure['families'];assert len(families)==len(h['contract_refs'])==14
    authorized_paths={r['path'].replace('_v1_1.json','_v1_2.json') if any(r['path']=='config/v4_13_'+name+'_v1_1.json' for name in ['dag_edge_registry','rotation_structure_enrichment_schema','field_registry','output_schema','machine_vectors']) else r['path'] for r in old['contract_refs']}
    assert {r['path'] for r in h['contract_refs']}==authorized_paths,'UNAUTHORIZED_FAMILY_SELECTION'
    unchanged={r['path']:r for r in old['contract_refs'] if r['path'] in authorized_paths}
    for ref in h['contract_refs']:
        if ref['path'] in unchanged:assert ref==unchanged[ref['path']],'UNCHANGED_CONTRACT_IDENTITY_REQUIRED'
    assert {r['path'] for r in h['contract_refs']}=={f['active']['path'] for f in families.values()}
    for family,row in families.items():
        obj=json.loads(exact(row['active'],root));assert obj['contract_id']==family and obj['version']==row['version']
        if 'supersedes' in obj:
            prev=json.loads(exact(obj['supersedes'],root));assert prev['contract_id']==family
            assert tuple(map(int,obj['version'].split('.')))>tuple(map(int,prev['version'].split('.')))
    for family,path in [('PROFILE_ADVANCED_PROJECTION_V1','config/v4_13_projection_v1_2.json'),('V4_13_DAG_INTEGRATION_INTERFACE_V1','config/v4_13_dag_edge_registry_v1_2.json'),('ROTATION_STRUCTURE_ENRICHMENT_V1','config/v4_13_rotation_structure_enrichment_schema_v1_2.json')]:assert families[family]['active']['path']==path
    # Prove that the amendment changes references/lineage only. This comparison
    # is independent of the publisher and preserves every business field.
    for name in ['dag_edge_registry','rotation_structure_enrichment_schema','field_registry','output_schema','machine_vectors']:
        current=read('config/v4_13_'+name+'_v1_2.json',root)
        previous=read('config/v4_13_'+name+'_v1_1.json',root)
        normalized=json.loads(json.dumps(current));normalized['version']=previous['version']
        if 'supersedes' in previous:normalized['supersedes']=previous['supersedes']
        else:normalized.pop('supersedes')
        if name=='dag_edge_registry':
            for new,prior in zip(normalized['edges'],previous['edges']):
                if prior['field'] in ['structure_projection','rotation_structure_enrichment']:
                    new['contract_binding']=prior['contract_binding'];new['version']=prior['version']
        elif name=='rotation_structure_enrichment_schema':normalized['structure_schema']=previous['structure_schema']
        elif name=='field_registry':
            for new,prior in zip(normalized['fields'],previous['fields']):
                if prior.get('object_schema',{}).get('path')=='config/v4_13_rotation_structure_enrichment_schema_v1_1.json':new['object_schema']=prior['object_schema']
        elif name=='output_schema':normalized['object_schemas']['rotation_structure_enrichment']=previous['object_schemas']['rotation_structure_enrichment']
        elif name=='machine_vectors':normalized['retained_R1_vectors']=normalized.pop('historical_lineage')['retained_R1_vectors']
        assert normalized==previous,'BUSINESS_SEMANTICS_CHANGED: '+name
    walk(h['contract_refs'],families,root)
    return dict(status='PASS',ACTIVE_CONTRACT_FAMILY_CLOSURE='PASS',R17R1A_V4_13_ACTIVE_BINDING_REPAIR='PASS',V4_13_ACCEPTED_HEAD_AMENDED_R1='CREATED',family_count=len(families))
if __name__=='__main__':print(json.dumps(validate()))
