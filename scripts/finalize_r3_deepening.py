"""Append reviewable current-scope dispositions without replacing historical acceptance."""
from immediate_r3_common import *
from deepen_r3_lineage import symbol
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime,timezone
D=OUT/'11_DEEPENING'
def main():
    h=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=h['accepted_trade_date'];stage=load(D/'STAGE_CONTRACT.json')
    for ref in stage['protected_heads']:checked(ref)
    t=load(OUT/'05_P1_COHORT/P1_FORWARD_FREEZE_AND_MATURITY_TESTS.json');assert t['exit_code']==0
    qa=load(OUT/'06_P1_PRODUCT_QA/P1_PRODUCT_FP_REGRESSION_MATRIX.json');assert not qa['failures']
    contract=load(D/'SECTOR_FORMAL_EXTRACTION_PROPOSAL.json');cohort=load(D/'COHORT_FIELD_CAPABILITY_MATRIX.json')
    missing=[]
    for field,gap in contract['admission_gaps'].items():
        missing.append((field,'P0-OWNER',contract['producer_bindings'],gap,'CONTRACT_GAP','/api/v4/sectors/INDUSTRY:T0706','板块画像 maturity/health，保留 SOURCE_INCOMPLETE','Versioned accepted extraction/episode entry and exact upstream payload',binding(D/'SECTOR_FORMAL_EXTRACTION_PROPOSAL.json')))
    for row in cohort['fields']:
        missing.append((row['field'],'P1-COHORT',[row['producer']],row['rule'],'AUTHORITY' if row['output_domain']=='FEP' else 'INPUT_MISSING',row['route'],'focus.js Cohort/settlement/FEP separate blocks',row['input_owner_required'],binding(D/'COHORT_FIELD_CAPABILITY_MATRIX.json')))
    missing.append(('formal_Amount_A_h21','P0-AMOUNT',[symbol('src/workbench_analysis/amount_a_go_forward_r3.py','compute_ledger_candidate')],None,'INPUT_MISSING',None,'Amount A production consumer disabled','20 exact missing dated membership observations; accepted full source/consumer gate',binding(D/'PIT_ORIGINAL_INGEST_AND_MISSING_DAYS.json')))
    matrix=load(D/'EXACT_FIELD_SOURCE_CONSUMER_MATRIX.json')['fields']
    for field,stage_name,producer,algorithm,layer,route,component,next_action,evidence in missing:
        matrix.append(dict(issue_id='R3-DEEP-MISSING-'+field,stage=stage_name,producer_code=producer,algorithm_version=algorithm,
          exact_input_owner=None,trade_date=day,first_available_at=None,member_asof=None,PIT_scope='SOURCE_NOT_PRESENT_NO_AS_RECORDED_CLAIM',window_identity='T0/H21/T-1 as explicitly specified in bound field contract',adjustment=None,unit=None,null_policy='UNKNOWN_NOT_ZERO',
          output_owner=None,expected_field=field,actual_field=None,BFF_route=route,UI_component=component,discrepancy='Exact accepted input/contract absent; producer code does not grant accepted owner',responsible_layer=layer,current_verdict='SOURCE_NOT_PRESENT' if layer=='INPUT_MISSING' else 'FORMAL_ACCEPTANCE_PENDING',evidence_path=evidence,code_sha=stage['BASE_SHA'],owner_sha=None,next_action=next_action,
          six_dimensions=dict(FORMULA_OR_LOGIC='IMPLEMENTED_SCOPED_OR_EXACT_PROPOSAL',CURRENT_DATA='SOURCE_NOT_PRESENT',API_BINDING='NOT_READY_CURRENT_DATA; FAIL_CLOSED_BOUNDARY_VERIFIED',UI_BEHAVIOR='UNKNOWN_DISPLAY_VERIFIED',HISTORICAL_PIT='NOT_VERIFIABLE',FUTURE_OUTCOME='NOT_OBSERVED')))
    write(D/'UNIFIED_FIELD_ISSUE_MATRIX.json',dict(fields=matrix,code_sha_role='BASE with exact working source hashes in bindings; result commit follows',no_generic_SEE_placeholders=True))
    observed={}
    try:
        with urlopen('http://127.0.0.1:28765/api/v4/context',timeout=10) as r:prod=json.load(r)
        query=__import__('urllib.parse',fromlist=['urlencode']).urlencode(dict(context_token=prod['context_token'],trade_date=prod['context']['trade_date']))
        identity=load(load(h['membership_snapshot'])['identity_source']);target=next(r['security_id'] for r in identity['rows'] if r.get('source_security_key')=='SZ.301628')
        with urlopen('http://127.0.0.1:28765/api/v4/stocks/'+target+'/profile?'+query,timeout=30) as r:profile=json.load(r)
        observed=dict(production_port=28765,competitive_hypotheses_loaded='competitive_hypotheses' in profile,status='ALREADY_LOADED' if 'competitive_hypotheses' in profile else 'PROD_RESTART_PENDING',no_service_mutation=True)
    except HTTPError as e:observed=dict(status='PROD_RESTART_PENDING',reason='REQUESTED_CURRENT_PRODUCT_ROUTE_NOT_READY',http_status=e.code,response_excerpt=e.read(3000).decode('utf8',errors='replace'),production_port=28765,no_service_mutation=True)
    except Exception as e:observed=dict(status='PROD_RUNTIME_NOT_VERIFIED',reason=type(e).__name__,production_port=28765,no_service_mutation=True)
    write(D/'PRODUCTION_LOADING_AND_HEAD_PROTECTION.json',dict(production=observed,QA_port=28767,protected=[binding(ref) for ref in stage['protected_heads']],accepted_head_changed=False))
    browser=dict(classification='ACTUAL_CUA_DOM_EXCERPTS_MANUALLY_TRANSCRIBED_NOT_FULL_SNAPSHOTS',QA_port=28767,proxy_port=28768,
      six_entries=[dict(entry=name,viewports=['1920x1080','1366x768'],excerpt=excerpt) for name,excerpt in [
      ('今日总览','符合 366 / 展示 30；去重净变化 457 · 无变化持续记录 645'),('板块研究','板块研究；行业/概念列表；来源能力不足；400-sector API pagination independently bound'),('个股研究','三一重能 SH.688349 13.590 启动确认 符合'),('关注跟踪','Focus 独立关注清单；共 2805 条 · 第 1 页'),('市场与事件','分母 5224 · 实际行情 5210 · 通达信成交额 19003.65 亿元；涨停72 跌停11 停牌14 不可判定11'),('数据与诊断','R43:2026-10-09 5210 重建研究；共1条 第1页')]],
      actual_scenarios=[dict(case='parent_filter_roundtrip_after_member_page_and_reload',url='/v4/research/sectors?trade_date=2026-10-09&type=INDUSTRY&offset=0&q=%E7%94%B5%E6%B0%94%E8%AE%BE%E5%A4%87&sort=-sector_rs20',excerpt='电气设备 INDUSTRY:T0706；共 1 条 · 第 1 页；返回链接保留完整 query'),
      dict(case='member_pagination',url='/v4/research/sectors/INDUSTRY%3AT0706?trade_date=2026-10-09&offset=30',excerpt='共 322 条 · 第 2 页'),
      dict(case='unknown_filters',url='maturity=UNKNOWN&health=UNKNOWN',excerpt='电气设备 行业 322 349 27；成熟度/健康度 来源能力不足；共1条'),
      dict(case='historical_688349_after_fix',url='/v4/research/stocks/SEC-00096141BD5420F5CB3120E687CDA5B9?trade_date=2026-09-30&offset=0',excerpt='研究日期2026-09-30 selected；收盘价13.240；图表DATED_HISTORY_INDEX_NOT_BOUND；竞争解释CONSISTENT_PRICE_BASIS 来源不足'),
      dict(case='conditional_competing_explanations',url='/v4/research/stocks/301628',excerpt='结构性趋势延续的解释；短暂反弹或波动、尚未形成持续趋势的解释；分别列反证与下一判别条件；未把后继结果写回'),
      dict(case='breadth503_only',url='/v4/research/market',excerpt='市场宽度与成交额：读取失败，请重试；真实市场指数/合规涨跌停仍可读；清除故障并点重试后恢复5224/5210/19003.65'),
      dict(case='forward_final',url='/v4/research/focus?trade_date=2026-10-09',excerpt='Focus共2805条；NO_AUTHORIZED_COHORT_OWNER；NO_AUTHORIZED_COHORT_SETTLEMENT_OWNER；MODEL_OR_PERMISSION_NOT_READY')],
      semantic_assertions='Checks above actual DOM observations; numerical full-owner comparisons separately in HTTP matrix; unavailable data is not API_BINDING_PASS')
    write(D/'ACTUAL_BROWSER_QA_EXCERPTS.json',browser)
    common='真实只读 QA 服务 127.0.0.1:28767；使用冻结生产 Head，而非生成假 Owner。实际 DOM 摘录见 11_DEEPENING/ACTUAL_BROWSER_QA_EXCERPTS.json；数值与完整集合比对见 P1_PRODUCT_FP_REGRESSION_MATRIX.json。\n\n'
    markdown(OUT/'03_P0_OWNER/P0_OWNER_BROWSER_QA.md','# P0-OWNER 本轮浏览器核验\n\n'+common+'电气设备 source349 / mapped322 / unmapped27 守恒；322成员跨页、行业搜索与排序、UNKNOWN成熟度/健康度过滤、分页刷新后返回原筛选均已核验。API完整比对400板块、322成员和201概念重叠关系；五个真实会话timeline日期相符。原Source rows不删除，26北交所暂缓及001235用户排除单独记账。\n\n板块正式D2仍为 SOURCE_NOT_PRESENT；6个精确输入门及版本化提案见 SECTOR_FORMAL_EXTRACTION_PROPOSAL.json。无法把 B0/Rotation 作为成熟度。浏览器显示正确 UNKNOWN 是 UI_BEHAVIOR_PASS_SCOPED，不是 formal Owner 或 API_BINDING PASS。\n')
    markdown(OUT/'05_P1_COHORT/P1_FORWARD_API_UI_QA.md','# P1-COHORT 最终只读 API/UI\n\n'+common+'逐字段15项定位到准确代码函数和 hash。只读统计可以读取独立 hash/date/contract 绑定的合法 validation_cohort，缺源时 observed_count/matured_count 为 null。当前 Head 无该 Owner，实际页面正确报告 NO_AUTHORIZED_COHORT_OWNER；期限结算独立报告 NO_AUTHORIZED_COHORT_SETTLEMENT_OWNER。Focus2805不替代入组。\n\nFEP读域显式6元 grant key、4个能力 NOT_GRANTED；prediction/model_revision 为null，training/Focus写权限false，Priority V1不改变。页面为 MODEL_OR_PERMISSION_NOT_READY。135项合同/冻结/结算/路径/隔离/缺源/金额测试通过，测试不是合法历史入组、模型注册或正式授权。\n')
    markdown(OUT/'06_P1_PRODUCT_QA/P1_PRODUCT_REAL_BROWSER_QA.md','# P1-PRODUCT 真实浏览器核验\n\n'+common+'六入口各在1920×1080和1366×768完成真实读取；另外核验来源抽屉、板块搜索/排序/UNKNOWN过滤/成员翻页/刷新返回、H两竞争解释、9/30历史画像、宽度503局部隔离及重试恢复。发现并修复 history.replaceState 清空返回上下文的问题；历史画像缺 adjusted Owner 引发的异常已修复，旧日期保留13.240并缺源降级。\n\n23路实际API验证无差异：400板块、322成员、201重叠关系的完整来源比较及6入口数值抽样；负例陈旧token409、未来日期400、非法sort400、负offset400。DOM证据仅声明上述观察，不声称所有表格单元均经过浏览器数值核验。生产运行态另见 PRODUCTION_LOADING_AND_HEAD_PROTECTION.json。\n')
    markdown(D/'AMOUNT_A_DEEP_AUDIT.md','# Amount A 独立审计追加\n\n345条原金额差异已在既有15,981条/3日期审计解释为整元HALF_UP再binary32表示，既有证据继承，不追加为新比较。当前stock金额原始TDX、sector participation_proxy、market总额三字段族分别穿透Owner→实际API；市场总额与5210条行情逐项来源的精确sum相同。proxy不是Amount A。\n\n本轮独立stdlib oracle对14个明确FIXTURE_ONLY正负边界做112项比较，零差异；包括万元/亿元、成员漏项、未知不能填零、停牌零、负数、非有限、冲突和共同成员门。真实严格ledger只包含9/30一个成员观测日，21会话窗口缺20天；378候选均UNKNOWN。真实历史成员不可从今日列表回填。正式Amount A消费者继续禁用，供应商经济口径与正式接纳仍OPEN，不能用fixture通过结案。\n')
    updates=[dict(id='AUDIT-CORE-R2-01',status='PASS_SCOPED_WITH_DECLARED_DOMAIN_GAPS',evidence='153 grouped formula lineage entries; 3 actual five-session cases/15 rows; exact source quality followup separate; inherited full LOO/pulse proofs preserved',next_action='Review unaccepted full LOO rank/episode publication and exact missing detector upstream payload; no re-run unchanged accepted baseline'),
      dict(id='PRODUCT-R2-02',status='CURRENT_UI_REPAIR_PASS_FORMAL_SECTOR_OWNER_OPEN',evidence='6 exact missing admission fields and versioned proposal; 400/322/201 full API source checks; page-return bug fixed',next_action='Accept exact extraction/episode entry contract and genuine upstream input bytes'),
      dict(id='DAILY-R2-03',status='WAIT_REAL_DAY',evidence='Actual cutoff remains2026-10-09',next_action='Real next-day DD R2.2 source QA, no simulation'),
      dict(id='FORWARD-R2-04',status='ENGINEERING_PASS_SCOPED_ACTUAL_ENROLLMENT_MODEL_GRANT_MISSING',evidence='15 precise capability mappings;135tests;actual fail-closed API/DOM',next_action='Independently frozen enrollment owner and accepted model/version/revision/6-keygrant'),
      dict(id='EXTERNAL-R2-05',status='EXTERNAL_RECHECK_REQUESTED_NOT_ACCEPTED',evidence='Reproducible review files and separate Drive readback receipt',next_action='Independent auditor issues conclusion; Codex does not self-sign'),
      dict(id='M10-AMOUNT-A',status='OPEN_EXACT_H21_GAP',evidence='112new fixture checks0differences;378actualUNKNOWN;20missing membership observation dates',next_action='Acquire actual missing dated membership observations with original availability and formally admitted amount consumer'),
      dict(id='MEMBER27',status='USER_SCOPE_EXCLUDED_THIS_ROUND',evidence='26BSEdeferred;1SZ001235 user-reported delisted excluded;raw349 preserved',next_action='No public search or pool/identity mutation this round')]
    ledger=load(OUT/'08_REMAINING_LEDGER.json');ledger['deepening_20261010']=dict(BASE_SHA=stage['BASE_SHA'],items=updates,unified_field_matrix=binding(D/'UNIFIED_FIELD_ISSUE_MATRIX.json'));write(OUT/'08_REMAINING_LEDGER.json',ledger)
    text='''# R3 深度推进结果（2026-10-10）

本轮按任务卡继续执行；仅排除26个北交所及用户说明已退市的SZ.001235。用户说明不是新的独立dated identity authority，原始349成员、正式证券池和两个Accepted Head未修改。

| 工作包 | 本轮完成与当前验收 | 尚未闭环的确切边界 |
|---|---|---|
| P0-ALG | 153组字段→公式→输入/输出hash索引；3段真实五会话案例共15行；保留既有22452+6021及完整LOO/Pulse独立数值验收；新增325项真实UNKNOWN精确原因比较零差异、两竞争解释及复权同口径门 | 325项是原空值样本的新原因证据，不重复计为新数值样本；不能将未发布full LOO rank/episode和未接纳Detector字段称为已发布；真实重新入组未观察 |
| P0-OWNER | 6个精确正式门、已有producer函数与独立抽取/entry版本化提案；400板块/322成员/201重叠API完整核查，浏览器翻页、筛选、返回修复 | 正式CONFIRMED/WARM、冻结episode、due/followup等实际合法上游与接纳未具备 |
| P0-AMOUNT | 345表示差异已有解释；新增14fixture/112独立比较零差异；真实三金额字段族API穿透；378真实ledger候选已逐行审计 | 正式H21缺20个dated membership observation；供应商经济口径及消费者正式门OPEN |
| P1-COHORT | 15字段准确函数/Owner能力定位；合法冻结读契约与统计/期限/FEP缺源接口；135测试通过；Focus与入组保持独立 | 当前没有独立合法as-recorded Cohort Owner；FEP model/revision/grant未就绪，不能激活 |
| P1-PRODUCT-QA | 23路实际HTTP检查无失败；六入口双分辨率DOM；修复分页刷新返回与历史缺复权Owner异常；503隔离/重试、历史价格13.240正确 | QA在独立只读服务；生产加载状态另附实测；缺源HTTP200不算数据绑定PASS |
| PIT | 88实际分域生成物逐一绑定原始membership/identity/lifecycle/freezecapture与时间；精确20缺失日期清单 | corrected/latest_member_retro不能变成as-recorded；旧日期原始first-capture尚不可验证 |

本轮不是全部正式数据已闭环。当前可执行代码与证据修补已完成上述范围，剩余项的producer、合同、缺失bytes、消费者、六维状态和下一动作见UNIFIED_FIELD_ISSUE_MATRIX.json与08_REMAINING_LEDGER.json追加段。AmountA仍为独立跨切审计；正式板块权限/模型权限不以“测试通过”代替。

新增具名交付：P0_OWNER_BROWSER_QA.md、P1_FORWARD_FREEZE_AND_MATURITY_TESTS.json、P1_FORWARD_API_UI_QA.md、P1_PRODUCT_FP_REGRESSION_MATRIX.json、P1_PRODUCT_REAL_BROWSER_QA.md、P1_PRODUCT_NEGATIVE_TESTS.json、09_EVIDENCE_MANIFEST.json、10_DRIVE_READBACK_RECEIPT.json。manifest/Drive收据由交付步骤随后生成，其PASS只以真实云端重取bytes/SHA为准。

未修改TDX输入、证券池、阈值、Focus正式写入、Priority V1、Accepted Head；未模拟10/12；EXTERNAL_RECHECK_REQUESTED，无EXTERNAL_ACCEPTANCE_PASS。既有核对报告保留历史原文，新判定以本报告和追加矩阵为准。
'''
    markdown(D/'DEEPENING_RESULT.md',text)
    report=OUT/'TASK_CARD_COMPLETION_RECONCILIATION_20261010.md';old=report.read_text(encoding='utf8')
    marker='## 2026-10-10 深度推进追加判定'
    if marker not in old:markdown(report,old+'\n'+marker+'\n\n上文是e1d7f69时点核对，保留历史记录。本轮已完成额外算法案例/字段矩阵、独立AmountA边界审计、Owner提案、Cohort能力/API/UI、产品真实交互修复及具名交付。最新状态见11_DEEPENING/DEEPENING_RESULT.md与08_REMAINING_LEDGER.json的deepening_20261010段；剩余正式输入/接纳/PIT/未来结果仍分别OPEN，不能沿用旧概括“工程均未处理”。\n')
    print('unified fields',len(matrix),'production',observed)
if __name__=='__main__':main()
