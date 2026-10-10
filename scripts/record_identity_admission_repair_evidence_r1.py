"""Record actual isolated calls and exact protected-head readback; no production writes."""
from pathlib import Path
import sys, os, json, shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT)]
for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
import pytest
from scripts.record_next_stage_contract_r1 import text
from scripts.record_identity_admission_repair_contract_r1 import OUT
from workbench_analysis.v4_14_replay_io import publish, ref
from test_cross_day_capture_repair_v1 import chain
from test_identity_gate_reason_r2 import exercise_provider_identity_classification
from test_next_stage_c_episode_genesis import genesis
from sector.episode_genesis_candidate_v2 import create, observe
from workbench_analysis.state_trusted_review_candidate_v1 import review_candidate


def document(name, content):return text(OUT+'/'+name,content.encode('utf-8'))


def main():
    output=ROOT/OUT
    results=[]
    for mode in ('same','new','delist','rename','suspended','tdx_conflict','package_missing','member_version'):
        folder=output/'B_FIXTURES'/mode;folder.mkdir(parents=True,exist_ok=True)
        with pytest.MonkeyPatch.context() as patch:
            fixture=chain.__wrapped__(folder,patch)
            result=exercise_provider_identity_classification(fixture,patch,mode)
        results.append(result)
    publish(ROOT,OUT+'/B_IDENTITY_CROSS_DAY_ORACLE.json',dict(
        contract_id='ACTUAL_VERIFY_SOURCE_GATE_INDEPENDENT_SET_AND_NUMERIC_ORACLE_R2',
        evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY',cases=results,
        production_write_authorized=False,formal_cohort_enabled=False))
    publish(ROOT,OUT+'/B_GATE_REASON_CONTRACT_R2.json',dict(
        contract_id='DATED_IDENTITY_GATE_REASON_R2',provider_failure='WAIT_BAOSTOCK_DAILY',
        provider_normal_previous_scope_mismatch='WAIT_DATED_IDENTITY_AUTHORITY',
        scheduler_recheck_preserves_saved_identity_gate=True,
        identity_admission='ACCEPTED_INDEPENDENT_REVIEW_SERVICE_NOT_DEPLOYED',
        missing_identity_facts='UNKNOWN',actual_runtime_module_loaded=False))
    claims=[dict(reviewer_role='INDEPENDENT_REVIEWER',decision='ACCEPT'),
            dict(Writer_Grant=True),dict(first_available='2999-01-01T00:00:00Z'),
            dict(revision='OTHER'),dict(membership_date='2026-10-09'),
            dict(episode=None),dict(universe='FOCUS_TOP_K'),dict(benchmark='CALLER_DEFINED'),
            dict(accepted_head=dict(sha256='0'*64))]
    negatives=[]
    for index,claim in enumerate(claims):
        binding=publish(ROOT,OUT+f'/A_FIXTURES/local-review-{index}.json',claim)
        result=review_candidate(ROOT,review_binding=binding,**claim)
        assert result['status']=='NOT_ADMITTED' and not result['formal_cohort_enabled']
        negatives.append(dict(input=binding,claim=claim,actual=result))
    publish(ROOT,OUT+'/A_AUTHORITY_NEGATIVE_ORACLE.json',dict(
        evidence_class='CALLER_DOCUMENT_NEGATIVE_TEST_ONLY',cases=negatives,
        limitation='No deployed trusted State source service; semantic validity cannot confer admission. Signed transport tests are isolated identity protocol fixtures, not a State service deployment.',
        trusted_adapter_deployed=False))
    requirements={
      'State':dict(owner='FULL_STATE_SIGNAL_OWNER',source='Original full-universe capture and accepted versioned State producer; Focus Top-K/reconstructed research cannot substitute',missing=['independent trusted review','actual new-day first capture','accepted State source revision']),
      'Membership':dict(owner='DATED_MEMBERSHIP_OWNER',source='Original same-day membership snapshot AS_RECORDED with immutable set/version; local latest members cannot prove historical PIT',missing=['actual new-day capture','accepted exact source binding']),
      'Model':dict(owner='MODEL_REGISTRY_OWNER',source='Independently accepted model registry revision and provenance',missing=['true registry owner','independent review']),
      'Episode Event':dict(owner='EPISODE_GENESIS_AND_SETTLEMENT_OWNER',source='Creation-bound original source event and frozen membership/AST, followed by due-day exact settlement source',missing=['actual lawful Genesis','due settlement owners']),
      'Benchmark':dict(owner='BENCHMARK_SOURCE_OWNER',source='Frozen contract-defined benchmark original bytes, date, revision and clocks; caller aliases cannot substitute',missing=['accepted actual benchmark source','trusted review'])}
    for item in requirements.values():
        item.update(earliest_legal_observation='Actual first availability, request and receipt on the authorized target session; never retroactively assigned',source_gaps_when='Any missing exact source binding, owner/revision, date, original clocks, valid independent review, full scope or matching Head CAS')
    publish(ROOT,OUT+'/STATE_REAL_SOURCE_REQUIREMENTS.json',dict(contract_id='STATE_REAL_SOURCE_REQUIREMENTS_R1',sources=requirements,
        required_review_fields=['pinned issuer','capability/scope','audience','valid_from/valid_until','independent revocation epoch','exact original source SHA/revision/clock','accepted Head CAS SHA'],
        deployed_review_service=None,production_adapter_deployed=False,
        reconstructed_20261009_and_synthetic_admitted=False))
    folder=output/'C_FIXTURE';folder.mkdir(parents=True,exist_ok=True)
    root,docs,refs,kwargs,days=genesis.__wrapped__(folder)
    episode=create(root,**kwargs)
    samples=[dict(label='NO_EPISODE',payload=observe(root,trade_date=days[0],calendar_binding=refs['calendar']))]
    for age in (0,1,3,5):
        samples.append(dict(label='HORIZON_AGE_'+str(age),payload=observe(root,episode_binding=episode,trade_date=days[age],calendar_binding=refs['calendar'])))
    publish(ROOT,OUT+'/C_FRONTEND_INTERFACE_SAMPLES.json',dict(
        contract_id='FOLLOWUP_DISPLAY_SEMANTICS_R2',evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY',
        fields=dict(followup_complete=['TRUE','FALSE','UNKNOWN',None],followup_status=['NO_PRIOR_EPISODE','PENDING','UNKNOWN','COMPLETE']),
        samples=samples,production_endpoint_wired=False))
    for source,name in [('G:/codex_tmp/B_IDENTITY_FINAL_JUNIT.xml','B_IDENTITY_FINAL_JUNIT.xml'),('G:/codex_tmp/A_C_REPAIR_JUNIT.xml','A_C_REPAIR_JUNIT.xml')]:
        text(OUT+'/'+name,Path(source).read_bytes())
    contract=json.loads((output/'STAGE_CONTRACT.json').read_bytes())
    after={p:ref(ROOT,p) for p in contract['protected_heads_before']}
    assert after==contract['protected_heads_before']
    publish(ROOT,OUT+'/PROTECTED_HEADS_READBACK.json',dict(before=contract['protected_heads_before'],after=after,unchanged=True,production_restart=False,TDX_written=False))
    old='docs/evidence/next_stage_after_audit_r1_20261010'
    historical={p.relative_to(ROOT).as_posix():ref(ROOT,p.relative_to(ROOT)) for p in (ROOT/old).glob('*') if p.is_file() and ('D_' in p.name or 'E_' in p.name)}
    publish(ROOT,OUT+'/D_E_HISTORICAL_EVIDENCE_BINDINGS.json',dict(historical_frozen_bindings=historical,http_cases=68,js_tests=5,rerun=False,external_scope_signoff=False))
    document('B_IDENTITY_AUTHORITY_PRODUCER.md','''# 同日 Identity 候选与主 DD 分类修复

实际 verify_source_gate 的原始提供方日期、数值和 active 覆盖先独立核对。旧身份集合失配单列 dated_identity_authority，提供方正常时返回 WAIT_DATED_IDENTITY_AUTHORITY，DailyJobs 对保存的证据重算也保留此状态。正常同范围仍按原门处理；提供方矛盾/缺行仍拒绝。受保护 last-good Head 不变。

dated_identity_candidate_v1 输入五份原始版本化绑定：roster（含与原始 BaoStock 对应的行情和身份）、TDX、GBBQ 原件、官方时态身份事件、同日 AS_RECORDED 成员。全部需实际目标日及请求/接收/首次可用时钟。未知上市/退市/改代码事实不猜测；缺成员时钟时 first_available 为 null。候选不自行准入，不改变主 DD scope。

真实独立审查服务不存在。默认 admission_candidate 永远 NOT_ADMITTED。IsolatedReviewAuthority 仅为明确合成测试运输合同：固定签发者、签名、能力/范围、有效期、撤销、原件版本/时钟、Head CAS；仅允许 docs/evidence 测试 Head，生产 Head 路径拒绝。CAS 后回读失败恢复原始字节，重试幂等。它不构成生产信任锚。

8 个实际门函数差异样本见 B_IDENTITY_CROSS_DAY_ORACLE.json。合法同日候选、未知新增、退市、改代码、停牌、成员绑定/版本、缺行、矛盾、非法回建、CAS/回滚见定点 JUnit。真实运行中的 28765 未重启，本轮源码不代表生产已加载。

唯一实际新日结论：WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER。阻断为真实新日来源尚未发生、独立 Identity 审查服务未部署、生产模块加载另需明确授权和独立验收；工程接口已有可重复验证，不列无限等待。
''')
    document('A_TRUSTED_REVIEW_BOUNDARY.md','''# State 可信审查边界

旧 state_publisher_bridge_v1.py 完全保留，其合成成功通道不升级为正式批准。新 state_trusted_review_candidate_v1.review_candidate 只进入独立 resolver，不接受 caller 传入 trust anchor/服务/签发密钥；部署的 accepted review service 为缺失，故 NOT_ADMITTED、UNTRUSTED_REVIEW_CANDIDATE，bridge_executed=false，STATE_SOURCE_ADMITTED=false，formal_cohort_enabled=false。

普通工作区 reviewer_role/decision、伪造 Grant、时间、revision、旧日 Member、缺 Episode、Focus Top-K、错误 benchmark、伪造 Head 均不能打开入口，实际结果及原件绑定见 A_AUTHORITY_NEGATIVE_ORACLE.json。签名运输合同的正反例额外验证 issuer/scope/有效期/撤销/原件/Head 绑定，但仅为隔离 Identity 合成协议测试，不能称为已部署可信 State adapter。

State/Membership/Model/Episode/Benchmark 真源要求与缺口见 STATE_REAL_SOURCE_REQUIREMENTS.json。将来仅在独立服务部署和接受后，才允许服务解析出的绑定进入 Bridge；本轮不能演示真实 accepted State Review 的成功通道，此项明确待真实源和独立验收。
''')
    document('C_FOLLOWUP_SEMANTICS_R2.md','''# D2 随访分类 R2

核对冻结 config/v4_10_input_provenance_r1_2.json 与 D2 admission：followup_complete 保留 TRI TRUE/FALSE/UNKNOWN；无 Episode 为 null。该生产者全部完成才 TRUE，其余 UNKNOWN，不把未到期填成失败。

新增 followup_status：无合法 Episode 为 NO_PRIOR_EPISODE；全部未到期或已完成与未到期混合、且无缺源为 PENDING；任一到期缺合法 settlement 或日历不覆盖 horizon 为 UNKNOWN；所有 horizon 完成为 COMPLETE。next_due_date 为仍待到期且已知日历日期的最早值。unknown_due_reasons 逐 horizon 列出缺日历或到期缺/错 Episode 来源。停牌、退市、旧事件不能替代创建绑定的 settlement；合法迟到来源可使对应 horizon 完成。

C_FRONTEND_INTERFACE_SAMPLES.json 提供前端可直接读取的真实函数输出形状，全部明确合成测试；本轮未把字段接入生产 HTTP，不宣称生产页面已显示。Python 验证单/混合 horizon、迟到完成、日历断档、无 Episode/Owner、停牌与退市；Genesis 无历史回填。
''')
    document('D_BROWSER_ENV_EXIT_PLAN.md','''# 本轮浏览器环境退出清单

本轮只尝试一次 IAB 打开 http://127.0.0.1:28765/v4/research；工具返回 net::ERR_BLOCKED_BY_CLIENT，状态 BLOCKED_BROWSER_ENV。未取得 DOM、截图、Console 或请求日志，不宣称 1366/1920 验收通过，停止重复尝试。28765 未停止或重启。

可复现手工清单：在实际 Windows 浏览器打开上述地址；分别设 1366 与 1920 宽度。记录初始真实日期、URL、DOM/全屏图、Console 与 Network 日志；选择历史日期再回最新；搜索证券/板块，进入第二页；核对股票/板块/市场/Focus/诊断/Chart/历史页；让单组件来源缺失，核对其他组件仍可读；换日期后触摸/点击旧 token 必须拒绝。保存每一步图片、请求原件和时间戳到 G:/codex_tmp，不把缺源响应计 READY。

候选页面现有源码明确显示 evidence_class、源截止日期、历史 first-available、候选冻结、来源再观察；RECONSTRUCTED_RESEARCH_ONLY 不证明历史已知。真实当前首次观察必须真实独立采集及准入；300 TRUE/79 研究 CONFIRMED 不计正式 Cohort 或成熟 Forward。
''')
    document('D_RESEARCH_SCOPE_ACCEPTANCE_MATRIX.md','''# FP13 只读研究范围提交

|范围|已有工程证据|本轮验收状态|
|---|---|---|
|市场/股票/板块/Focus/诊断/Chart/历史阅读|旧 68 个真实 HTTP + 5 个 JS，原始 SHA 绑定保留|FP13_RESEARCH_READ_SCOPE_PENDING_EXTERNAL_SIGNOFF|
|1366/1920 DOM/截图/Console/交互|一次 IAB ERR_BLOCKED_BY_CLIENT|BLOCKED_BROWSER_ENV，按退出清单待实际浏览器验收|
|研究候选身份/来源时钟|现有页面源码及原只读证据|保持研究身份，真实 first capture 待发生|
|Forward/FEP/严格回放/正式 Cohort|合法源或独立 Grant 缺失|SOURCE_INCOMPLETE / NOT_GRANTED，不能计 READY|

旧 HTTP/JS 证据仅作为冻结历史，未重复声称本轮重新运行。外部独立范围签收未获得；FP14_FULL_NOT_GRANTED。
''')
    document('REAL_T0_20261012_RUNBOOK.md','''# 10/12 实际 T0 现场执行手册

当前唯一结论 WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER。预计交易日须以正式日历确认；周末不执行真实采集或改时钟。已有实际调度时点为北京时间 18:35、19:05、19:35、20:05、20:35、21:05、22:05。

1. 在 G:/codex work/大A交易 设 TMP/TEMP/TMPDIR=G:/codex_tmp、PYTHONDONTWRITEBYTECODE=1；fetch/readback 远端，确认目标日期、Phase0 FULL_PASS 和两个受保护 Head SHA。不得假称本轮源码已加载到生产。
2. 按已授权只读调度获取当日原始 roster/BaoStock 与 TDX 包/GBBQ/Member 原件，保存请求、接收、first-available 和原始 SHA；确认 actual provider 日期/active 覆盖/数值。来源异常按提供方等待，正常但旧池变化记录 WAIT_DATED_IDENTITY_AUTHORITY，保留 last-good。
3. 对真实已有官方 Listing/Delisting/改代码事件调用 dated_identity_candidate_v1.build(root,sources=五份 exact refs,parent_head=旧 accepted Head ref,candidate_directory='docs/evidence/实际日期_identity_candidate',cutoff=实际带时区时间)。先核对源 JSON 合同，缺字段保留 UNKNOWN/SOURCE_GAPS。admission_candidate 目前应返回 NOT_ADMITTED；不把合成 HMAC 当真实授权。
4. 独立审查方需先部署并验收真实 issuer/capability/revocation 服务及 exact source/Head-CAS 合同；另行获得改真实准入源/加载或重启生产/Writer Grant 的明确范围授权。满足前不得调用生产发布，真实服务缺失保持精准阻断。
5. State/Member/Model/Episode/Benchmark 按 STATE_REAL_SOURCE_REQUIREMENTS 核查，首次实际捕获必须当天事实。合法 Genesis 冻结成员、AST、价格与 due-plan，后续按真实日历和 settlement Owner 区分 PENDING/UNKNOWN/COMPLETE。缺一个域不停止其他合法只读研究。
6. 实际发布另行授权后执行两 Head CAS/重试/回读失败回滚现场 QA，留 before/after、原件 SHA、唯一状态与独立验收。提交并 push code/evidence，Drive 原始字节回读。Push 不构成外部验收。

工程可运行验证命令见本轮报告；以上生产发布步骤的必要授权和真实服务均未由本任务卡授予，不能现在执行。
''')
    document('REPORT.md','''# Identity / State / D2 精确修复交付

基线 d7b19feabc8e17ca4948bfdef38047f10fd6f97c，Phase0 FULL_PASS。P0 门分类及同日 Identity 候选、State fail-closed resolver、D2 三值保留与显式到期分类已落实源码和定点验证。受保护运营/严格 Head 原始 SHA 完全不变；TDX 只读；无 28765 重启、真实准入变更或 Writer Grant。

|分域|结论|
|---|---|
|OPERATIONS_READ_SCOPED|既有合法研究只读范围保留；本轮源码未加载生产|
|IDENTITY_AUTHORITY_ENGINEERING|工程验证通过；正式身份准入仍关闭|
|STATE_REVIEW_TRUST_BOUNDARY|默认 resolver 与普通 caller 隔离；真实 accepted review service 尚无|
|D2_EPISODE_ENGINEERING|三值字段不变，PENDING/UNKNOWN/COMPLETE 分类工程通过|
|FP13_BROWSER_SCOPE|BLOCKED_BROWSER_ENV；FP13_RESEARCH_READ_SCOPE_PENDING_EXTERNAL_SIGNOFF|
|REAL_FIRST_CAPTURE_PENDING|真实下一交易日采集尚未发生|
|FORMAL_COHORT_NOT_GRANTED|保持关闭|
|FEP_HOLD|复用旧 E_HOLD；六预测字段仍 SOURCE_INCOMPLETE/null，无重复预测测试|
|FP14_FULL_NOT_GRANTED|保持关闭|

唯一 T0 结论 WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER，详见 10/12 手册。独立 State 服务成功通道和实际浏览器验收明确尚未完成；本轮只验收工程及失败关闭，不制造正式通过。

验证：B 定点回归 63 passed；A/C 定点回归见 A_C_REPAIR_JUNIT.xml；实际差异 Oracle、原件与前端接口样本同目录。先前 C 合成日历样本路径冲突已修正为独立捕获，最终 JUnit 为修复后的重验结果。综合审计项 M10 Amount A 等沿用独立跟踪，不用本轮工程门抵销。

复现：PowerShell 设置 TMP/TEMP/TMPDIR 到 G:/codex_tmp 及 PYTHONDONTWRITEBYTECODE=1；python -B -m pytest tests/test_identity_gate_reason_r2.py tests/test_dated_identity_candidate_v1.py tests/test_state_trusted_review_candidate_v1.py tests/test_followup_semantics_r2.py --basetemp=G:/codex_tmp/test_temp/repair_recheck -o cache_dir=G:/codex_tmp/pytest_cache_repair。Git/Drive exact-byte 回读收据在交付收尾补充。
''')
    print(json.dumps(dict(output=OUT,gate_cases=len(results),negative_cases=len(negatives),heads_unchanged=True)))


if __name__=='__main__':main()
