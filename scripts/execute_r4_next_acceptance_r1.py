"""Bounded read-only recheck and versioned R4 evidence; no production promotion."""
from pathlib import Path
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from replay_r4_post_audit_runtime import read, ROUTES
OUT=ROOT/'docs/evidence/v4_r4_post_audit_repair_20261010/13_NEXT_ACCEPTANCE'
PREV=OUT.parent
def ref(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def put(name,value):atomic_json(ROOT,OUT/name,value)
def compact(value):
    if isinstance(value,list):return [compact(x) for x in value[:2]]
    if not isinstance(value,dict):return value
    keys={'status','reason','code','value','quality','unit','source_digest','source_as_of',
          'trade_date','accepted_trade_date','context_token','contract_id','total','limit','offset','has_next',
          'symbol','entity_id','security_id','display_name','AS_RECORDED','PIT_ELIGIBLE','knowledge_lineage',
          'observed_count','matured_count','production_authorized','write_authorized','production_write_authorized',
          'production_status','errors','state','event','final_state','state_status','denominator','amount','close',
          'raw_close','total_amount','currency','count','source','data','items','context','counts','gap',
          'fields','market','indices','axes','breadth','turnover','amount_cny','advance','decline','unchanged',
          'admission_gate','authority','capabilities','return_expectancy','downside_risk','return_quantiles',
          'prediction_revision','model_display','priority_use'}
    if 'fields' in value:
        value=dict(value,fields={k:v for k,v in value['fields'].items() if k in ('close','amount','volume','final_state','state','research_state','dq5','q20','amount_ratio20')})
    return {k:compact(v) for k,v in value.items() if k in keys}
def md(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp');tmp.write_text(value,encoding='utf8');os.replace(tmp,p)
def entry():
    contracts=[ref(ROOT/'docs/evidence'/p) for p in (
        'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md',
        'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md')]
    heads=[ref(ROOT/'data/v4'/p) for p in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json')]
    put('STAGE_CONTRACT.json',dict(contract_id='V4_R4_NEXT_ACCEPTANCE_R1_20261010',
        base_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        recorded_at=datetime.now(timezone.utc).isoformat(),T0='2026-10-09',contracts=contracts,
        protected_heads=heads,acceptance='ENTRY_FROZEN',
        stages=['E scoped read-only differential','D status correction and isolated SQL','B formal producer decision','C admission counterexamples','FINAL versioned reconciliation'],
        next_stage='Bounded engineering evidence then independent external recheck; no automatic formal release'))
def runtime():
    ctx=json.loads(read('context')['response_body']);token=ctx['context_token']
    records=[]
    for route in ROUTES+('market/breadth','market/axes','forward'):
        for mode,value in [('empty',''),('old','38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40'),('current',token)]:
            r=read(route,dict(context_token=value,limit=2,trade_date='2026-10-09'))
            payload=json.loads(r.pop('response_body'));r.update(route=route,mode=mode,payload=compact(payload))
            assert r['http_status']==(200 if mode=='current' else 409),(route,mode,r['http_status'])
            records.append(r)
    for query in [dict(q='688349',trade_date='2026-09-30'),dict(q='301628',trade_date='2026-10-09'),dict(q='688349',trade_date='2026-10-09'),dict(limit=2,offset=2,trade_date='2026-10-09')]:
        r=read('stocks',dict(context_token=token,**query));r['payload']=compact(json.loads(r.pop('response_body')));records.append(r)
    att=json.loads((ROOT/'runtime/r4_product_loaded_modules.json').read_bytes())
    process=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',f"Get-CimInstance Win32_Process -Filter 'ProcessId={att['pid']}' | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress"],text=True))
    modules=[dict(module=m['module'],startup_sha=m['source_sha256'],current_sha=hashlib.sha256(Path(m['runtime_module_path']).read_bytes()).hexdigest()) for m in att['modules']]
    put('E_CURRENT_PROCESS_READBACK.json',dict(captured_at=datetime.now(timezone.utc).isoformat(),
        current_code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        process=process,attestation=att,modules=modules,records=records,
        protected_heads=[ref(ROOT/'data/v4'/p) for p in att['protected_heads']],
        restart_performed=False,interpretation='Startup loaded bytecode inherited. D R2 disk correction is not loaded by this unchanged process; no runtime hot reload or restart claimed.'))
    print('E bounded live token/API readback passed',flush=True)
def compact_existing():
    p=OUT/'E_CURRENT_PROCESS_READBACK.json';a=json.loads(p.read_bytes())
    for r in a['records']:r['payload']=compact(r['payload'])
    put(p.name,a)
def db_receipts():
    import psycopg
    sys.path.insert(0,str(ROOT/'tests/fep_e5'))
    from test_canonical_authority_read import seed,complete_rows,REQUEST,AT
    from workbench_analysis.fep_e5.trusted_authority import read_canonical_candidate,resolve_current_sources
    records=[]
    with psycopg.connect('host=127.0.0.1 port=55547 user=postgres dbname=fep_authority_isolated',autocommit=True) as pg:
        directory=Path(pg.execute('show data_directory').fetchone()[0]).resolve()
        assert directory==Path('G:/codex_tmp/test_temp/r4_next_authority_20261010/data').resolve()
        for case in ('complete_engineering','expired_grant','missing_prediction'):
            pg.execute('drop schema if exists fep cascade');pg.execute('create schema fep')
            data=complete_rows();request=dict(REQUEST,prediction_id='P')
            if case=='expired_grant':data['permission_keys'][0]['expires_at']=AT
            if case=='missing_prediction':request.pop('prediction_id')
            seed(pg,data);r=read_canonical_candidate(pg,request,at=AT)
            records.append(dict(case=case,result=r))
    put('D_REAL_SQL_SUCCESS_FAILURE_READBACK.json',dict(scope='Actual isolated SQL with synthetic rows, no formal Owner or authority',records=records))
    actual=resolve_current_sources(ROOT)
    put('D_EXACT_TRUSTED_PRODUCTION_REQUIREMENTS.json',dict(contract_id='FEP_CANONICAL_AUTHORITY_READ_R2',
        T0='2026-10-09',production_authorized=False,actual_source_discovery=actual,
        required_before_consumer_start=[
            'Independently admitted canonical production DB Owner and read-only connection, never default DSN',
            'Exact scope_id,target_id,horizon,feature_contract_id,model_set_id,model_revision,capability',
            'Immutable model registry revision/digest and accepted CHAMPION model-set membership',
            'Current ALLOW activation, exact grant/Head identity, version CAS receipt and prior activation',
            'Original valid_from/expires_at grant window containing consumer cutoff; engineering_only is insufficient',
            'Independent current capability approval Owner, not caller bool/dict or engineering CAS',
            'Exact prediction_id, immutable output digest, accepted prediction run/snapshot/publication lineage',
            'PIT_OBSERVED PRODUCTION first-asof dependencies with source Owner/SHA/first availability before cutoff',
            'Actual FIT labels mature and revision available before fit_started_at, all six typed READY fields'],
        status='SOURCE_NOT_PRESENT',next_stage='Independent original-source admission; no model or grant manufactured'))
def finish():
    import shutil,xml.etree.ElementTree as ET
    for source,target in [('G:/codex_tmp/r4_next_d_registered.xml','D_NEGATIVE_CANDIDATE_JUNIT.xml'),('G:/codex_tmp/r4_next_c.xml','C_ADMISSION_JUNIT.xml'),('G:/codex_tmp/r4_next_de.xml','DE_CONSUMER_REGRESSION_JUNIT.xml')]:
        raw=Path(source).read_bytes();p=OUT/target;tmp=p.with_suffix('.tmp');tmp.write_bytes(raw);os.replace(tmp,p)
        suite=ET.fromstring(raw).find('testsuite');assert suite is not None
        assert all(suite.get(k,'0')=='0' for k in ('failures','errors','skipped'))
    original_path=PREV/'07_SCOPE_GATE_MATRIX.json'
    historical=OUT/'07_SCOPE_GATE_MATRIX_R1_ORIGINAL.json'
    original_bytes=historical.read_bytes() if historical.exists() else original_path.read_bytes()
    old=json.loads(original_bytes)
    if not historical.exists():
        tmp=historical.with_suffix('.tmp');tmp.write_bytes(original_bytes);os.replace(tmp,historical)
    for source,target in [('G:/codex_tmp/r4_next_d.xml','D_INITIAL_UNREGISTERED_CLUSTER_JUNIT.xml'),
                          (ROOT/'reports/r4_next_acceptance_20261010/ISOLATED_CLUSTER_MANIFEST.json','ISOLATED_CLUSTER_MANIFEST.json')]:
        p=OUT/target;tmp=p.with_suffix('.tmp');tmp.write_bytes(Path(source).read_bytes());os.replace(tmp,p)
    for name in ('V4_R4_NEXT_ACCEPTANCE_GATES_TASK_R1_20261010.md','V4_R4_POST_AUDIT_EXTERNAL_RECHECK_R2_20261010.md'):
        p=OUT/name;tmp=p.with_suffix('.tmp');tmp.write_bytes((Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes());os.replace(tmp,p)
    entry=json.loads((OUT/'STAGE_CONTRACT.json').read_bytes())
    for head in entry['protected_heads']:assert ref(ROOT/head['path'])==head
    b=json.loads((PREV/'12_BCD_DEVELOPMENT/03_B/B_CURRENT_SOURCE_AND_ENGINEERING_BOUNDARIES.json').read_bytes())
    source_refs=[b[k] for k in ('operational_head_binding','current_native_owner','current_core_owner','accepted_legacy_observation_binding')]
    for source in source_refs:assert ref(ROOT/source['path'])==source
    put('B_CURRENT_SOURCE_BYTE_READBACK.json',dict(T0='2026-10-09',sources=source_refs,
        verdict='SOURCE_BYTES_UNCHANGED_FROM_EXTERNAL_RECHECK_R2',formal_admission=False,
        fields=b['blocked_production_fields']))
    md('B_FORMAL_PRODUCER_ADMISSION_DECISION.md', '''# 板块正式 Producer 入场决策 R1

T0=2026-10-09。真实 Native、Core、运营 Head、9/24 legacy 原件字节 SHA 已在 B_CURRENT_SOURCE_BYTE_READBACK.json 回读；本轮无新正式原件。

| 六字段 | Producer / 必须原件 | 10/09 首获与 accepted binding | 窗口/成员版本 | 当前决策 |
|---|---|---|---|---|
| CONFIRMED | exact legacy valid-member publication + 冻结 AST | SOURCE_NOT_PRESENT | 当日 legacy 成员、观察截止、AST 版本 | BLOCKED |
| WARM | q20/dq5_3 rank + SETUP/RECOVERY 原 publication | SOURCE_NOT_PRESENT | 原排名窗口、成员版本；Amount 分支独立 H21 门 | BLOCKED |
| frozen_invalidation | 原始 prior SECTOR Episode 创建冻结 Owner | SOURCE_NOT_PRESENT | 创建时成员集与首次可用 | BLOCKED |
| episode_invalidation_contract_id | 原 Episode 合同 ID/version/SHA | SOURCE_NOT_PRESENT | 创建冻结版本，不用当前配置替代 | BLOCKED |
| followup_complete | 原 due_plan + 已成熟 settlement Owner | SOURCE_NOT_PRESENT | 冻结市场会话与真实到期 source | BLOCKED |
| scenario | 正式 confirmation/scenario + 原 priority publication | SOURCE_NOT_PRESENT | 当时成员版本、first_available、prior state | BLOCKED |

A05 只接受 2026-09-24 原证据；10/09 仍 A05_CURRENT_SNAPSHOT_TARGET_NOT_ACCEPTED。9/24 TRUE/FALSE/UNKNOWN 金样本只为诊断候选。

合法新原件路径：由获准正式 Producer 在真实新 T0 从只读源生成完整观察、原始窗口/成员清单、first_available、cutoff、source SHA 和合同版本；在 G 盘以不可变 publication 发布。独立审查当日 source/Owner 合同、Head binding、AST 黄金输入覆盖、Episode 前驱、能力 grant，之后才可通过 prepare_entry 输入六个逐字段 SHA 绑定 receipt。候选字节校验不替代 SECTOR_D2_FORMAL_OWNER_PASS。不得扩写9/24授权日期或改 as-recorded 标签。

Native 非 H21 事实继续按既有获准显示。正式 reducer 与消费者保持关闭；下一阶段为真实原件及独立准入审查。
''')
    md('C_REAL_T0_CAPTURE_ADMISSION_CHECKLIST.md', '''# Cohort 真实 T0 入场接口 R1

真实10/09 Head无 State cohort_signals Producer、独立 Validation Cohort Owner和 separate write grant；observed_count=null、production_write_authorized=false。八项实际 Head/原字节负例与接口回归见 C_ADMISSION_JUNIT.xml（81项，范围重叠不相加为独立样本）。使用原 Head 字节的伪 manifest 负例明确属于隔离反例，绝不表示正式新源。

1. 获准正式 State Producer 必须发布所有 eligible/ineligible 信号与明确资格及不合格原因；Focus Top-K 不可作样本源。
2. 原 Owner/manifest SHA、真实上海新 T0、first_available<=accepted_at<=实际 capture clock<=deadline；T0之前/之后首次捕获拒绝，冻结字段必须在 cutoff 可见。
3. freeze_source_candidate 同 publication/revision 原字节只冻一次；篡改/同revision覆盖拒绝。合法新revision仍需原出版和独立批准，不能借revision补旧事件。
4. extract_candidate 要求候选 Head 的 owners[T0].state 等于真实 Producer source_owner；ledger必须完整且去重，原资格/窗口/成员版本冻结。
5. prepare_capture 分别检查独立 Owner、完整 source receipt和 PREPARE_FIRST_CAPTURE write grant 的绑定/时效；READ_STATISTICS 不能代写，write grant不能代读。
6. DD候选能力失败只影响Cohort，不阻塞既有RAW/市场/股票派生；现有接口回归验证这一点。独立Owner准入、DD R2.2 CAS之后才可能正式入组。

旧2290事件永不回填。本轮没有新正式首获原件，也不模拟10/12宣称上线；工程包到此结束，下一阶段仅在真实新T0原件及独立准入存在时进入。
''')
    md('D_STATUS_CONTRACT_CORRECTION.md', '''# FEP 候选状态合同订正 R2

修复P2：errors非空不再返回 CANONICAL_AUTHORITY_CANDIDATE_VERIFIED。contract_id升级 FEP_CANONICAL_AUTHORITY_READ_R2。

- db_facts_status=DB_FACTS_READ_VERIFIED 仅表示只读 repeatable-read 查询完整结束。
- status=CANDIDATE_INCOMPLETE 表示源、身份、授权窗口、预测、成熟标签或schema有缺口；candidate_complete=false。
- 仅余独立approval/engineering CAS问题时 status=FORMAL_APPROVAL_MISSING，仍 candidate_complete=false。
- 缺valid_from/expires_at明确 GRANT_VALIDITY_WINDOW_SOURCE_MISSING，过期 GRANT_TIME_INVALID；不修改业务模型或写accepted Head。
- production_authorized恒false；完整typed工程预测可保留 READY_ENGINEERING_EVIDENCE_ONLY，但不能供生产显示/排序授权。

实际隔离PostgreSQL31项零失败/跳过。首次未登记cluster被隔离保护拒绝（1通过、30 setup错误），登记G盘exact cluster manifest后31通过；保护始终启用，数据库已停止。D_REAL_SQL_SUCCESS_FAILURE_READBACK.json保存完整工程正向与expired/missing prediction真实SQL负向返回；这些是合成行的真实查询，不是正式生产源。

真实消费者前置与实际缺源详见 D_EXACT_TRUSTED_PRODUCTION_REQUIREMENTS.json。当前28765仍加载R1；本修复为离线DB候选入口R2，未声称该进程加载新代码。下一阶段：独立可信原件/能力审批及受控加载审查；生产预测保持BLOCKED。
''')
    md('E_FP13_INDEPENDENT_RECHECK_MATRIX.md', '''# FP13 独立复验申请矩阵

开发方本机只读复验，申请 FP13_SCOPED_BROWSER_EXTERNAL_RECHECK；不自签外审。

真实28765 PID51368、命令/启动时刻/模块startup bytecode、当前磁盘SHA与两个Head见 E_CURRENT_PROCESS_READBACK.json。1c47f6ca→336827bf无src/scripts/config/tests差异；本轮仅D reader R2改变已加载模块的磁盘源，进程仍R1，未重启。E UI/BFF核心代码保持原字节。

真实token空/旧/当前分别409/409/200；六入口与forward、breadth等实时响应SHA/量纲见回读。200+SOURCE_INCOMPLETE计缺源，不能算指标可用。688349/9/30 close=13.240 CNY，10/09使用当前上下文；301628 INVALIDATED、Focus、六导航、搜索返回与两个尺寸差异抽查见browser/E_DIFFERENTIAL_BROWSER_RECEIPT.json。

两个尺寸1366×768、1920×1080实际受控breadth拦截一次503，局部重试按钮点击恢复，其余section原DOM一致、T0保留；见browser/E_BREADTH_503_BROWSER_RECEIPT.json。server_fault=false，绝不称真实服务器宕机。

旧完整浏览器覆盖按原收据继承，当前差异抽查不扩展为FP14正式授权；FP14_FULL_RELEASE=EXTERNAL_ACCEPTANCE_BLOCKED。
''')
    gates=dict(PROD_CODE_LOADED='PASS_SCOPED_INHERITED_E_RUNTIME_R1; D_R2_DISK_ONLY',
        PROD_API_SCOPED='PASS_SCOPED; SOURCE_INCOMPLETE_IS_NOT_READY',
        FP13_BROWSER_SCOPED='CONTROLLED_BROWSER_503_ISOLATION_RECOVERY_PASS; EXTERNAL_RECHECK_REQUESTED',
        FP14_FULL_RELEASE='EXTERNAL_ACCEPTANCE_BLOCKED',SECTOR_D2_FORMAL='BLOCKED_SOURCE_NOT_PRESENT',
        COHORT_REAL_ENROLLMENT='BLOCKED_SOURCE_AND_WRITE_GRANT_MISSING',FEP_PRODUCTION_AUTHORIZED=False,
        H21_STRICT='H21_STRICT_HISTORY_NOT_VERIFIABLE')
    put('07_SCOPE_GATE_MATRIX_R2_APPEND.json',dict(contract_id='R4_SCOPE_GATE_RECONCILIATION_R2',
        effective_at=datetime.now(timezone.utc).isoformat(),evidence_base_sha=entry['base_sha'],
        historical_original=ref(historical),historical_stage_E=old['stages']['E'],
        supersedes_current_interpretation=['07_SCOPE_GATE_MATRIX.json:stages.E.acceptance FP13_FAULT_RECOVERY_OPEN'],
        current_stages_E_acceptance='PRODUCTION_API_AND_BROWSER_PASS_SCOPED; CONTROLLED_BROWSER_503_ISOLATION_RECOVERY_PASS; EXTERNAL_RECHECK_REQUESTED',
        startup_contract=dict(binding=ref(PREV/'12_BCD_DEVELOPMENT/STAGE_CONTRACT.json'),role='ENTRY_FREEZE_ONLY_NOT_CURRENT_ACCEPTANCE',original_acceptance='IN_PROGRESS'),
        evidence=[ref(OUT/'browser/E_BREADTH_503_BROWSER_RECEIPT.json'),ref(OUT/'E_CURRENT_PROCESS_READBACK.json')],
        gates=gates,protected_heads=entry['protected_heads'],T0='2026-10-09',
        engineering_acceptance='ENGINEERING_SCOPE_COMPLETE_WITH_DECLARED_FORMAL_GATES',
        formal_acceptance='EXTERNAL_ACCEPTANCE_BLOCKED',next_stage='Independent FP13 scoped recheck and original formal source admission; FP14 separate authorization'))
    revision=ref(OUT/'07_SCOPE_GATE_MATRIX_R2_APPEND.json')
    old['status_revisions']=[dict(version='R2',binding=revision,
        supersedes='stages.E.acceptance historical FP13_FAULT_RECOVERY_OPEN',historical_original=ref(historical))]
    old['effective_current_revision']=revision
    old['stages']['E']['historical_acceptance']=old['stages']['E']['acceptance']
    old['stages']['E']['acceptance']='PRODUCTION_API_AND_BROWSER_PASS_SCOPED; CONTROLLED_BROWSER_503_ISOLATION_RECOVERY_PASS; EXTERNAL_RECHECK_REQUESTED'
    atomic_json(ROOT,original_path,old)
    put('CROSS_CUTTING_AUDIT_ITEMS_R2.json',dict(items=[
        dict(id='P2_FEP_CANDIDATE_STATUS_SEMANTICS',scope='Canonical DB reader only; old P0 not reopened',evidence='D_NEGATIVE_CANDIDATE_JUNIT.xml',acceptance='ENGINEERING_FIXED_SCOPED'),
        dict(id='P2_EVIDENCE_STATUS_RECONCILIATION',scope='R4 current ledger versus historical entry snapshots',evidence='07_SCOPE_GATE_MATRIX_R2_APPEND.json',acceptance='VERSIONED_APPEND_COMPLETE'),
        dict(id='AMOUNT_A_H21_HISTORY',scope='Historical20 first-capture member observation gaps; independent of D/E',evidence='../05_A_AMOUNT',acceptance='H21_STRICT_HISTORY_NOT_VERIFIABLE')]))
    md('V4_R4_NEXT_ACCEPTANCE_RESULT_20261010.md', '''# R4 本轮修复结果

ENGINEERING_SCOPE_COMPLETE_WITH_DECLARED_FORMAL_GATES。全V4仍 EXTERNAL_ACCEPTANCE_BLOCKED。申请 FP13_SCOPED_BROWSER_EXTERNAL_RECHECK；未签EXTERNAL_ACCEPTANCE_PASS。

FEP候选错误状态已修，R2区分DB事实与候选/正式批准缺口，production_authorized恒false；实际隔离SQL31项通过。C实际Head负例与接口回归81项通过。两个尺寸受控browser503局部失败/重试恢复通过；六入口差异抽查见独立矩阵与收据。

板块六正式Producer、Cohort真实首获/独立write grant、FEP正式model/approval/as-recorded成熟预测原件仍SOURCE_NOT_PRESENT，给出了逐字段与逐消费者精确前置。没有造源、授权或回填旧2290事件。Amount历史20日缺口保留原终局，未重复扫描与比例计算。

07_SCOPE_GATE_MATRIX_R2_APPEND.json以版本化覆盖关系消除旧E账本冲突，并把12_BCD_DEVELOPMENT/STAGE_CONTRACT的IN_PROGRESS解释为开工冻结；保留历史原始文件和判定。八个能力门分开列示。

T0=2026-10-09；两个受保护Head原字节未改变。28765未重启，仍R1启动身份；D修复为磁盘及隔离SQL验证，尚未加载到该进程。Git/Drive交付最终回读见DELIVERY_READBACK.json，不把推送当外部验收或下一阶段授权。
''')
    files=[ref(p) for p in OUT.rglob('*') if p.is_file() and p.name not in ('SHA256_MANIFEST.json','DELIVERY_READBACK.json')]
    files += [ref(original_path)]
    files += [ref(ROOT/p) for p in ('src/workbench_analysis/fep_e5/trusted_authority.py','tests/fep_e5/test_canonical_authority_read.py','tests/test_r4_next_real_source_admission.py','scripts/execute_r4_next_acceptance_r1.py','scripts/recheck_r4_next_browser.cjs')]
    put('SHA256_MANIFEST.json',dict(files=files,output_scope='Actual bytes at engineering closeout'))
    import zipfile
    with zipfile.ZipFile('G:/codex_tmp/V4_R4_NEXT_ACCEPTANCE_LIGHT_20261010.zip','w',zipfile.ZIP_DEFLATED) as z:
        for r in files:
            p=ROOT/r['path'];z.write(p,p.relative_to(ROOT).as_posix())
        z.write(OUT/'SHA256_MANIFEST.json',(OUT/'SHA256_MANIFEST.json').relative_to(ROOT).as_posix())
    print('Versioned closeout and light pack written',flush=True)
if __name__=='__main__':
    for k in ('TMP','TEMP','TMPDIR'):os.environ[k]='G:/codex_tmp'
    globals()[sys.argv[1]]()
