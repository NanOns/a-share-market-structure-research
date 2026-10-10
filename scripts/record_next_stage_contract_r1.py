"""Seal this task's authority and one capability ledger; no new market capture."""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from workbench_analysis.v4_14_replay_io import publish, ref

OUT = 'docs/evidence/next_stage_after_audit_r1_20261010'
BASE = 'c0b9903fe596c1884c04f5529d6699034548850e'


def text(path, value):
    p = ROOT/path
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else value.encode('utf-8')
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.next-stage-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(tmp, p)
        except FileExistsError:
            if p.read_bytes() != raw:
                raise ValueError('NO_CLOBBER_EVIDENCE')
    finally:
        os.unlink(tmp)
    return ref(ROOT, path)


def main():
    for name in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[name] = 'G:/codex_tmp'
    sources = []
    for name in ('V4_NEXT_STAGE_EXECUTION_MASTER_AFTER_OVERALL_AUDIT_R1_20261010.md',
                 'V4_OVERALL_PROGRESS_INDEPENDENT_AUDIT_R1_20261010.md'):
        original = Path('D:/Users/lps/Desktop/阶段任务')/name
        sources.append(text(OUT+'/task_sources/'+name, original.read_bytes()))
    phase = 'reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json'
    final = 'docs/evidence/pre_next_t0_execution_r1_20261010/final/'
    contract = 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
    publish(ROOT, OUT+'/STAGE_CONTRACT.json', dict(contract_id='NEXT_STAGE_AFTER_OVERALL_AUDIT_R1',
        exact_BASE=BASE, card_BASE_to_latest_remote_diff=[], sources=sources,
        upgrade_contract=ref(ROOT, contract), applicable_sections=['78','80','81','90'],
        phase0=ref(ROOT, phase), phase0_status=json.loads((ROOT/phase).read_bytes())['phase0_status'],
        prior_authoritative_final=ref(ROOT, final+'STATE_PUBLISHER_ISOLATED_RUN.json'),
        scope=['A_ENGINEERING','B_ISOLATED_PREFLIGHT','C_FUTURE_EPISODE_ENGINEERING','D_READ_ONLY_QA','E_ONE_PAGE_HOLD'],
        production_restart_authorized=False, write_grant_authorized=False, TDX_write_authorized=False,
        clocks='Actual timestamps only; next real session 2026-10-12 remains PENDING',
        acceptance='Per-scope engineering evidence; no external acceptance issued',
        next_stage='Independent scope review and real next T0 source capture; production load separately authorized'))
    specs = [
        ('OPERATIONS_CURRENT','DailyJobs / dated operational Owner','data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',
         'src/workbench_analysis/operational_daily_executor_v1.py','PASS_SCOPED_DATED_RESEARCH','new source/identity same-day review pending','Read-only operation; B preflight; real 10/12 capture',True),
        ('STATE_PUBLISHER_RESEARCH','FULL_MARKET_STATE_PUBLISHER_V1',final+'STATE_PUBLISHER_ISOLATED_RUN.json',
         'src/workbench_analysis/full_market_state_publisher_v1.py','PASS_SCOPED_RECONSTRUCTED_RESEARCH_ONLY','eligible_at_T0=false; missing legal clocks/event/benchmark','A candidate bridge; preserve research gzip',False),
        ('STATE_SOURCE_PIT','Independently admitted State Source Owner',final+'STATE_PUBLISHER_ISOLATED_RUN.json',
         'src/workbench_analysis/full_state_first_observed_v1.py','NOT_ADMITTED','PIT source, membership/model clocks and source review absent','A complete isolated fixture; wait real first capture and independent review',True),
        ('D2_RESEARCH','SECTOR_OPERATIONAL_RESEARCH_CANDIDATE_V2',final+'D2_PRODUCER_SOURCE_MATRIX.json',
         'src/sector/d2_research_source_matrix_v1.py','PASS_SCOPED_RESEARCH','10/09 original missing_state not verifiable; 9/24 golden only','C source map/Genesis candidate; UNKNOWN remains UNKNOWN',False),
        ('D2_FORMAL','Creation-bound Sector Episode / field admission',final+'D2_PRODUCER_SOURCE_MATRIX.json',
         'src/sector/operational_candidate_v1.py','NOT_GRANTED','no legal current Genesis and six fields reviewed','Per-field admission using actual originals',True),
        ('COHORT_CAPTURE/ENROLLMENT','FirstObserved / independent Writer Grant',final+'STATE_PUBLISHER_ISOLATED_RUN.json',
         'src/workbench_analysis/full_state_first_observed_v1.py','ENGINEERING_ONLY_FORMAL_DENOMINATOR_NULL','no admitted real source or scoped Grant','A freeze→candidate→extract→prepare fixture; real T0 then separate Grant',True),
        ('FEP_SHADOW/PRODUCTION','Accepted Model Registry / as-recorded Prediction Owner',final+'FEP_CURRENT_SOURCE_READBACK.json',
         'src/workbench_analysis/fep_e5/admission.py','PRODUCTION_OFF_REAL_FEP_SHADOW_NOT_ADMITTED','Registry/Head/CAS, matured FIT and independent Grant absent; six fields null','E hold; optional isolated engineering after trustworthy sources',True),
        ('FP13_READ_QA','CORE_PRODUCT_BFF_R1 / current research scope','docs/evidence/fp13_20261008/FINAL_ACCEPTANCE.json',
         'src/workbench_service/core_product_bff_r1.py','RESEARCH_READ_SCOPED_EVIDENCE_READY_FULL_FP13_BLOCKED','full product/source coverage and browser acceptance incomplete','D live HTTP semantic matrix; independent scope signoff',False),
        ('FP14_FULL','Independent release scope signer','docs/evidence/fp14_20261008/FINAL_ACCEPTANCE.json',
         'config/v4_full_product_qa_contract_v1.json','NOT_GRANTED','full FP13 and full release gates absent','Prepare limited research release/rollback contract only',False),
    ]
    rows = [dict(capability=c, owner=o, exact_source=ref(ROOT,s), code=ref(ROOT,k), status=v,
        blocker=b, next_action=n, requires_real_future_date=f) for c,o,s,k,v,b,n,f in specs]
    publish(ROOT, OUT+'/CAPABILITY_GATE_LEDGER.json', dict(contract_id='SINGLE_CAPABILITY_GATE_LEDGER_R1',
        exact_BASE=BASE, rows=rows, facts=dict(research_TRUE=300, research_signal_count=20896,
        prior_pytest=200, formal_observation_denominator=None, formal_matured_denominator=None,
        historical_1009_first_hand_observation=False), final_overrides_same_round_provisional=True,
        original_evidence_deleted=False, external_acceptance=False))
    text(OUT+'/CAPABILITY_GATE_LEDGER.md', '# 单一能力门账本\n\n机器权威版：CAPABILITY_GATE_LEDGER.json；每行 exact source 与源码均含字节 SHA。\n\n'
        '| 能力 | Owner | 当前状态 | 阻断 | 下一动作 | 需真实未来日期 |\n|---|---|---|---|---|---|\n' +
        ''.join(f"| {r['capability']} | {r['owner']} | {r['status']} | {r['blocker']} | {r['next_action']} | {r['requires_real_future_date']} |\n" for r in rows) +
        '\n300 TRUE 是股票×场景研究标签；200 pytest 是前轮工程测试。10/09 原件为事后重建，正式观察和成熟分母均为 null。final 回读覆盖同轮 provisional 解释，原证据保留。\n')
    text(OUT+'/E_HOLD_AND_ADMISSION_REQUIREMENTS.md', '''# E：FEP 保持关闭与独立准入条件

引用前轮 final/FEP_CURRENT_SOURCE_READBACK.json 的精确冻结事实，不重复运行300个权限检查。当前 current_gate fail-closed：可信生产Registry、部署Head/CAS、已接纳DB Owner、as-recorded Prediction、成熟FIT和独立范围Grant未齐；六字段 SOURCE_INCOMPLETE/null，production_authorized=false。

隔离接口或历史工程模型不签生产权限。E3/E4可选，FEP不成为Core Shadow、FP13研究读域或Native业务的全局前置。当前源尚无新增获准事实，本轮不启动新的宏大FEP版本。

真实首日Cohort只有在State来源独立审查和精确Writer Grant具备后冻结；其后按原V4-15日历和due plan累计T+1/T+3/T+5。未成熟为PENDING，到期缺settlement为UNKNOWN，无正式分母不给胜率；Focus历史样本不补分母。Amount H21历史缺20个首次成员日仍NOT_VERIFIABLE，未来第21个严格连续样本可另行审查；不阻塞无关Native业务。

下一动作：独立审查A/B/C候选接口与真实10/12首获；准入按字段和能力逐项签出。FEP生产启用为后续独立支线，本轮无授权、无预测写入。
''')
    print(json.dumps(dict(exact_BASE=BASE, rows=len(rows), stage_contract=OUT+'/STAGE_CONTRACT.json')))


if __name__ == '__main__':
    main()
