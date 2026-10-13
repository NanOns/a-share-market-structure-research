"""Version current execution sources for R1.1 QA; never grants publication.

Historical policy archives and their admission evidence stay untouched.
Only a subsequent independently checked G1/G2/G3/G4 receipt can admit runtime.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--stage-only',action='store_true');a=p.parse_args()
    root=Path(a.root).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp').resolve()) and not (a.stage_only and root==Path('G:/codex work/v4-production-20261012').resolve()):raise ValueError('ISOLATED_CANDIDATE_ROOT_REQUIRED')
    from workbench_analysis.r43_owner_replay import checked,ref
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_analysis.operational_daily_exact_policy_v2 import PATH,REQUIRED_SOURCES,immutable_policy_binding
    parent=json.loads((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    old=json.loads(checked(root,parent['release_policy']).read_bytes())
    additions={
        'src/workbench_analysis/operational_increment_plan_v1.py',
        'src/workbench_analysis/operational_revision_guard_r1.py',
        'src/workbench_analysis/operational_runtime_acceptance_r1_1.py',
        'src/workbench_analysis/operational_market_context_correction_r1.py',
        'src/workbench_analysis/operational_sealed_resume_r1.py',
        'src/workbench_analysis/r43_daily_price_limits.py',
        'src/workbench_analysis/operational_new_listing_r1.py',
        'src/workbench_analysis/tdx_sector_retro_r43.py',
        'src/workbench_db/v4_read_index_r1.py',
        'src/workbench_db/v4_native.py',
        'src/workbench_desktop/source_adapter.py',
        'src/workbench_desktop/storage.py',
        'src/workbench_desktop/jobs.py',
        'config/v4_operational_new_listing_r1.json',
    }
    logical=set(REQUIRED_SOURCES)|additions|{b.get('module_path',b['path']) for b in old['accepted_algorithm_bindings']}
    def archive(name):
        path=ROOT/name
        raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        target=root/'data/v4/runtime_repair_sources_r1_1'/sha/name
        if target.exists() and target.read_bytes()!=raw:raise ValueError('IMMUTABLE_SOURCE_CONFLICT')
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix(target.suffix+'.tmp')
            temporary.write_bytes(raw);os.replace(temporary,target)
        return dict(ref(root,target),module_path=name)
    bindings=[archive(name) for name in sorted(logical)]
    components=[archive(b['module_path']) for b in old['component_source_bindings']]
    task=ROOT/'docs/upgrade/V4_INCREMENT_IDENTITY_PARITY_AMENDMENT_R1_1_20261013.md'
    target=root/task.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.tmp');temporary.write_bytes(task.read_bytes());os.replace(temporary,target)
    document=dict(old,accepted_algorithm_bindings=bindings,component_source_bindings=components,
                  task_contract=ref(root,target),publication_ready=False,status='R1_1_CANDIDATE_GATES_PENDING',
                  runtime_repair_contract='V4_RUNTIME_REPAIR_ACCEPTANCE_R1_1',
                  predecessor_runtime_policy=parent['release_policy'])
    document.pop('admission_evidence',None)
    if a.stage_only:
        raw=json.dumps(document,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        path=root/'data/v4/exact_daily_policies_v2'/hashlib.sha256(raw).hexdigest()/'POLICY.json'
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);os.replace(temporary,path)
        binding=ref(root,path)
    else:
        atomic_json(root,root/PATH,document)
        binding=immutable_policy_binding(root)
    atomic_json(root,root/'runtime/r1_1/CANDIDATE_POLICY_RECEIPT.json',dict(
        contract_id='V4_RUNTIME_REPAIR_CANDIDATE_POLICY_R1_1',policy=binding,
        accepted_algorithm_bindings=bindings,component_source_bindings=components,
        publication_ready=False,parent_head=ref(root,root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')))
    print(json.dumps(dict(status=document['status'],sources=len(bindings),components=len(components),policy=binding)))

if __name__=='__main__':main()
