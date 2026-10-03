"""Authority-only V4-14 successors; preserve literal replay semantics."""
from copy import deepcopy
import json
from scripts.prepare_r17_governance import ROOT,bind,put
from scripts.prepare_r17r1_authority import HEAD,CLOSURE,read
from scripts.validate_r17r1_active_closure import validate
NAMES=['replay_gate_b_contract','replay_case_registry','temporal_non_edge_registry','quality_degradation','machine_vectors']
def prepare():
    assert validate()['status']=='PASS' and read('reports/r17r1a/completion_gate.json')['R17R1A_V4_13_ACTIVE_BINDING_REPAIR']=='PASS'
    out=ROOT/'reports/r17r1b';out.mkdir(parents=True,exist_ok=True);(out/'.gitattributes').write_text('* -text\n')
    put('reports/r17r1b/stage_contract.json',dict(baseline='204d799f26a7badbce3d6b09d3ceed722c522c91',entry_gate=bind('reports/r17r1a/completion_gate.json'),protected={p:bind(p) for p in ['AGENTS.md','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json','data/v4/V4_13_ACCEPTED_HEAD.json',HEAD,'data/v4/V4_STAGE_ACCEPTED_HEAD.json']},scope='CONTRACT_AUTHORITY_REFREEZE_ONLY',task=bind('docs/evidence/r17r1/V4_14_R17R1B_CONTRACT_REFREEZE_ACTIVE_AUTHORITY_TASK_20261003.md'),next='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'))
    h=read(HEAD);old=read('data/v4/V4_13_ACCEPTED_HEAD.json')
    mapping={a['path']:b for a,b in zip(old['contract_refs'],h['contract_refs']) if a!=b}
    mapping['config/v4_13_projection_v1.json']=bind('config/v4_13_projection_v1_2.json')
    mapping['data/v4/V4_13_ACCEPTED_HEAD.json']=bind(HEAD)
    def remap(x,lineage=False):
        if isinstance(x,list):return [remap(v,lineage) for v in x]
        if isinstance(x,dict):
            if {'path','sha256','bytes'}<=x.keys():return deepcopy(mapping.get(x['path'],x)) if not lineage else deepcopy(x)
            return {k:remap(v,lineage or k in ['supersedes','derived_from','historical_lineage']) for k,v in x.items()}
        return x
    witness=remap(read('reports/r17c/owner_oracle_witnesses.json'));witness.update(version='1.1.0',supersedes=bind('reports/r17c/owner_oracle_witnesses.json'))
    # Oracle inputs and expected outputs are literal historical witnesses.
    # Active source books now use the same unchanged vectors with amended lineage.
    put('reports/r17r1b/owner_oracle_witnesses_v1_1.json',witness)
    mapping['reports/r17c/owner_oracle_witnesses.json']=bind('reports/r17r1b/owner_oracle_witnesses_v1_1.json')
    mapping['reports/r17b/completion_gate.json']=bind('reports/r17r1a/completion_gate.json')
    for name in NAMES[1:]+NAMES[:1]:
        oldpath='config/v4_14_'+name+'_v1.json';newpath='config/v4_14_'+name+'_v1_1.json';assert not (ROOT/newpath).exists()
        obj=remap(read(oldpath));obj.update(version='1.1.0',supersedes=bind(oldpath),active_family_closure=bind(CLOSURE),accepted_v4_13_authority=bind(HEAD))
        enrich=bind('config/v4_13_rotation_structure_enrichment_schema_v1_2.json')
        if enrich not in obj['source_bindings']:obj['source_bindings'].append(enrich)
        if name=='temporal_non_edge_registry':
            obj['owner_dag']=next(r for r in h['contract_refs'] if 'dag_edge_registry' in r['path'])
            obj['owner_edges']=read(obj['owner_dag']['path'])['edges']
        put(newpath,obj);mapping[oldpath]=bind(newpath)
    put('reports/r17r1b/contract_freeze_manifest.json',dict(contracts=[bind('config/v4_14_'+n+'_v1_1.json') for n in NAMES],dimensions=17,vector_count=60,active_family_closure=bind(CLOSURE),V4_14_RUNTIME='NOT_IMPLEMENTED',ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED'))
if __name__=='__main__':prepare()
