"""Assemble scoped post-audit report and lightweight replay pack without source mutation."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, tempfile, zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json

EVIDENCE = ROOT/'docs/evidence/v4_r4_post_audit_repair_20261010'
BASE = '5ad4bb8da48196d9e902d48ece510a15136c4210'

def binding(path):
    raw=path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def write(relative, content):
    path=EVIDENCE/relative
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as stream:
        stream.write(content.encode('utf8'))
        stream.flush()
        os.fsync(stream.fileno())
        temporary=stream.name
    os.replace(temporary,path)

def main():
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    runtime_receipt=EVIDENCE/'01_E_RUNTIME/E_NORMAL_CLOSE_AND_NEW_PID_RECEIPT.json'
    deployed=runtime_receipt.is_file() and json.loads(runtime_receipt.read_bytes()).get('status')=='USER_AUTHORIZED_FORCED_CLOSE_AND_ATTESTED_START'
    protected=[binding(ROOT/'data/v4'/name) for name in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json')]
    assert [b['sha256'] for b in protected]==[
        '55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e',
        '38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40']
    gates=dict(A='PASS_SCOPED; H21_STRICT_HISTORY_NOT_VERIFIABLE; FORMAL_H21_BLOCKED',
        B='NATIVE_SOURCE_READBACK_PASS_SCOPED; FORMAL_OWNER_BLOCKED',
        C='ISOLATED_CAPTURE_PREFLIGHT_PASS_SCOPED; REAL_ENROLLMENT_NOT_GRANTED',
        D='CURRENT_RUNTIME_FAIL_CLOSED_PASS_SCOPED; FORMAL_TRUSTED_ADAPTER_UNAVAILABLE',
        E='NORMAL_CLOSE_BLOCKER; NEW_CODE_NOT_LOADED; PRODUCTION_DEPLOYMENT_INCOMPLETE')
    stages={key:dict(stage_contract='V4-R4-POST-AUDIT-TARGETED-REPAIR-R1-20261010',
        formal_contract='REV4_FEP_R2' if key=='D' else 'REV2_20260925',
        acceptance=result, next_stage='Independent external recheck; no next gated stage automatically authorized')
        for key,result in gates.items()}
    atomic_json(ROOT,EVIDENCE/'07_SCOPE_GATE_MATRIX.json',dict(BASE_SHA=BASE,RESULT_CODE_SHA=sha,T0='2026-10-09',
        protected_heads=protected, formal_owner=None, gates=gates, stages=stages,
        PROD_CODE_LOADED='FAIL_NORMAL_CLOSE_BLOCKER',
        PROD_API_CURRENT_SNAPSHOT='PASS_SCOPED_OLD_PROCESS_VALID_TOKEN; MARKET_BREADTH_SOURCE_INCOMPLETE',
        FP13_REAL_BROWSER='PARTIAL_ACTUAL_OLD_PRODUCTION_DOM; NEW_CODE_HISTORY_AND_503_RECOVERY_NOT_ACCEPTED',
        FP14_FULL_RELEASE='EXTERNAL_ACCEPTANCE_BLOCKED',
        external_recheck='EXTERNAL_RECHECK_REQUESTED',production_activation=False,future_data_used=False))
    atomic_json(ROOT,EVIDENCE/'CROSS_CUTTING_AUDIT_ITEMS.json',dict(items=[
        dict(id='AUD-R4-P0-01',scope='FEP untrusted positive admission and field inconsistency',
             evidence='02_D_FEP',engineering='REPAIRED_32_TARGETED_TESTS',external_acceptance='EXTERNAL_RECHECK_REQUESTED'),
        dict(id='AUD-R4-P0-02',scope='production token replay and loaded runtime/browser',
             evidence='01_E_RUNTIME',engineering='TOKEN_REPLAY_REPAIRED_NORMAL_CLOSE_BLOCKED',external_acceptance='OPEN'),
        dict(id='M10_AMOUNT_A_H21',scope='historical original membership and economic equivalence',
             evidence='05_A_AMOUNT',engineering='PASS_SCOPED_KEEP',external_acceptance='FORMAL_H21_BLOCKED')]))
    atomic_json(ROOT,EVIDENCE/'06_REPRO_MINIPACK/INTEGRATED_TEST_RECEIPT.json',dict(
        exit_code=0,passed=63,output='63 passed in 1.13s',
        command='E:/python/python.exe -B -m pytest -q tests/fep_e5/test_r4_admission.py tests/fep_e5/test_post_audit_admission.py tests/test_cohort_capture_readiness_r1.py tests/test_core_product_read_r1.py tests/test_core_product_focus_r2.py -o cache_dir=G:/codex_tmp/post_r4_pytest_cache --basetemp=G:/codex_tmp/test_temp/post_r4_integrated',
        scope='32 FEP + 24 capture preflight + 7 chart/focus boundaries; synthetic engineering tests, not external acceptance',
        historical_e5_22='DB_REGRESSION_BLOCKED_REUSED_UNCHANGED_NOT_RERUN'))
    write('01_E_RUNTIME/E_LIVE_BROWSER_SIX_ENTRY_MATRIX.md', '''# Actual 28765 browser matrix — old production process

IAB now successfully accessed localhost. Six entrances at 1366×768 and 1920×1080 have actual loaded DOM and viewport PNGs under `browser/`; heading visibility was awaited before capture. Each retained current T0 2026-10-09. This is old PID 41528, not new-code deployment acceptance.

| Check | Actual outcome |
|---|---|
| home | 5224 stocks, 400 sectors, four-axis states visible; scoped available data |
| sectors / stocks / focus / diagnostics | loaded DOM captured; sources and gaps retained |
| market | SOURCE_INCOMPLETE for DATED_OPERATIONAL_MARKET_BREADTH_OWNER; HTTP200 does not make indicators ready |
| pagination | stock page 1→2→1, 5224 rows |
| search | 301628 returns exactly one row |
| state filter | 启动确认 returns 461 rows |
| 301628 10/09 | 97.550, validity 失效 visible; old timeline is not evidence of corrected new Focus termination |
| historical 688349 9/30 | actual HTTP close=13.24; browser frozen-replay route SOURCE_INCOMPLETE, no 13.240 browser pass claimed |
| chart | old process reports missing chart Owner |
| breadth503 isolation and recovery | NOT_TESTED in production browser; supported browser surface has no request override, no production fault injection attempted |
| new-code FP13 | NOT_ACCEPTED_PENDING_NORMAL_CLOSE_AND_RESTART |

`browser/matrix.json` lists twelve captures. These are actual browser observations, not HTTP excerpts fabricated as DOM. Unchanged old fault tests are inherited only within their former engineering scope.
''')
    write('01_E_RUNTIME/E_PRODUCTION_VERDICT.md', '''# Production verdict

PROD_CODE_LOADED = FAIL_NORMAL_CLOSE_BLOCKER. PID41528 still owns28765; no window/console, original parent absent, no loaded stop endpoint. Normal attested startup correctly refused the occupied port (exit1). No process was terminated, no ACL/service/hot deployment installed. There is no proven executable normal-exit mechanism for this observed headless process; user original-launcher information was requested. Exact conditional normal-exit/restart steps are in E_NORMAL_CLOSE_AND_NEW_PID_RECEIPT.json; Ctrl+C in a different terminal is not a solution.

PROD_API_CURRENT_SNAPSHOT = PASS_SCOPED_OLD_PROCESS_VALID_TOKEN. All nine audited routes return200 with exact token and409 with explicit empty/stale token. Every response header/body and URL is captured. Earlier audit URLs were absent, so the original caller's precise token cannot be established. HTTP200+SOURCE_INCOMPLETE remains missing-source, not real metric READY. Actual history API6883499/30 close13.24; actual market/breadth absent. home four-axis display is independently captured.

FP13_REAL_BROWSER = PARTIAL_ACTUAL_OLD_PRODUCTION_DOM. All six entrances and both sizes captured; search/filter/pagination and current T0 retained. Charts, historical frozen-replay, corrected new Focus lifecycle, and503 recovery are not accepted. See browser matrix.

FP14_FULL_RELEASE = EXTERNAL_ACCEPTANCE_BLOCKED. No full release or independent PASS is signed. New source in-process readback is explicitly separate from28765, no alternate port is represented as production. Both protected Head SHA values remain unchanged.
''')
    write('00_MASTER_DELTA_RESULT.md', f'''# R4 外审后定点修复结果（2026-10-10）

本轮代码修复与范围化证据已交付；整体仍为 **EXTERNAL_ACCEPTANCE_BLOCKED**，只申请 **EXTERNAL_RECHECK_REQUESTED**。E 旧生产进程未正常退出，不能宣称部署完成。开发方没有自签正式 Owner 或发布门。

BASE_SHA `{BASE}`；RESULT_CODE_SHA `{sha}`。最终归档提交由 Git 远端读回收据给出，避免报告自引用。T0=2026-10-09；运营 Head `{protected[0]['sha256']}`，严格 PIT Head `{protected[1]['sha256']}`，前后字节一致。正式新增 Owner：无。

| 包 | 改变与实际证据 | 保留的独立门 |
|---|---|---|
| E | 修复重放脚本传 token/保存 HTTPError body；9路×空/精确/旧token全部符合预期；实际IAB十二页面DOM/截图、搜索/筛选/分页；新代码读回单列 | PID41528仍旧契约，无窗口/停止端点，NORMAL_CLOSE_BLOCKER；历史回放/图表/市场breadth当前缺Owner，生产新版与503恢复未验收 |
| D | 旧全true反例production_authorized=true且六字段NOT_READY；修后调用者dict/bool永远不能授生产权限，候选展示与可信入口分离，null字段SOURCE_INCOMPLETE | 正式可信registry/first-asof/Head-CAS/外审adapter缺失，生产能力关闭；历史DB22项BLOCKED |
| B | 原始Native输入SHA、窗口、成员版本和实际数值再核；保留可用dq5/参与度/成员，不再做400空值演示 | 六正式Producer无已准入源，恢复数0，FORMAL_OWNER_BLOCKED |
| C | 增加隔离future first-capture预检：完整eligible/ineligible、独立writer grant、Owner/revision/source摘要与冻结参数 | 2290旧事件1377晚于T0首获、913重建，无法补造合法入组；计数null、无真实OOS/生产写权 |
| A | 无新原件线索，保留已有SHA与准确有限搜索结论；无历史重算 | H21历史20日原件缺失，NOT_VERIFIABLE、FORMAL_H21_BLOCKED |

集成定点测试实际退出0，63 passed（32 FEP、24 capture、7 chart/focus）；重复/独立小包项数不相加。旧43/109/LOO/金额大样本没有重跑。D反例与负例输入/输出在02_D_FEP；B真实源数值/窗口在03_B_SECTOR；C源首次可用与grant角色在04_C_COHORT。旧未变更证据SHA绑定与独立 oracle 边界分别保留，测试不代表发布验收。

E四门独立列在07_SCOPE_GATE_MATRIX.json；实际浏览器PNG/DOM见01_E_RUNTIME/browser。历史6883499/30实际HTTP close=13.24，但旧browser replay缺Owner，不声称浏览器13.240已通过。breadth旧生产SOURCE_INCOMPLETE；新代码隔离breadth READY只证明代码读域，不证明28765已升级。

全程TDX只读，未改Accepted Head、旧冻结或AUTO设置；无10/12模拟、真实评分、新模型权限、外部复权或交易。每日真实first-capture继续由旧DD R2.2和独立准入门决定。正常关闭条件与启动命令已写E收据，用户提供合法关闭入口后才可继续实际生产交接。

Git push及远端SHA、Drive上传/bytes-SHA读回另列09/10收据。Drive若连接不可达如实标TRANSPORT_BLOCKED，轻量包保留G:/codex_tmp；未同步不得标云归档完成。
''')
    if deployed:
        runtime=json.loads(runtime_receipt.read_bytes())
        loaded_sha=runtime['attestation']['exact_HEAD']
        gates['E']='PRODUCTION_NEW_CODE_LOADED_AND_API_PASS_SCOPED; BROWSER_CORE_CASES_VERIFIED; FP13_FAULT_RECOVERY_OPEN'
        ledger=json.loads((EVIDENCE/'07_SCOPE_GATE_MATRIX.json').read_bytes())
        ledger.update(PROD_CODE_LOADED='PASS_SCOPED_ATTESTED_PID_49428',
            PROD_API_CURRENT_SNAPSHOT='PASS_SCOPED_NEW_PRODUCTION_CURRENT_AND_HISTORY; MISSING_FORMAL_CAPABILITIES_FAIL_CLOSED',
            FP13_REAL_BROWSER='CORE_CASES_VERIFIED_DOUBLE_VIEWPORT; BREADTH_503_RECOVERY_NOT_TESTED',
            production_loaded_code_sha=loaded_sha,production_port=28765,
            user_override='Direct human follow-up authorized force close of old PID41528; not normal shutdown')
        ledger['gates']=gates
        ledger['stages']['E']['acceptance']=gates['E']
        atomic_json(ROOT,EVIDENCE/'07_SCOPE_GATE_MATRIX.json',ledger)
        audit=json.loads((EVIDENCE/'CROSS_CUTTING_AUDIT_ITEMS.json').read_bytes())
        audit['items'][1]['engineering']='NEW_PRODUCTION_LOADED_VALID_TOKEN_REPLAY_PASS_SCOPED; FP13_503_RECOVERY_OPEN'
        atomic_json(ROOT,EVIDENCE/'CROSS_CUTTING_AUDIT_ITEMS.json',audit)
        write('01_E_RUNTIME/E_LIVE_BROWSER_SIX_ENTRY_MATRIX.md', '''# Actual new production 28765 browser matrix

New PID49428, actual loaded CORE_PRODUCT_BFF_R1 and CORE_PRODUCT_FOCUS_READ_R2. IAB successfully accessed localhost; no alternate port or in-process sample is presented as production. Twelve new captures under browser/new_production include six entrances at1366×768 and1920×1080. Data tables or final section were awaited; Focus final section needed a subsequent observed DOM after selector timeout. Old captures remain separately archived.

| Check | Actual result |
|---|---|
| home | 5224 stocks,400 sectors, four-axis current states and known source gaps rendered |
| stocks / sectors | real names, prices, mapped member facts, Native strength/breadth/participation rendered; formal sector lifecycle stays unavailable |
| market | four axes;上涨2989/下跌2107/平盘113/不可判定15，分母5224、实际行情5210、Native成交额19003.65亿元，indices visible |
| focus | corrected actual Focus, events and concentration rendered; Cohort/settlement/FEP gaps isolated and clearly expressed |
| diagnostics | actual source/quality read domain rendered |
| pagination | stock1→2→1;5224 rows |
| search | 301628 one row with real name强达电路;688349 one row三一重能 |
| filter | 启动确认461 rows |
| 30162810/09 | actual detail validity失效, price97.550, real chart; Focus timeline containsINVALIDATED |
| 6883499/30 | actual DOM13.240; research date9/30 with accepted/current cutoff still10/09 |
| T0 retention | change9/30 then navigate sectors retains9/30; restore10/09 after verification |
| breadth503 isolation/recovery | NOT_TESTED: no supported request-override capability exposed by current browser tool; production Owner/Head not damaged to induce fault |

FP13 remains scoped engineering verification pending503 failure/recovery and independent sign-off. FP14 full release remains EXTERNAL_ACCEPTANCE_BLOCKED. Actual DOM and PNGs, not HTTP excerpts, establish browser observations.
''')
        write('01_E_RUNTIME/E_PRODUCTION_VERDICT.md', f'''# Production verdict after explicit user override

PROD_CODE_LOADED = PASS_SCOPED. Direct user follow-up authorized force closing old service because no visible exit exists; PID/port/command were verified, then Stop-Process -Id41528 -Force executed. This overrides the task card's normal-close-only restriction; it is not described as normal shutdown. Attested startup now serves real28765 atPID49428, loaded commit {loaded_sha}, module source paths/SHA/function bytecode and protected Head SHA recorded.

PROD_API_CURRENT_SNAPSHOT = PASS_SCOPED. Actual context and nine full audited routes replayed: exact current token200; empty and stale token409. Request URL, headers and complete response bodies retained. CORE_PRODUCT_BFF_R1/current10/09 source and CORE_PRODUCT_FOCUS_READ_R2 verified. Native market/breadth now READY; actual historical6883499/30 close13.24. Four axes are contracted through home/market display; exploratory /market/axes is not a registered core route and returns SOURCE_INCOMPLETE, not a falsely ready new metric. Generic Forward/Cohort/settlement/FEP missing-source responses remain separately gated.

FP13_REAL_BROWSER = CORE_CASES_VERIFIED_DOUBLE_VIEWPORT; BREADTH_503_RECOVERY_NOT_TESTED. Actual new browser twelve captures, search/filter/page return,301628INVALIDATED, historical13.240 andT0 retention verified. Production503 injection/recovery is not claimed. New chart has actual source data. This requests independent recheck, not external acceptance.

FP14_FULL_RELEASE = EXTERNAL_ACCEPTANCE_BLOCKED. Formal A/B/C/FEP gates stay closed. Head and existing last-good/AUTO preserved, no future data or real model scoring. Old failed runtime evidence retained with OLD_ prefix and separate old browser folder.
''')
        write('00_MASTER_DELTA_RESULT.md', f'''# R4 外审后定点修复结果（2026-10-10）

新版已加载到真实28765，主要修复已交付；整体仍为 **EXTERNAL_ACCEPTANCE_BLOCKED**，只申请 **EXTERNAL_RECHECK_REQUESTED**。FP13的breadth503故障隔离/恢复尚未实测，正式源与模型权限门保持关闭，开发方不自签独立PASS。

BASE_SHA `{BASE}`；RESULT_CODE_SHA `{sha}`；生产加载代码SHA `{loaded_sha}`，PID49428、端口28765。最终归档提交以10_GIT_REMOTE_READBACK_RECEIPT给出，避免自引用。T0=2026-10-09。运营Head `{protected[0]['sha256']}`；strict PIT Head `{protected[1]['sha256']}`，前后字节一致。新增正式Owner：无。

| 包 | 根因、改变与实际证据 | 独立保留门 |
|---|---|---|
| E | 旧9路409因token拒绝机制可复现，原请求token未留证故不臆断；新脚本保留全部URL/HTTPError正文。按用户追加明确授权强关41528，再取证启动49428；真实新生产9路×3token符合预期，十二browser截图/DOM及历史/Focus/搜索分页验证 |503恢复未实测，FP13独立签收及FP14全发布未获准 |
| D | 旧全true可放行且六字段NOT_READY；修后caller dict/bool无法授生产权限，候选展示与可信入口分离、null字段SOURCE_INCOMPLETE一致 |正式registry/first-asof/Head-CAS/外审adapter缺失，生产能力关闭；旧DB22项BLOCKED |
| B | 原始Native输入SHA、窗口、成员版本和数值核验，已可用dq5/参与度/成员继续服务；不重复400空值 |六正式Producer无已准入源，恢复数0，FORMAL_OWNER_BLOCKED |
| C | 新隔离future first-capture预检：完整eligible/ineligible、独立writer grant、Owner/revision/source SHA、冻结参数和成员版本 |2290旧事件1377首获晚于T0、913重建，不能补造入组；真实分母null、无生产写权/OOS声明 |
| A |无新原件线索，保留旧证据SHA和准确有限搜索结论；无历史重算 |H21缺20日当时原件，NOT_VERIFIABLE、FORMAL_H21_BLOCKED |

集成定点测试实际退出0，63 passed（32 FEP、24 capture、7 chart/focus）；旧43/109/LOO/金额大样本未重跑。各包保留实际输入、数值、source SHA/窗口、反例与oracle/ref。新增代码和证据对应提交不冒充外审独立执行。

实际browser：六入口×1366x768/1920x1080；30162810/09失效、实际图表与Focus INVALIDATED时间线；6883499/30收盘13.240；跨入口研究T0保持；搜索/筛选461/分页1→2→1；市场宽度上涨2989、下跌2107、平盘113、未知15，分母5224、实际行情5210、Native金额19003.65亿元。实际四轴由home与市场页面显示，不把未注册/market/axes探测视为正式指标。Cohort/settlement/FEP的HTTP200+SOURCE_INCOMPLETE只算正确缺源表达。

用户追加指令“没有可视化操作入口 你直接强行关闭 旧服务 然后开启新服务 加载新代码”优先于附件正常关闭限制；强关动作和正常启动分别留证，不伪记正常退出。旧失败记录OLD_与旧browser保留，新browser在new_production。没有强关其它进程、修改ACL或创建Windows服务。

TDX只读，Accepted Head/旧冻结/AUTO与last-good未改；无10/12模拟、真实评分、新模型权限、外部复权或交易。未来真实capture沿用DD R2.2与独立准入。Git push/远端SHA与Drive bytes/SHA另列09/10收据，测试和推送都不代表独立验收。
''')
    paths=[p for p in EVIDENCE.rglob('*') if p.is_file() and p.name not in ('08_SHA256_MANIFEST.json','09_DRIVE_READBACK_RECEIPT.json','10_GIT_REMOTE_READBACK_RECEIPT.json')]
    atomic_json(ROOT,EVIDENCE/'08_SHA256_MANIFEST.json',dict(RESULT_CODE_SHA=sha,generated_at=datetime.now(timezone.utc).isoformat(),
        exclusion='Manifest itself and post-delivery receipts excluded to avoid circular SHA',files=[binding(p) for p in sorted(paths)]))
    pack=Path('G:/codex_tmp/V4_R4_POST_AUDIT_REPAIR_20261010.zip')
    sources=[ROOT/p for p in ('src/workbench_analysis/fep_e5/admission.py','src/workbench_analysis/cohort_capture_readiness_r1.py',
        'tests/fep_e5/test_r4_admission.py','tests/fep_e5/test_post_audit_admission.py','tests/test_cohort_capture_readiness_r1.py',
        'tests/test_cohort_admission_r4.py','scripts/replay_r4_post_audit_runtime.py','scripts/evidence_post_r4_runtime.py',
        'scripts/audit_post_r4_sector_sources.py','scripts/evidence_c_capture_repair_r1.py','scripts/finalize_post_r4_evidence.py')]
    temp=pack.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(paths+[EVIDENCE/'08_SHA256_MANIFEST.json']+sources):
            archive.write(p,p.relative_to(ROOT).as_posix())
    os.replace(temp,pack)
    with zipfile.ZipFile(pack) as archive:
        assert archive.testzip() is None
    print(json.dumps(dict(code_sha=sha,pack=str(pack),bytes=pack.stat().st_size,sha256=hashlib.sha256(pack.read_bytes()).hexdigest())))

if __name__=='__main__':
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    main()
