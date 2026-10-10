"""R4 final scoped ledger and portable evidence seal; no source/Head writes."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/v4_current_snapshot_r4_20261010'

def ref(path):
    raw=path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def write(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp')
    raw=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    t.write_text(raw,encoding='utf8');os.replace(t,p)

def main():
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    before=json.loads((OUT/'00_PROTECTED_BEFORE.json').read_bytes())
    protected=[ref(ROOT/'data/v4'/n) for n in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json')]
    if [r['sha256'] for r in before]!=[r['sha256'] for r in protected]:raise ValueError('PROTECTED_HEAD_CHANGED')
    states=[
        ('A_AMOUNT','AMOUNT_ENGINEERING_AND_PROVENANCE_AUDIT_PASS_SCOPED','FORMAL_H21_BLOCKED_HISTORICAL_EVIDENCE','01_A_AMOUNT/A_FIX_AND_VERDICT.md','Only actual original first-capture membership for the missing 20 September sessions can reopen this history; future sessions cannot prove old captures.'),
        ('B_SECTOR','ENGINEERING_CANDIDATE_PASS_SCOPED','SECTOR_D2_OWNER_OPEN','02_B_SECTOR/B_SECTOR_ADMISSION_BLOCKERS.md','Independent acceptance of the exact sector extraction, frozen episode, due and scenario owners; no activation authorized.'),
        ('C_COHORT','COHORT_ENGINEERING_READY_SCOPED','REAL_COHORT_ENROLLMENT_NOT_GRANTED','03_C_COHORT/C_LIVE_ENROLLMENT_BLOCKER.md','A genuine T0 frozen event, first-availability, immutable Owner and Head-bound grant must be independently admitted.'),
        ('D_FEP','FEP_ENGINEERING_GATE_READY','FEP_CAPABILITY_NOT_READY','04_D_FEP/D_FEP_ACTIVATION_DECISION.md','Existing historical engineering models and Shadow grants do not authorize the current production model or input.'),
        ('E_RUNTIME','SCOPED_CODE_AND_HTTP_EVIDENCE_READY','PROD_RESTART_PENDING','05_E_RUNTIME/E_RUNTIME_VERDICT.md','User normal close of the old service, then normal attested product start and actual production DOM verification; no force kill.'),
    ]
    gates=[]
    for work,engineering,formal,evidence,next_action in states:
        p=OUT/evidence
        if not p.is_file():raise ValueError('WORK_PACKAGE_EVIDENCE_MISSING:'+work)
        gates.append(dict(work=work,engineering=engineering,formal_gate=formal,evidence=ref(p),next_action=next_action,
            dimensions=dict(FORMULA_LOGIC='PASS_SCOPED',DATED_INPUT='PASS_SCOPED' if work=='E_RUNTIME' else 'SOURCE_NOT_PRESENT',FORMAL_OWNER='NOT_AUTHORIZED',API_UI_BINDING='NOT_TESTED' if work=='E_RUNTIME' else 'SOURCE_NOT_PRESENT',HISTORICAL_AS_RECORDED_PIT='UNKNOWN',FUTURE_MATURED_OUTCOME='SOURCE_NOT_PRESENT'),
            dimension_scope='Formal missing capability only; available current Native fields have separate package field matrices',
            T0='2026-10-09',first_available=None,membership_version='TDX_LATEST_MEMBER_RETRO_V1',
            consumer={'A_AMOUNT':'sector Amount A strict consumer','B_SECTOR':'/api/v4/sectors maturity/health','C_COHORT':'/api/v4/forward/statistics','D_FEP':'/api/v4/forward/fep','E_RUNTIME':'28765 six product entrances'}[work],
            window={'A_AMOUNT':'2026-09-01 through 2026-09-30 H21','B_SECTOR':'T0 and exact prior official session frozen episode','C_COHORT':'T0 freeze then T+1/T+3/T+5 official sessions','D_FEP':'model selection cutoff and prediction deadline','E_RUNTIME':'accepted 2026-10-09 read domain'}[work]))
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    ledger=dict(contract_id='V4-R4-CURRENT-SNAPSHOT-FORMAL-GATES-20261010',RESULT_CODE_SHA=sha,
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),gates=gates,
        historical_PIT='STRICT_HISTORY_NOT_VERIFIABLE_WITH_AVAILABLE_ORIGINALS',next_day='WAIT_REAL_SESSION',
        protected=protected,external_acceptance='EXTERNAL_ACCEPTANCE_BLOCKED',external_recheck='EXTERNAL_RECHECK_REQUESTED',
        scope_completion='ENGINEERING_SCOPE_COMPLETE_WITH_DECLARED_FORMAL_GATES',production_activation=False)
    write('07_GATES_LEDGER.json',ledger)
    write('CROSS_CUTTING_AUDIT_ITEMS.json',dict(items=[dict(id='M10-AMOUNT-A/R4',scope='Formal H21 as-recorded inputs, economic source equivalence and per-consumer authority',status='OPEN_INDEPENDENT_AUDIT',evidence=ref(OUT/'01_A_AMOUNT/A_FIX_AND_VERDICT.md'),acceptance='Actual original input lineage and formal consumer authority; representation fitting alone is insufficient'),dict(id='FP13-FP14/R4',scope='Independent production runtime/browser/full release acceptance',status='OPEN_INDEPENDENT_AUDIT',evidence=ref(OUT/'05_E_RUNTIME/E_RUNTIME_VERDICT.md'),acceptance='Live normal restart, original DOM/source linkage and independent release acceptance')]))
    write('NEXT_REAL_DAY_INTERFACE.md','# Next actual session interface\n\nUse the existing DD R2.2 contract and scripts/audit_dd_r22_data_first.py for a read-only preflight after actual sources are available. Its source/owner QA/CAS/API chain remains the daily job authority. No 10/12 data, receipt, prediction, outcome or enrollment has been generated by R4. Preserve last-good on any failure. New genuine captures only improve future H21/PIT windows; they cannot validate the 20 missing historical captures. No recurring automation or settings change is created by R4.\n')
    write('00_MASTER_RESULT_R4.md',f'''# R4 当前快照修复交付（2026-10-10）

本轮工程范围状态：ENGINEERING_SCOPE_COMPLETE_WITH_DECLARED_FORMAL_GATES。全正式准入仍为 EXTERNAL_ACCEPTANCE_BLOCKED；只申请 EXTERNAL_RECHECK_REQUESTED，不自签外审。代码提交：{sha}。精确各包代码、源字节与测试以manifest及包内收据为准。

| 包 | 本轮工程结果 | 独立保留的门 |
|---|---|---|
| A Amount | 原历史观测/归档只读追溯、日历重算、消费者金额核对；缺观测数量/覆盖率修为null | H21仍缺20日原始成员首获；经济等价与正式消费者权限未证明 |
| B Sector | 六字段版本化契约、隔离提取/Episode候选、400板块守恒与独立oracle、负例 | 正式CONFIRMED/WARM/冻结前态/due/scenario与Owner未准入；不发布成熟度 |
| C Cohort | 可信Head/grant/Owner/source SHA接线、语义负例、不可覆盖隔离publisher、原settlement日历复用 | 2290条实际结构事件不证明合法历史enrollment；真实分母未知 |
| D FEP | 3历史工程模型、615历史预测和Shadow授权盘点；六类中文禁入原因；冻结预测时钟不可改写 | 既有工程/Shadow产物不自动获得当前生产模型或评分权限 |
| E runtime | 真实PID/旧服务10路HTTP、当前代码隔离10路、正常启动模块取证入口 | 28765仍为旧进程，无安全停止接口；PROD_RESTART_PENDING；双尺寸DOM及生产故障恢复NOT_TESTED |

集成测试85项通过；C包另有43项最终准入定点测试与109项原Forward/settlement回归通过（与集成有重叠，不合计为独立样本总数）。D新增14项通过；扩大历史E5套件22项被隔离DB门拒绝setup，未声称数据库回归通过。A/B源级及边界计数见各自独立结果。

三个既有R3小包CRC/逐文件SHA已核；LOO固定种子抽样139组合/1112比较、两个真实pulse240比較均零差异。这是开发机stdlib独立公式重放，不能替代外部审计人独立执行。没有重建未变全量旧历史。

运营Head保持55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e，严格PIT Head保持38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40；AUTO=true/revision5与10/09旧日收据保持原值。TDX只读、无新能力激活、无真实FEP预测、无10/12数据或未来结果、无Windows运维改造。

浏览器限制实录：IAB本机地址ERR_BLOCKED_BY_CLIENT；Chrome不可用。HTTP或手写摘录未冒充原始DOM。正常启动入口为scripts/start_product_attested_r4.py，仅在旧服务正常退出后运行；占用端口实测拒绝，无进程被停止。E门等待实际可执行的正常关闭和浏览器工具，不阻塞本輪其他工程交付。

历史来源搜索结论仅覆盖A_SEARCH_MANIFEST列明的真实本机/归档/收据位置及Drive受限目录读取，不声称全世界不存在原件。出现真实原件或正式授权前各门保持关闭。Drive写入与字节回读结果另见09_DRIVE_READBACK_RECEIPT.json；回读收据在报告/小包之后追加，未包含于先生成归档。
''')
    files=[ref(p) for p in OUT.rglob('*') if p.is_file() and p.name not in ('08_EVIDENCE_MANIFEST_SHA256.json','09_DRIVE_READBACK_RECEIPT.json')]
    sources=[ref(ROOT/p) for p in subprocess.check_output(['git','diff','--name-only','6b6d5cbd2b115335918aeeafcec9ae5a46f9eb99'],cwd=ROOT,text=True).splitlines() if p.startswith(('src/','tests/','scripts/')) and (ROOT/p).is_file()]
    write('08_EVIDENCE_MANIFEST_SHA256.json',dict(contract='R4_ATOMIC_EVIDENCE_SEAL_V1',files=files,sources=sources,excluded=['self_manifest','subsequent_cloud_readback_receipt'],protected=protected))

if __name__=='__main__':main()
