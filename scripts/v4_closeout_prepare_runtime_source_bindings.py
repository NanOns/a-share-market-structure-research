"""Archive both exact source versions; original formal Head and source stay put."""
import hashlib,json,sys
from pathlib import Path
import shutil
SOURCE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
FORMAL=Path('G:/codex work/v4-production-20261012')
TASK=Path('D:/Users/lps/Desktop/阶段任务/V4_85E9A881E799BFE58D_AEE6B4AAE6B6_8EE68394E4A788E6A2_B8E6A189E88C80E4BB8A.md')
def main():
    from workbench_desktop.closeout_runtime_sources_r1 import CONTRACT,AUTHORITY,REPAIRS,admitted
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_service.current_v4_context import canonical
    policy=json.loads((SOURCE/'config/read_only_operational_daily_release_policy_v1_1.json').read_bytes())
    accepted={r['path']:r for r in policy['accepted_algorithm_bindings']}
    before={name:(FORMAL/'data/v4'/name).read_bytes() for name in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    base=Path('data/v4/closeout_runtime_sources_r1')
    repairs=[]
    def materialize(relative,raw):
        for root in (SOURCE,FORMAL):
            path=root/relative
            if path.exists() and path.read_bytes()!=raw:raise ValueError('PRESERVE_IMMUTABLE_SOURCE_ARCHIVE')
            if not path.exists():atomic_bytes(path,raw)
        return dict(path=relative.as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    for name in sorted(REPAIRS):
        original=(FORMAL/name).read_bytes();current=(SOURCE/name).read_bytes()
        if hashlib.sha256(original).hexdigest()!=accepted[name]['sha256'] or len(original)!=accepted[name]['bytes']:raise ValueError('EXACT_ORIGINAL_ACCEPTED_SOURCE_REQUIRED')
        repairs.append(dict(module_path=name,upstream=materialize(base/'upstream'/name,original),runtime=materialize(base/'runtime'/name,current)))
    document=dict(contract_id=CONTRACT,scope='BOUNDED_NATIVE_PG_ADAPTER_AND_CORRECTED_FOCUS_ONLY',
        production_acceptance=False,general_algorithm_upgrade_permission=False,historical_PIT_permission=False,automated_trading_permission=False,
        task_card=materialize(base/'FULL_TASK_CARD.md',TASK.read_bytes()),
        user_scope_amendment=materialize(base/'USER_SCOPE_AMENDMENT.md',(SOURCE/'docs/audits/v4_full_closeout_20261012/USER_CUTOVER_SCOPE_AMENDMENT_20261012.md').read_bytes()),
        repairs=repairs,meaning='Upstream accepted algorithm bytes remain archived unchanged; compiled runtime repairs have separate exact source versions. Full functional release acceptance remains required.')
    for root in (SOURCE,FORMAL):
        path=root/AUTHORITY
        if path.exists() and path.read_bytes()!=canonical(document):raise ValueError('PRESERVE_EXISTING_RUNTIME_SOURCE_AUTHORITY')
        if not path.exists():atomic_bytes(path,canonical(document))
        if set(admitted(root))!=REPAIRS:raise ValueError('RUNTIME_SOURCE_ADMISSION_NOT_COMPLETE')
    for name,raw in before.items():
        if (FORMAL/'data/v4'/name).read_bytes()!=raw:raise ValueError('ACCEPTED_HEAD_CHANGED')
    print(json.dumps(dict(status='VERSIONED_SOURCE_BYTES_STAGED_ONLY',repairs=len(repairs),head_changed=False,production_acceptance=False)))
if __name__=='__main__':main()
