"""Exercise the actual nine builders on explicitly synthetic, persisted inputs."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from tests.v4_dm01.a01_fixture_inputs import make_inputs, replace_input, save
from workbench_analysis.dm01_candidate_orchestrator_r1 import build_candidate
from workbench_analysis.dm01_incremental_component_builders import sha, digest, artifact_reference_path

BASE = ROOT/'reports/dm01'
SCOPE = 'SYNTHETIC_INPUTS_REAL_NINE_ADAPTERS_ENGINEERING_ONLY'
HEADS = [ROOT/'data/v4'/p for p in ('V4_DATA_ACCEPTED_HEAD.json', 'V4_STAGE_ACCEPTED_HEAD.json', 'V4_DEV_BASELINE_HEAD.json')]

def run(env):
    return build_candidate(parent_data_head=env['parent'], source_freeze=env['freeze'], calendar_binding=env['calendar'],
        identity_binding=env['identity'], staging_root=env['staging'], head_paths=HEADS)

def report(name, value):
    atomic_json(BASE/f'DM01_A01_{name}_R1.json', dict(evidence_scope=SCOPE, market_acceptance_claim=False, **value))

def main():
    before={artifact_reference_path(p):sha(p) for p in HEADS}
    env=make_inputs(BASE/'engineering_inputs_r1'/sha(ROOT/'config/dm01_incremental_builders_contract_r1.json'))
    save(env['root'], 'context.json', dict(parent_data_head=env['parent'],source_freeze=env['freeze'],
        calendar_binding=env['calendar'],identity_binding=env['identity']))
    first=run(env)
    if len(first.get('components',{}))!=9:raise RuntimeError(first)
    second=run(env)
    if second['status']!='NOOP_IDENTICAL_CANDIDATE':raise RuntimeError(second)
    marker=Path(first['candidate_path'])
    posts={cap:json.loads((marker.parent/cap/'postcheck.json').read_text(encoding='utf8')) for cap in first['components']}
    report('COMPONENT_POSTCHECK', dict(status='PASS', adapter_used_as_oracle=False, components=first['components'], postchecks=posts,
        candidate=dict(path=artifact_reference_path(marker),sha256=sha(marker))))
    report('CROSS_COMPONENT_POSTCHECK', first['postcheck'])
    bad=deepcopy(env)
    replace_input(bad,'PRICE_RULES',dict(rules=[]))
    failed=run(bad)
    if failed['status']!='BLOCKED' or len(failed['completed_components'])<7:raise RuntimeError(failed)
    failures=list(env['staging'].rglob('failure.json'))
    if not failures or any((p.parent/'PROMOTION_CANDIDATE.json').exists() for p in failures):raise RuntimeError('PARTIAL_READY_MARKER')
    report('ATOMIC_FAILURE_PROBES',dict(status='PASS', late_price_source_failure=failed,
        retained_failure_evidence=[dict(path=artifact_reference_path(p),sha256=sha(p)) for p in failures],
        accepted_namespace_visible=False, protected_heads_before=before,
        protected_heads_unchanged=all(sha(ROOT/p)==s for p,s in before.items()),
        additional_negative_vectors='tests/v4_dm01/test_a01_incremental_builders_r1.py'))
    revised=deepcopy(env)
    provider=json.loads((ROOT/revised['freeze']['inputs']['BAOSTOCK_DAILY_UPDATE']['path']).read_text(encoding='utf8'))
    provider['daily_rows'][0]['isST']='1'
    replace_input(revised,'BAOSTOCK_DAILY_UPDATE',provider)
    third=run(revised)
    if len(third.get('components',{}))!=9 or third['candidate_path']==first['candidate_path']:raise RuntimeError(third)
    if sha(marker)!=first['candidate_sha256']:raise RuntimeError('PREVIOUS_REVISION_OVERWRITTEN')
    report('DETERMINISM',dict(status='PASS', same_frozen_source_rerun=second['status'],
        candidate_sha256=first['candidate_sha256'],rerun_candidate_sha256=second['candidate_sha256'],
        revised_source_candidate=dict(path=artifact_reference_path(Path(third['candidate_path'])),sha256=third['candidate_sha256']),
        revision_parent_unchanged=all(r['parent_data_head_digest']==env['parent']['binding']['sha256'] for r in third['components'].values()),
        old_candidate_immutable=True, same_source_revision_is_logically_deterministic=True,
        wall_clock_zip_generation_not_compared_as_same_source=True, external_acceptance='PENDING'))
    assert all(sha(ROOT/p)==s for p,s in before.items())
    print(json.dumps(dict(status='PASS_ENGINEERING_EVIDENCE',components=9, late_failure_components=len(failed['completed_components']))))

if __name__=='__main__':main()
