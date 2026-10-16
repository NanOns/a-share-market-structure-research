"""Install exact checked-in source closure bytes in a disposable checkout."""
import json
from pathlib import Path
from workbench_analysis.operational_daily_exact_policy_v2 import PATH


def install_official_closure(root):
    root=Path(root).resolve()
    repository=Path(__file__).resolve().parents[1]
    if root == repository or repository in root.parents:
        raise ValueError('EXACT_POLICY_TEST_ROOT_MUST_BE_DISPOSABLE')
    policy_path=repository/PATH
    policy=json.loads(policy_path.read_bytes())
    closure=policy['accepted_algorithm_bindings']+policy['component_source_bindings']
    closure += [policy['task_contract'],policy['predecessor_policy']]
    for binding in closure:
        source=repository/binding['path']
        if not source.is_file():
            raise FileNotFoundError(f"EXACT_POLICY_SOURCE_MISSING:{binding['path']}")
        target=root/binding['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=source.read_bytes()
        if target.exists() and target.read_bytes()!=raw:
            raise ValueError(f"EXACT_POLICY_SOURCE_COLLISION:{binding['path']}")
        if not target.exists():target.write_bytes(raw)
    target_policy=root/PATH
    target_policy.parent.mkdir(parents=True,exist_ok=True)
    raw_policy=policy_path.read_bytes()
    if target_policy.exists() and target_policy.read_bytes()!=raw_policy:
        raise ValueError('EXACT_POLICY_TEST_POLICY_COLLISION')
    if not target_policy.exists():target_policy.write_bytes(raw_policy)
    return policy


def install_pending(root):
    """Legacy focused fixture: pending policy with a deliberately small closure."""
    import json
    from workbench_analysis.operational_daily_exact_policy_v2 import CONTRACT,KERNEL,REQUIRED_SOURCES
    from workbench_analysis.r43_owner_replay import ref
    root=Path(root).resolve()
    repository=Path(__file__).resolve().parents[1]
    sources=REQUIRED_SOURCES|{'config/read_only_operational_daily_release_policy_v1_1.json','docs/upgrade/V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md'}
    for name in sources:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes((repository/name).read_bytes())
    policy=dict(contract_id=CONTRACT,adjustment_contract=KERNEL,publication_ready=False,
        task_contract=ref(root,root/'docs/upgrade/V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md'),
        predecessor_policy=ref(root,root/'config/read_only_operational_daily_release_policy_v1_1.json'),
        accepted_algorithm_bindings=[ref(root,root/p) for p in sorted(REQUIRED_SOURCES)])
    (root/PATH).write_text(json.dumps(policy),encoding='utf8')
    return policy
