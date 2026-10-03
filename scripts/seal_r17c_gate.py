"""Seal contract-only evidence and the unified authorized R17 handoff."""
from pathlib import Path
import json,sys,subprocess,hashlib
from scripts.prepare_r17_governance import ROOT,put,atomic,bind
from scripts.validate_r17c_contract_freeze import validate
def seal(output):
    output=Path(output);clean=json.loads((output/'clean_detached.json').read_bytes());reg=json.loads((output/'regression_gate.json').read_bytes())
    assert clean['status']=='PASS' and clean['git_clean_before'] and clean['git_clean_after'] and reg['source_unchanged']
    assert reg['deselected_count']==0 and not reg['failures'] and not reg['errors'] and not reg['skipped']
    result=validate();assert result['V4_14_CONTRACT_COMPLETENESS']=='PASS_READY_FOR_EXTERNAL_AUDIT'
    for name in ['clean_detached.json','regression_gate.json','regression.xml','regression.log']:atomic('reports/r17c/clean/'+name,(output/name).read_bytes())
    put('reports/r17c/completion_gate.json',dict(result,tested_source=clean['source_sha'],test_totals=clean['test_totals'],clean_detached=bind('reports/r17c/clean/clean_detached.json'),contract_freeze=bind('reports/r17c/contract_freeze_manifest.json')))
    base='f12315bf8e3142aa44e9068c5895004c35c4e23c';changed=subprocess.check_output(['git','diff','--cached',base,'--name-only','src'],cwd=ROOT,text=True,encoding='utf8').splitlines()
    old_changed=[p for p in changed if subprocess.run(['git','cat-file','-e',base+':'+p],cwd=ROOT,capture_output=True).returncode==0]
    assert set(old_changed)=={'src/workbench_analysis/dm01_accepted_chain_v1.py','src/workbench_analysis/dm01_publication_history_reader_v1.py'}
    kept=[]
    frozen_paths=subprocess.check_output(['git','ls-tree','-r','--name-only',base,'config','src/workbench_analysis','src/v4'],cwd=ROOT,text=True,encoding='utf8').splitlines()
    for path in frozen_paths:
        if path.startswith('config/v4_13_') or path.startswith('src/workbench_analysis/v4_12_') or path.startswith('src/workbench_analysis/v4_13_') or path.startswith('src/v4/'):
            raw=subprocess.check_output(['git','show',base+':'+path],cwd=ROOT)
            assert (ROOT/path).read_bytes()==raw,path
            kept.append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),byte_identical=True))
    m=json.loads((ROOT/'reports/v4_13_runtime_r16/real/2026-09-30/r6/manifest.json').read_bytes())
    for r in m['runtime_source_refs']:assert bind(r['original_path'])['sha256']==r['sha256']
    assert not subprocess.check_output(['git','diff','--cached',base,'--name-only','reports/v4_13_runtime_r16','reports/v4_13_runtime_r16r1'],cwd=ROOT).strip()
    put('reports/r17c/KEEP_integrity.json',dict(status='PASS',baseline=base,kept=kept,r5_r6_and_r16r1_evidence_modified=False,algorithm_threshold_changes=False,only_existing_source_changes=old_changed,scope='GOVERNANCE_READER_MAINTENANCE_ONLY'))
    state=dict(R17A_CROSS_STAGE_GOVERNANCE_REPAIR='PASS',R17B_V4_13_ACCEPTED_HEAD_PROMOTION='PASS',V4_13_ACCEPTED_HEAD='CREATED_EXTERNALLY_AUTHORIZED_ENGINEERING_SCOPE',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_13_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',R17C_V4_14_CONTRACT_FREEZE_ENTRY='PASS_LOCAL',V4_14_CONTRACT_COMPLETENESS='PASS_READY_FOR_EXTERNAL_AUDIT',V4_14_RUNTIME='NOT_IMPLEMENTED',ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    put('reports/r17c/final_handoff.json',dict(final_state=state,baseline=base,tested_source=clean['source_sha'],stage_order=['R17A','R17B','R17C'],stage_gates=[bind('reports/'+s+'/completion_gate.json') for s in ['r17a','r17b','r17c']],heads={p:bind(p) for p in ['data/v4/V4_13_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json']},KEEP_integrity=bind('reports/r17c/KEEP_integrity.json'),production=False,shadow=False,focus=False,global_mandatory_adoption=False,test_totals=clean['test_totals'],runtime_replay_executed=False,source_checkpoint_kind='CLEAN_DETACHED_VALIDATION_SNAPSHOT; BRANCH_AND_REMOTE_ADVANCE_ONLY_AFTER_ALL_STAGES_COMPLETE'))
    print(json.dumps(state))
if __name__=='__main__':seal(sys.argv[1])
