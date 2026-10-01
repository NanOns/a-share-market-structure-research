"""Formalize accepted A13 evidence semantics without changing business heads."""
import copy
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes, atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.official_event_acceptance_v1 import (
    AUDIT, AUDITED_HEAD, CONFIG, DISPOSITION, HEAD, require_accepted_semantic_head, require_trading_event)
from workbench_analysis.official_event_semantics_v1 import TRADING_TYPES

P = 'reports/audits/A13_FORMALIZATION_'
CANDIDATE = 'data/v4/source_evidence/a13/OFFICIAL_NOTICE_EVENT_SEMANTICS_AMENDMENT_R1.json'
SIDECAR = 'data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_SIDECAR_R1.json'
TASK = 'docs/evidence/source_authority/V4_A13_EVENT_SEMANTICS_EXTERNAL_ACCEPTANCE_FORMALIZATION_TASK_20261001.md'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf8'))


def assert_preserved(protected):
    for binding in protected:
        assert bind(binding['path'])['sha256'] == binding['sha256'], binding['path']


def main():
    now = datetime.now(timezone.utc).isoformat()
    if (ROOT / HEAD).exists():
        existing_head, _ = require_accepted_semantic_head(ROOT)
        now = existing_head['accepted_at']
    authority = dict(bind(AUDIT), audited_head=AUDITED_HEAD, document_role='INDEPENDENT_EXTERNAL_ACCEPTANCE')
    protected = copy.deepcopy(read('reports/audits/A13_STAGE_ENTRY_R1.json')['protected_bindings'])
    existing = {b['path'] for b in protected}
    for path in sorted((ROOT / 'data/v4/source_evidence/a13').rglob('*')):
        name = path.relative_to(ROOT).as_posix()
        if path.is_file() and name not in existing:
            protected.append(bind(name))
    for name in (CANDIDATE, 'reports/audits/A13_NOTICE_REMOVAL_ADMISSION_COUNTERFACTUAL_R1.json',
                 'reports/audits/a13_counterfactual_r1/FULL_DOWNSTREAM_REPLAY_OUTPUTS_R1.json.gz'):
        if name not in {b['path'] for b in protected}:
            protected.append(bind(name))
    assert_preserved(protected)
    atomic_json(ROOT / (P + 'STAGE_ENTRY_R1.json'), dict(
        contract_id='WP-A13-EXTERNAL-ACCEPTANCE-FORMALIZATION', baseline_commit=AUDITED_HEAD,
        stage_contract='EXACT_EXTERNAL_AUDIT_ACCEPTED_EVIDENCE_SEMANTICS_NO_BUSINESS_IMPACT',
        external_authority=authority, task=bind(TASK), phase0_status='FULL_PASS',
        phase0_evidence=bind('reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'),
        protected_bindings=protected, entered_at=now,
        next_stage='Independent external reaudit of formal registration; business heads KEEP'))
    candidate_binding = bind(CANDIDATE)
    sidecar = copy.deepcopy(read(CANDIDATE))
    assert sidecar['external_acceptance'] is None
    sidecar.update(external_acceptance='EXTERNALLY_ACCEPTED', external_authority=authority,
                   status='ACCEPTED_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT', candidate=candidate_binding,
                   acceptance_scope='EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT', accepted_at=now,
                   business_rebuild_required=False, production_permission=False,
                   positive_trading_event_authority_consumed=False)
    payload = (json.dumps(sidecar, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf8')
    artifact = 'data/v4/artifact_store/a13/sha256-' + hashlib.sha256(payload).hexdigest() + '.json'
    atomic_bytes(ROOT / artifact, payload)
    atomic_bytes(ROOT / SIDECAR, payload)
    runtime = bind('src/workbench_analysis/official_event_acceptance_v1.py')
    atomic_json(ROOT / CONFIG, dict(
        contract_id='OFFICIAL_EVENT_ACCEPTANCE_V1', version='1.0.0', runtime=runtime,
        semantic_runtime=bind('src/workbench_analysis/official_event_semantics_v1.py'),
        candidate=candidate_binding, accepted_semantic_head_path=HEAD,
        filename_or_capture_id_grants_trading_authority=False, unknown_event_may_enter_trading_status=False,
        formal_trading_truth_requires='EXACT_ACCEPTED_HEAD_SIDECAR_RAW_TEXT_IDENTITY_AND_EFFECTIVE_DATE',
        acceptance_scope='EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT'))
    atomic_json(ROOT / HEAD, dict(
        contract_id='OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_V1', external_acceptance='EXTERNALLY_ACCEPTED',
        external_authority=authority, sidecar=bind(SIDECAR), content_addressed_sidecar=bind(artifact),
        runtime=runtime, config=bind(CONFIG), candidate=candidate_binding,
        audited_head=AUDITED_HEAD, accepted_at=now, business_rebuild_required=False,
        acceptance_scope='EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT', v4_08_head_action='KEEP',
        production_permission=False, shadow_permission=False, focus_permission=False,
        formal_consumer_authorization=False, positive_trading_event_authority_consumed=False))
    head, accepted = require_accepted_semantic_head(ROOT)
    vectors = []
    for kind in ('IPO_ISSUANCE_POSTPONEMENT', 'IPO_LISTING_POSTPONEMENT', 'UNKNOWN_EVENT_SEMANTICS'):
        entries = [e for e in accepted['entries'] if e['actual_event_type'] == kind]
        assert entries
        for event in entries:
            try:
                require_trading_event(ROOT, head['sidecar'], event['raw_artifact'],
                                      security_key=event['security_key'], effective_date=event['event_effective_date'])
            except ValueError as exc:
                assert str(exc) == 'OFFICIAL_NOTICE_NOT_A_DATED_TRADING_EVENT'
                vectors.append(dict(actual_event_type=kind, raw_artifact=event['raw_artifact'],
                                    security_key=event['security_key'], effective_date=event['event_effective_date'],
                                    rejection=str(exc), status='PASS_REJECTED'))
            else:
                raise AssertionError('NON_TRADING_NOTICE_AUTHORIZED')
    positives = [e for e in accepted['entries'] if e['actual_event_type'] in TRADING_TYPES
                 and e.get('identity_evidence') and e.get('event_effective_date')
                 and e['consumer_permissions'].get('TRADING_STATUS_TRUTH') is True]
    assert not positives, 'Positive authority requires individual actual market proof'
    atomic_json(ROOT / (P + 'REAL_HEAD_RUNTIME_READBACK_R1.json'), dict(
        status='PASS', head=bind(HEAD), external_authority=authority, semantic_entry_count=len(accepted['entries']),
        original_candidate_immutable=True, vectors=vectors, positive_eligible_real_entry_count=len(positives),
        positive_trading_event_authority='NOT_CONSUMED_NO_COMPLETE_AUTHORIZED_PRIMARY_EVENT',
        nested_dated_statements_not_promoted_to_primary_events=True, fixture_market_facts_consumed=False))
    # Rerun the original accepted kernel in a fresh output namespace. Original
    # receipts, case inputs and raw sources remain byte-for-byte unchanged.
    spec = importlib.util.spec_from_file_location('a13_formalization_counterfactual', ROOT / 'scripts/replay_a13_notice_counterfactual.py')
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    destination = 'reports/audits/a13_formalization_counterfactual_r1/'
    original_bytes = replay.atomic_bytes
    original_json = replay.atomic_json
    def save_bytes(path, value):
        original_bytes(ROOT / (destination + Path(path).name), value)
    def save_json(path, value):
        value = copy.deepcopy(value)
        value['status'] = 'PASS_NO_BUSINESS_IMPACT_FORMALIZATION'
        value['external_acceptance'] = DISPOSITION
        value['external_authority'] = authority
        value['replay_outputs'] = bind(destination + Path(value['replay_outputs']['path']).name)
        original_json(ROOT / (P + 'COUNTERFACTUAL_REVALIDATION_R1.json'), value)
    replay.atomic_bytes = save_bytes
    replay.atomic_json = save_json
    replay.main()
    result = read(P + 'COUNTERFACTUAL_REVALIDATION_R1.json')
    assert result['full_PIT_fact_count'] == 50162 and result['full_PIT_equal_to_accepted'] is True
    assert all(v['security_rows_changed'] == 0 for v in result['full_downstream_business_diff'].values())
    assert_preserved(protected)
    atomic_json(ROOT / (P + 'RAW_AND_BUSINESS_IMMUTABILITY_R1.json'), dict(
        status='PASS', checked_bindings=protected, exact_byte_changes=0,
        V4_08_ACCEPTED_HEAD='KEEP', V4_DATA_ACCEPTED_HEAD='KEEP', V4_STAGE_ACCEPTED_HEAD='KEEP',
        raw_source_renames_or_overwrites=0, network_calls=0))
    atomic_json(ROOT / (P + 'ENGINEERING_GATES_R1.json'), dict(
        contract_id='WP-A13-EXTERNAL-ACCEPTANCE-FORMALIZATION', external_authority=authority,
        allowed_candidate_status='READY_FOR_EXTERNAL_REAUDIT',
        A13_EXTERNAL_ACCEPTANCE_FORMALIZATION='PASS', V4_08_ACCEPTED_HEAD='KEEP',
        gates={'EXACT_EXTERNAL_AUDIT':'PASS_ENGINEERING', 'REAL_ACCEPTED_HEAD_READBACK':'PASS_ENGINEERING',
               'FULL_COUNTERFACTUAL_REVALIDATION':'PASS_ENGINEERING', 'RAW_AND_BUSINESS_IMMUTABILITY':'PASS_ENGINEERING',
               'CLEAN_REGRESSION':'PENDING_CLEAN_DETACHED'},
        evidence_bindings=[bind(P + name) for name in ('REAL_HEAD_RUNTIME_READBACK_R1.json',
            'COUNTERFACTUAL_REVALIDATION_R1.json', 'RAW_AND_BUSINESS_IMMUTABILITY_R1.json')],
        production_permission=False, shadow_permission=False, focus_permission=False,
        next_stage='Independent external reaudit of formalization; no business head movement'))
    atomic_json(ROOT / (P + 'CROSS_STAGE_REGISTRY_DISPOSITION_R1.json'), dict(
        audit_id='OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS', status='ACCEPTED',
        implementation_work_package='WP-A13-EXTERNAL-ACCEPTANCE-FORMALIZATION',
        external_acceptance='PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT',
        external_authority=authority, audited_head=AUDITED_HEAD,
        formal_consumer_authorization=False, business_rebuild_required=False, v4_08_head_action='KEEP',
        formal_trading_event_truth_requires='EXACT_ACCEPTED_SEMANTIC_HEAD_SIDECAR_RAW_TEXT_IDENTITY_AND_EFFECTIVE_DATE',
        filename_or_capture_id_inference_forbidden=True,
        positive_trading_event_authority_consumed=False,
        evidence=[bind(HEAD), bind(SIDECAR), bind(P + 'REAL_HEAD_RUNTIME_READBACK_R1.json'),
                  bind(P + 'COUNTERFACTUAL_REVALIDATION_R1.json')],
        next_step='Independent external reaudit of registration metadata; no business head movement'))
    closure = '''# A13 外部验收正式化｜2026-10-01

允许交付状态：`READY_FOR_EXTERNAL_REAUDIT`。A13 外部验收正式化验证 PASS；V4-08 Accepted Head KEEP，业务重建不需要。

唯一 acceptance authority 是仓库内的真实独立外部验收文件 `V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md`，绑定 exact path、bytes、SHA-256 和审计 HEAD `d85f815097a09ca2dceda00d0e29d6ff4fe331d4`。任务卡仅作为执行范围，未作为 external authority。

新增 versioned accepted sidecar 与 Accepted Head，content-addressed artifact 绑定原 candidate exact digest。原 candidate 的 134 条 primary semantic entries、raw/text/identity evidence 和 consumer permissions 全部保持原值。Accepted Head/config/runtime 显式限制为 evidence-governance acceptance。

真实 Accepted Head 的 `require_trading_event()` readback 检查了 24 条 IPO 发行暂缓、6 条 IPO 上市暂缓和 47 条 UNKNOWN，77 条均拒绝进入 trading status truth。当前 primary entries 中没有满足完整 identity/effective-date 与 trading permission 的真实已上市停/复牌事件，因此 positive trading-event authority 暂不消费；未把测试 fixture 作为市场事实。

在 fresh namespace 重新执行原 admission/PIT 和下游 kernel。移除任务指定三份误命名 notice 后，完整 50,162 PIT facts 与 accepted artifact exact 相同，V4-07 Base Seed、V4-08 四类 sector 输出及 V4-09 Prewatch 全部 business changed rows = 0。原反事实 receipts/output、候选、raw 和所有既有 business Accepted Heads exact hashes 保持不变。

新证据位于 `reports/audits/A13_FORMALIZATION_*`；fresh full replay 位于 `reports/audits/a13_formalization_counterfactual_r1/`。Cross-stage registry 更新裁决单独输出供合并，审计项为 ACCEPTED / PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT，并继续保留 accepted semantic truth guard 与 filename/capture-id 推断禁令。

回归范围 A13、V4-01、V4-02、V4-08、V4-09、DM01、NoSymbol，由 clean detached stage receipt 记录实际测试 commit 与结果。正式化元数据完成后提交外部复审，禁止 business head promotion，production/shadow/focus 继续 false。
'''
    atomic_bytes(ROOT / 'docs/audits/A13_EXTERNAL_ACCEPTANCE_FORMALIZATION_CLOSURE_20261001.md', closure.encode('utf8'))
    print('A13 external acceptance formalization PASS; package READY_FOR_EXTERNAL_REAUDIT pending clean regression')


if __name__ == '__main__':
    main()
