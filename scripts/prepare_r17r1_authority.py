"""Append-only authority repair; no owner or runtime algorithm changes."""
import json, shutil
from copy import deepcopy
from pathlib import Path
from scripts.prepare_r17_governance import ROOT, bind, put
from src.workbench_analysis.v4_13_io import digest, atomic, canonical
BASE='204d799f26a7badbce3d6b09d3ceed722c522c91'
HEAD='data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'
OLD_HEAD='data/v4/V4_13_ACCEPTED_HEAD.json'
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
CLOSURE='config/v4_13_active_contract_family_closure_r17r1.json'
ENTRY='config/v4_13_accepted_entry_contract_v1_1.json'
DOCS=['V4_R17_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md','V4_13_R17R1A_ACCEPTED_PACKAGE_ACTIVE_BINDING_REPAIR_TASK_20261003.md','V4_14_R17R1B_CONTRACT_REFREEZE_ACTIVE_AUTHORITY_TASK_20261003.md','V4_NEXT_ROUND_EXECUTION_MASTER_R17R1_20261003.md']
def read(p):return json.loads((ROOT/p).read_bytes())
def successor(old,new,mutate,version='1.2.0'):
    assert not (ROOT/new).exists()
    obj=deepcopy(read(old)); mutate(obj);obj.update(version=version,supersedes=bind(old));put(new,obj);return bind(new)
def prepare():
    assert not (ROOT/HEAD).exists()
    dest=ROOT/'docs/evidence/r17r1';dest.mkdir(parents=True,exist_ok=True)
    (dest/'.gitattributes').write_text('* -text\n',encoding='utf8')
    for name in DOCS:atomic(ROOT,'docs/evidence/r17r1/'+name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes(),append_only=True)
    out=ROOT/'reports/r17r1a';out.mkdir(parents=True,exist_ok=True);(out/'.gitattributes').write_text('* -text\n')
    old=read(OLD_HEAD); stage=read(STAGE)
    protected=[bind(p) for p in ['AGENTS.md','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json',OLD_HEAD]]
    protected += [bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'reports/v4_13_runtime_r16/real/2026-09-30/r6').rglob('*')) if p.is_file()]
    put('reports/r17r1a/stage_contract.json',dict(baseline=BASE,documents=[bind('docs/evidence/r17r1/'+n) for n in DOCS],protected=protected,scope='FORMAL_ACTIVE_BINDING_CONSISTENCY_REPAIR',next='R17R1B_AFTER_PASS',additional_binding_repairs=['DAG enrichment consumer','field registry enrichment consumer','output schema enrichment consumer','retained oracle reference explicitly historical']))
    projection=bind('config/v4_13_projection_v1_2.json')
    enrichment=successor('config/v4_13_rotation_structure_enrichment_schema_v1_1.json','config/v4_13_rotation_structure_enrichment_schema_v1_2.json',lambda x:x.update(structure_schema=projection))
    def dag(x):
        for e in x['edges']:
            if e['field']=='structure_projection':e['contract_binding']=projection;e['version']='1.2.0'
            if e['field']=='rotation_structure_enrichment':e['contract_binding']=enrichment;e['version']='1.2.0'
    mapping={
      'config/v4_13_rotation_structure_enrichment_schema_v1_1.json':enrichment,
      'config/v4_13_dag_edge_registry_v1_1.json':successor('config/v4_13_dag_edge_registry_v1_1.json','config/v4_13_dag_edge_registry_v1_2.json',dag),
    }
    mapping['config/v4_13_field_registry_v1_1.json']=successor('config/v4_13_field_registry_v1_1.json','config/v4_13_field_registry_v1_2.json',lambda x:next(r for r in x['fields'] if r.get('object_schema',{}).get('path')=='config/v4_13_rotation_structure_enrichment_schema_v1_1.json').update(object_schema=enrichment))
    mapping['config/v4_13_output_schema_v1_1.json']=successor('config/v4_13_output_schema_v1_1.json','config/v4_13_output_schema_v1_2.json',lambda x:x['object_schemas'].update(rotation_structure_enrichment=enrichment))
    def oracle(x):x.setdefault('historical_lineage',{})['retained_R1_vectors']=x.pop('retained_R1_vectors')
    mapping['config/v4_13_machine_vectors_v1_1.json']=successor('config/v4_13_machine_vectors_v1_1.json','config/v4_13_machine_vectors_v1_2.json',oracle)
    refs=[mapping.get(r['path'],r) for r in old['contract_refs']]
    families={read(r['path'])['contract_id']:dict(active=r,version=read(r['path'])['version'],lineage={k:read(r['path'])[k] for k in ['supersedes','derived_from','historical_lineage'] if k in read(r['path'])}) for r in refs}
    put(CLOSURE,dict(contract_id='V4_13_ACTIVE_CONTRACT_FAMILY_CLOSURE_V1',version='1.0.0',families=families,selection='EXPLICIT_ACCEPTED_PACKAGE_NO_DIRECTORY_LATEST_SCAN',lineage_roles=['supersedes','derived_from','historical_lineage']))
    entry=deepcopy(read('config/v4_13_accepted_entry_contract_v1.json'))
    entry.update(version='1.1.0',supersedes=bind('config/v4_13_accepted_entry_contract_v1.json'),authority_namespace=HEAD,contract_refs=refs,contract_digest=digest(refs),active_family_closure=bind(CLOSURE),historical_lineage=dict(candidate_original_package=dict(contract_refs=old['contract_refs'],contract_digest=old['contract_digest'])))
    put(ENTRY,entry)
    archive='reports/r17r1a/PARENT_STAGE_HEAD.json';atomic(ROOT,archive,(ROOT/STAGE).read_bytes(),append_only=True)
    h=deepcopy(old);h.update(version='1.1.0',supersedes=bind(OLD_HEAD),amendment_scope='FORMAL_ACTIVE_BINDING_CONSISTENCY_REPAIR',amendment_authority=bind('docs/evidence/r17r1/'+DOCS[0]),amendment_task=bind('docs/evidence/r17r1/'+DOCS[1]),amendment_master=bind('docs/evidence/r17r1/'+DOCS[3]),formal_entry_contract=bind(ENTRY),contract_refs=refs,contract_digest=digest(refs),active_family_closure=bind(CLOSURE),historical_lineage=dict(original_publication_contract_refs=old['contract_refs'],original_publication_contract_digest=old['contract_digest']),amendment_parent_stage_archive=bind(archive))
    atomic(ROOT,HEAD,canonical(h)+b'\n',append_only=True)
    stage['v4_13_binding']=bind(HEAD);stage['v4_13_package_authority']=bind(ENTRY)
    atomic(ROOT,STAGE,canonical(stage)+b'\n')
if __name__=='__main__':prepare()
