"""Real pending source contract for disposable mocked-kernel layer tests."""
import json
from pathlib import Path
from workbench_analysis.operational_daily_exact_policy_v2 import CONTRACT,KERNEL,PATH,REQUIRED_SOURCES
from workbench_analysis.r43_owner_replay import ref

def install_pending(root):
    root=Path(root).resolve()
    assert root.is_relative_to(Path('G:/codex_tmp/test_temp').resolve())
    repository=Path(__file__).resolve().parents[1]
    sources=REQUIRED_SOURCES|{'config/read_only_operational_daily_release_policy_v1_1.json','docs/upgrade/V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md'}
    for name in sources:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        # Existing focused-layer inputs are synthetic identity bindings and
        # remain intact. Pending admission never grants their publication.
        if not p.exists():p.write_bytes((repository/name).read_bytes())
    policy=dict(contract_id=CONTRACT,adjustment_contract=KERNEL,publication_ready=False,
        task_contract=ref(root,root/'docs/upgrade/V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md'),
        predecessor_policy=ref(root,root/'config/read_only_operational_daily_release_policy_v1_1.json'),
        accepted_algorithm_bindings=[ref(root,root/p) for p in sorted(REQUIRED_SOURCES)])
    (root/PATH).write_text(json.dumps(policy),encoding='utf8')
    return policy
