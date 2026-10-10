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
