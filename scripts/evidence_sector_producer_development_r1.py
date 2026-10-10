"""Bounded B source archaeology and exact golden extraction evidence."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from sector.producer_entry_r1 import read_bound
from sector.legacy_producer_candidate_r1 import extract_legacy_candidate
from v4.a02_a05_external_acceptance_r1 import accepted_legacy_observations, validate_a05_record

OUT = ROOT / 'docs/evidence/v4_r4_post_audit_repair_20261010/12_BCD_DEVELOPMENT/03_B'


def binding(path):
    raw = (ROOT / path).read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(value if isinstance(value, str) else
                    json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temp, path)


def main():
    head_binding = binding('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    head = json.loads(read_bound(ROOT, head_binding))
    target = head['accepted_trade_date']
    record, _ = validate_a05_record(ROOT)
    try:
        accepted_legacy_observations(ROOT, target=target)
    except ValueError as error:
        current_rejection = str(error)
    else:
        raise AssertionError('UNEXPECTED_CURRENT_LEGACY_ACCEPTANCE')
    amendment_path = 'reports/audits/next_round_r2/V4_08_ACCEPTED_HEAD_B2_CAPABILITY_AMENDMENT_CANDIDATE_R2.json'
    amendment = json.loads((ROOT / amendment_path).read_bytes())
    original = amendment['current_snapshot_replay']
    rows = [json.loads(line) for line in read_bound(ROOT, original).splitlines()]
    ast_binding = binding('config/v4_08_b2_machine_ast_r5.json')
    ast = json.loads(read_bound(ROOT, ast_binding))
    sources = dict(source=binding(ast['source_path']),
        source_parameters=binding(ast['source_parameter_path']),
        parameters=binding('config/v4_08_algorithm_parameter_set_r5.json'))
    samples = []
    for expected in ('TRUE', 'FALSE', 'UNKNOWN'):
        row = next(r for r in rows if r['new']['confirmed_raw'] == expected)
        extracted = extract_legacy_candidate(ROOT, input_owner=original,
            sector_id=row['sector_id'], ast_binding=ast_binding, source_bindings=sources)
        assert extracted['CONFIRMED']['candidate_value'] == expected
        assert extracted['WARM']['candidate_value'] == row['new']['warm_diagnostic']
        samples.append(dict(expected=expected, actual=extracted['CONFIRMED']['candidate_value'],
            oracle=row['new'], extracted=extracted, pass_result=True))
    write('B_EXACT_LEGACY_SOURCE_GOLDEN_EXTRACTIONS.json', dict(
        status='PASS_SCOPED_EXACT_EXTRACTION', rechecked_sectors=3,
        full_541_replay_repeated=False, real_golden_date=record['accepted_snapshot_trade_date'],
        current_T0=target, original_golden_binding=original,
        original_receipt_binding=binding(amendment_path), samples=samples,
        production_authorized=False, formal_current_owner_recovered=False))
    write('B_CURRENT_SOURCE_AND_ENGINEERING_BOUNDARIES.json', dict(
        contract_id='B_SOURCE_BOUND_ENTRY_DEVELOPMENT_R1', T0=target,
        operational_head_binding=head_binding,
        current_native_owner=head['owners'][target]['sector'],
        current_core_owner=head['owners'][target]['core'],
        existing_AST_implemented=True, existing_real_golden_samples=True,
        old_v1_not_implemented_label_superseded_by_existing_R5_engineering=True,
        current_legacy_valid_member_rejection=current_rejection,
        accepted_legacy_observation_date=record['accepted_snapshot_trade_date'],
        accepted_legacy_observation_binding=record['real_observations'],
        implemented_this_round=['SHA-bound six-field Producer entry',
            'source Owner entity/member/as-recorded/cutoff validation',
            'exact original prior Owner and immutable creation contract checks',
            'actual operational Native command entry',
            'executable exact-source CONFIRMED and WARM diagnostic extraction'],
        blocked_production_fields={
            'CONFIRMED': 'No independently admitted 2026-10-09 exact legacy valid-member publication. 09/24 acceptance refuses other dates; current Native/Core corrected does not establish an admitted legacy observation.',
            'WARM': 'Exact legacy q20/dq5_3 rank snapshots and SETUP/RECOVERY publications unavailable; Amount A-dependent paths require separate strict H21 acceptance. AST branches remain independently diagnostic.',
            'frozen_invalidation': 'No admitted exact prior SECTOR Episode and creation-frozen invalidation Owner.',
            'episode_invalidation_contract_id': 'No original admitted prior SECTOR creation contract ID/version/SHA Owner.',
            'followup_complete': 'No admitted original SECTOR due_plan and matured settlement Owner; future data cannot supply them.',
            'scenario': 'No accepted SECTOR confirmation/scenario publication with original priority and first availability.'},
        immutable_formal_contracts=[binding('config/v4_10_research_state_contract_r1_2.json'),
            binding('config/v4_08_b2_machine_ast_r5.json')],
        formal_admission=False, external_gate='EXTERNAL_RECHECK_REQUESTED'))
    write('B_TEST_AND_PROTECTED_HEAD_RECEIPT.json', dict(
        BASE_SHA=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                        text=True).strip(),
        test_files=['tests/test_sector_producer_entry_r1.py'],
        test_command='E:/python/python.exe -B -m pytest tests/test_sector_producer_entry_r1.py -q -o cache_dir=G:/codex_tmp/b_producer_pytest_cache --basetemp=G:/codex_tmp/test_temp/b_producer_entry4',
        test_result={'passed': 30, 'exit_code': 0},
        real_native_entry='B_REAL_NATIVE_SOURCE_ENTRY_R2.json',
        real_native_idempotent_replay_exit_code=0,
        exact_legacy_real_goldens={'checked': 3, 'mismatches': 0, 'exit_code': 0},
        protected_operational_head_before=head_binding,
        protected_operational_head_after=binding(head_binding['path']),
        protected_strict_head=binding('data/v4/V4_DATA_ACCEPTED_HEAD.json'),
        code_bindings=[binding(p) for p in (
            'src/sector/producer_entry_r1.py',
            'src/sector/legacy_producer_candidate_r1.py',
            'scripts/prepare_sector_producer_entry_r1.py',
            'scripts/evidence_sector_producer_development_r1.py',
            'tests/test_sector_producer_entry_r1.py')],
        production_promotion=False, frozen_contracts_modified=False))
    write('B_DEVELOPMENT_RESULT.md', '# B 开发推进结果\n\n'
        '实际新增六字段 SHA 绑定 Producer Entry、真实 Native 命令入口、精确 legacy Producer 候选提取。完整六字段隔离正向链和负例测试通过，正式消费者仍关闭。真实10/09 Native 原字节已进入新入口；当前六源缺失精确返回 null，已有 dq5 保留。\n\n'
        '旧 V1 合同中的 AST 未实现文字不能代表当前工程：R5 AST、exact legacy 源码及9/24真实黄金样本已经存在。本轮复用原件，重新提取 TRUE/FALSE/UNKNOWN 各一个黄金样本，3项独立预期全部匹配，未重跑541或400全量。CONFIRMED/WARM 的纯Core分支均可运行并独立解释。\n\n'
        '继续正式10/09需要新合法原件及独立准入：A05 accepted_legacy_observations 明确只允许9/24，实际10/09调用返回 A05_CURRENT_SNAPSHOT_TARGET_NOT_ACCEPTED。REV2 §17 要求 warm_raw/confirmed_raw 来自§34已提取验收 legacy；冻结 research_state.reduce_state 的 ACCEPTED_FACT_INTERFACE 分支拒绝正向 CONFIRMED/WARM（UNACCEPTED_D0_D1_DETECTOR）。不能把9/24现有授权改日期、把10/09 corrected 字段改成 as-recorded，或改冻结合同开放权限。\n\n'
        'WARM 真源还缺 q20/dq5_3 原排名快照、SETUP/RECOVERY，金额分支独立缺 H21；其余四项缺原始 SECTOR Episode、冻结失效合同、到期结算 Owner 和 scenario Producer。候选 source→extraction→candidate 接线完成；正式源恢复和 SECTOR_D2_FORMAL_OWNER_PASS 没有达成。\n')
    assert binding(head_binding['path']) == head_binding
    print(json.dumps(dict(status='PASS_SCOPED_ENGINEERING', golden_samples=3,
        current_formal_recovery=0, current_rejection=current_rejection)))


if __name__ == '__main__':
    main()
