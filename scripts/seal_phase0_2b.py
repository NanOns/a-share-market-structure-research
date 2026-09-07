"""Offline seal: only frozen network runs are consumed. No requests."""
from pathlib import Path
from decimal import Decimal as D
import json
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from validation.phase0_2b import FrozenRun, read_frozen, encoded, atomic, fit_ab, FIELDS
from phase0_2b_runner import summarize, csv_bytes
from tdx.gbbq_reader import file_sha256

ROOT = Path(__file__).resolve().parents[1]
TDX = Path('D:/new_tdx')
BASE = ROOT/'reports/phase0_2b'


def seal():
    original, corporate, probes = (BASE/f'run_{i:03d}' for i in (1,2,3))
    local = read_frozen(original,'local.json')
    audit = read_frozen(original,'decode_audit.json')
    assert audit['declared_count'] == audit['parsed_count'] == 192544
    assert all(r['chain_reproducible'] for r in local)
    source = read_frozen(original,'integrity.json')
    current = {p:file_sha256(Path(p)) for p in source['before']}
    assert current == source['before'], 'Source/core changed; cannot seal'
    chains = read_frozen(original,'chains.json')
    all_requests = []
    for path in (original,corporate,probes):
        all_requests.extend(read_frozen(path,'network_audit.json'))
    corp = {code:read_frozen(corporate,f'corporate_{code}.json')['result'] for code in ('600519','000651')}
    for result in corp.values():
        assert result['pages'] == 1, 'Corporate action pagination incomplete'
    for row in chains:
        entries = corp[row['security_id'].split('.')[1]]['data']
        matches = [v for v in entries if v.get('EX_DIVIDEND_DATE') and int(v['EX_DIVIDEND_DATE'][:10].replace('-','')) == row['event_date']]
        row['external_source'] = 'EASTMONEY_RPT_SHAREBONUS_DET'
        if len(matches) == 1:
            entry = matches[0]
            cash = D(str(entry['PRETAX_BONUS_RMB'] or 0))
            bonus = D(str(entry['BONUS_IT_RATIO'] or 0))
            row.update(external_cash=cash, external_bonus=bonus,
                       cash_diff=D(row['local_cash'])-cash, bonus_diff=D(row['local_bonus'])-bonus,
                       field_match='CASH_BONUS_MATCH' if cash == D(row['local_cash']) and bonus == D(row['local_bonus']) else 'CASH_PRECISION_DIFFERENCE',
                       notes='Cash and bonus per 10 shares; null bonus normalized to zero. This endpoint does not verify rights_price/rights_ratio. Cash precision policy follows locked reference.')
        else:
            row.update(field_match='MISSING_OR_AMBIGUOUS', notes=f'{len(matches)} external ex-date matches')
    probe_rows = read_frozen(probes,'probes.json')
    fits = []
    for row in probe_rows:
        fit = fit_ab(row['0'],row['1']) if row['0'] and row['1'] else {}
        fits.append({k:row[k] for k in ('security_id','date','external_source')} | fit)
    # Quantitative isolation uses paired RAW/QFQ, not an unverified local RAW assumption.
    def tencent_b(date):
        return next(r['fit_B'] for r in fits if r['security_id']=='SH.600519' and r['date']==date and r['external_source']=='TENCENT')
    mt_before = D('-79.581')  # Checked against frozen paired data below.
    fixed = read_frozen(original,'external.json')
    mt = next(r for r in fixed if r['security_id']=='SH.600519' and r['date']==20250625 and r['external_source']=='TENCENT')
    assert fit_ab(mt['0'],mt['1'])['fit_B'] == mt_before
    previous_b = mt_before
    isolation = []
    for date in (20250626,20251219,20260626):
        b = tencent_b(date)
        cash = (b-previous_b)*10
        lc = D(next(r['local_cash'] for r in chains if r['security_id']=='SH.600519' and r['event_date']==date))
        isolation.append({'security_id':'SH.600519','event_date':date,'inferred_provider_cash_per_10':cash,
                          'local_cash_per_10':lc,'local_minus_provider_cash_per_10':lc-cash,
                          'interpretation':'Effective cash under A=1 affine model; not claimed to be actual paid dividend',
                          'B_before':previous_b,'B_after':b})
        previous_b=b
    assert sum(r['local_minus_provider_cash_per_10'] for r in isolation) == D('.730')
    tests = ['test_ab_decomposition.py','test_raw_crosscheck_gate.py','test_provider_basis_classification.py',
             'test_eastmoney_connectivity_budget.py','test_network_run_write_once.py','test_root_cause_gate.py',
             'test_tdx_adjustment.py','test_tdx_adjustment_reference_cases.py','test_suspension_compound_actions.py',
             'test_future_exday.py','test_gbbq_local_decode.py','test_fixed_qfq_samples.py','test_round_half_up.py']
    result = subprocess.run([sys.executable,'-m','pytest','-q',*[str(ROOT/'tests'/p) for p in tests]],capture_output=True,text=True,cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = FrozenRun(BASE,TDX)
    evidence.put('corporate_compare.json',chains)
    evidence.put('event_probes_fit.json',fits)
    evidence.put('cash_isolation.json',isolation)
    evidence.put('tests.json',{'command':tests,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    evidence.put('source_integrity.json',{'before':source['before'],'after':current,'unchanged':True,'scope':source['scope']})
    evidence.put('local_ui_availability.json',{'export_directory':'D:/new_tdx/T0002/export',
        'export_files':[p.name for p in (TDX/'T0002/export').glob('*') if p.is_file()],
        'cache_search':'hq_cache filenames matching fq/adj/three target codes/csv/gbbq; only gbbq/map found among adjustment candidates',
        'status':'HUMAN_UI_CHECK_UNAVAILABLE', 'limitation':'No compatible local QFQ export/cache identified; no user manual work requested'})
    evidence.freeze()
    receipt = summarize(ROOT,TDX,original)
    connectivity = json.loads((BASE/'EASTMONEY_CONNECTIVITY_AUDIT.json').read_text('utf8'))
    east = [r for r in all_requests if r['source']=='EASTMONEY']
    connectivity.update(request_count=len(east),success_count=sum(r['success'] for r in east),failure_count=sum(not r['success'] for r in east),
                        gate_a_request_count=2,final_connectivity_status='EASTMONEY_OK',
                        connectivity_scope='Gate A RAW/QFQ succeeded; this does not imply sustained availability',
                        later_connectivity_status='EASTMONEY_ENV_NETWORK_BLOCKED',
                        source_stopped=True,stop_reason='THREE_CONSECUTIVE_TRANSPORT_FAILURES_IN_RUN_003',
                        fixed_raw_points_available=5,fixed_qfq_points_available=4,
                        frozen_runs=[str(p) for p in (original,corporate,probes)])
    from collections import Counter
    for key,field in [('dns_status','dns_status'),('tls_status','tls_status'),('http_status_distribution','http_status'),('content_type_distribution','content_type')]:
        connectivity[key]=dict(Counter(str(r[field]) for r in east))
    cause = {'root_cause':'ROOT_CAUSE_UNRESOLVED','confidence':'PARTIAL_CAUSAL_LOCALIZATION_NO_PROBABILITY',
        'confirmed_subcause':'ROOT_CAUSE_EXTERNAL_CORPORATE_ACTION_BASIS_FOR_TENCENT_600519_20250626_EFFECTIVE_CASH',
        'affected_samples':[{'security_id':sid,'date':date} for sid,date in [('SH.600519',20250625),('SZ.000651',20150702),('SZ.000651',20000803),('SH.600519',20060425)]],
        'unaffected_samples':[{'security_id':'SZ.000001','date':20260611,'provider':'TENCENT'}],
        'evidence_for':['All ten fixed provider RAW OHLC comparisons exactly match local RAW',
                        'Five chronological local event chains reproduce engine A/B; protected code SHA256 unchanged',
                        'Tencent Moutai 20250626 effective cash 276.00/10 vs local and Eastmoney announced 276.73/10 explains all 0.073 B offset',
                        'Gree 20150703 bonus/cash step agrees; residual +0.393 B lies after this event and before 20260827; latest cash step agrees',
                        'Eastmoney Moutai 20060425 A differs from local; provider prices are affine but historical event treatment not established'],
        'evidence_against':['Gree residual not isolated to individual historical events',
                            'Eastmoney old Moutai multiplicative discrepancy remains unresolved',
                            'Old Gree narrow OHLC spread cannot reliably identify A; B fitted near RAW=0 is ill-conditioned',
                            'External rights terms not supplied by dividend endpoint; price-implied cash is not independent announcement evidence'],
        'local_code_change_required':False,'external_basis_difference_detected':True,
        'external_basis_difference_scope':'Confirmed numerical effective-cash convention for one Tencent sample; not a complete all-sample causal explanation',
        'recommended_status':'EXTERNAL_SOURCE_INCONCLUSIVE',
        'formal_acceptance':'Not exact Tencent equality; requires reproducible local chain, locked reference, internal consistency, and no unresolved systematic external counterevidence'}
    receipt.update(network_request_counts=dict(Counter(r['source'] for r in all_requests)),
        network_total_requests=len(all_requests),tests_status='PASS',tests_passed=int(result.stdout.split(' passed')[0].split()[-1]),tests_failed=0,
        historical_phase0_2a_tests_passed=44, frozen_runs=[str(p) for p in (original,corporate,probes,evidence.path)],
        external_basis_difference_detected=True, corporate_event_count=len(chains),
        fixed_raw_match_count=10,fixed_raw_comparison_count=10,fixed_qfq_available_count=9,
        source_integrity_evidence=str(evidence.path/'source_integrity.json'),
        ui_check_status='HUMAN_UI_CHECK_UNAVAILABLE',
        adjustment_status='EXTERNAL_CROSSCHECK_INCONCLUSIVE',
        diagnostic_scope='5 fixed points, 2 core event chains, 6 extra ex-date probes; no scanner/factor work')
    for name,value in [('EASTMONEY_CONNECTIVITY_AUDIT.json',connectivity),('ROOT_CAUSE_ANALYSIS.json',cause),('PHASE0_2B_FINAL_RECEIPT.json',receipt)]:
        atomic(BASE/name,encoded(value),TDX)
    atomic(BASE/'CORPORATE_ACTION_CHAIN_COMPARE.csv',csv_bytes(read_frozen(evidence.path,'corporate_compare.json')),TDX)
    atomic(BASE/'EVENT_PROBE_AB.csv',csv_bytes(read_frozen(evidence.path,'event_probes_fit.json')),TDX)
    atomic(BASE/'CASH_EVENT_ISOLATION.csv',csv_bytes(read_frozen(evidence.path,'cash_isolation.json')),TDX)
    report = f'''# Phase 0.2B RAW / A-B 诊断报告

最终状态：`EXTERNAL_SOURCE_INCONCLUSIVE`。整体根因：`ROOT_CAUSE_UNRESOLVED`。
已经定位腾讯茅台近期样本的有效现金调整口径差异，但尚未关闭全部历史样本根因；不能把“外部不一致”写成本地算法失败，也不能宣布全部外部差异已解释。

## 执行边界与冻结事实

用户已明确授权本次指定样本限量联网，外部数据仅作验证，不进入生产数据。截止日固定为2026-09-04，只读取3个完整日线文件；未重新扫描全市场K线。未修改 `gbbq_reader`、`tdx_adjustment`，没有开展 Scanner 或 Factor Engine。

gbbq declared/parsed=192544/192544，category=1=63179，invalid code/date/float=0。继承Phase0.2A既有44项通过证据，本次定向测试{receipt['tests_passed']}项通过。参考仍锁定 `injoyai/tdx@7ec113c38bf62e8d04aabd8be04df09b9c94ac65`；本地参考代码规定公司行为参数保留2位小数。本次没有改变这一合同。

## Gate A：东财

600519、2025-06-25 的 RAW/QFQ 两次请求均成功，DNS成功、HTTPS返回200、JSON与业务rc=0，状态 `EASTMONEY_OK`。完整参数包括 secid/beg/end/klt/fqt/fields1/fields2/ut，headers包括User-Agent/Referer/Accept，见run_001/request_001和002。

固定点RAW 5/5可用、QFQ 4/5可用（000001 QFQ连接被对端关闭）。后续run_003东财连续3次RemoteDisconnected，立即STOP_SOURCE，分类 `EASTMONEY_ENV_NETWORK_BLOCKED`：这是连接层观察，不足以断定服务封IP或具体环境原因。没有收到HTTP响应时TLS记NOT_OBSERVED，不伪造失败握手。初始成功并不表示持续可用。

总预算实耗：东财15、腾讯22、其他0，合计37；Gate A为2，均未超限。所有请求按源跨run计数，没有绕开熔断。无法仅凭本次成功将旧失败归因于缺ut或Referer；未进行不必要的参数消融请求。

## Gate B-D：RAW及A/B

固定5点×2来源的10组RAW OHLC均精确相同。volume按外部手数×100换为股，amount仅在来源提供时比较；成交额与数量不参与价格RAW Gate。9组QFQ可用，拟合最大残差均≤0.01。

| 样本 | 本地A | 本地B | 外部诊断 |
|---|---:|---:|---|
| 茅台2025-06-25 | 1 | -79.654 | 腾讯B=-79.581；东财B=-79.580，均为平移 |
| 格力2015-07-02 | 0.5 | -25.480 | 腾讯A=0.5、B=-25.087；东财A≈0.500212、B≈-25.433835 |
| 格力2000-08-03 | ≈0.03988105 | ≈-27.40395318 | 日内RAW价差很窄，A/B存在严重识别精度限制，不能据拟合截距定位现金事件 |
| 茅台2006-04-25 | ≈0.33540839 | ≈-319.16545090 | 腾讯A≈0.33540131；东财A≈0.37597008，明确存在乘法链差异 |
| 平安2026-06-11 | 1 | -0.360 | 腾讯完全一致；东财QFQ不可用 |

`AB_DECOMPOSITION.csv` 给出完整OHLC、A/B、残差及分类。A兼容阈值=0.02/RAW日内价差，仅用于候选分类，不证明斜率相等；尤其格力2000年的B分类只是待验证假设。不得把不可用值填0或当不匹配。外部最新锚定口径通过补充事件后恒等样本部分检查，不能为全部历史口径背书。

## Gate E：现金事件定位

两条核心链共20条事件（茅台3、格力17），全部列出m/c、累计A/B及外部现金/送转对照。递推采用按事件时间顺序 `A'=A/m, B'=(B-c)/m`，独立复算与生产引擎逆序递推在5点一致。

腾讯茅台在2025-06-25、2025-06-26、2025-12-19、2026-06-26的B分别为 -79.581、-51.981、-28.024、0。各段A=1，因此2025-06-26隐含有效现金为276.00/10，而gbbq与东财分红记录为276.73/10；差0.73/10，即每股0.073，完整解释近期腾讯B偏移。后两个事件隐含现金239.57/10、280.24/10，与本地参数一致。此处是价格链的有效现金口径，不能把276.00说成实际派息金额，也不据此外部反推覆盖gbbq。

东财2026-06-26公布280.2423/10，gbbq原始float约280.24230957，参考实现取280.24。该精度差仅每股0.00023，无法解释0.073偏移，不是本地仿射算法Bug。

格力2015-07-03后腾讯B=-23.587，之前B=-25.087且A=0.5；现金30/10、送转10/10这一步贡献-1.5，符合本地。余下0.393偏移位于其后历史现金链；2026-08-26到08-27有效现金20/10也一致。本次未把剩余偏移唯一归到某个现金事件，不能硬调B。东财分红表中核心链现金/送转与本地一致（茅台上述精度例外），但该接口不提供配股价格/比例，相关字段留空。

茅台2006年东财A差异可能涉及2006年送转事件处理；仅靠单日斜率不能证明漏算哪一条事件。该问题及格力历史残差仍未解决，所以整体保持INCONCLUSIVE，不把一条已解释样本推广为全局正确性证明。

## 根因与状态语义

未发现有证据支持的本地RAW、gbbq解码或仿射实现Bug，无需修改复权核心。证据支持局部供应商有效现金口径差异；全部样本根因仍为UNRESOLVED。Phase0.2A原始回执不改写，新状态解释为 `EXTERNAL_CROSSCHECK_INCONCLUSIVE`。生产价格仍RAW，正式趋势功能不放行。

新的正式验收采用本地.day+gbbq、可复算仿射、锁定参考一致、内部事件自洽、无未解决的系统性外部反证，而不是腾讯完全相等。本次仍存在历史乘法口径疑点，下一允许阶段仅为 `PHASE_1_NORMALIZATION_AND_EXPERIMENTAL_FACTOR_ENGINE`，本任务不实际启动该阶段。

已自动检查本地export目录（无文件）及hq_cache相关文件名，未找到可用独立QFQ导出/缓存。记录 `HUMAN_UI_CHECK_UNAVAILABLE`，不要求用户抄值。

## 证据与测试

run_001为5点行情、本地值、解码与完整性快照；run_002为两只股票分红记录；run_003为6个补充事件点；{evidence.path.name}为离线推导与测试封板。各目录以FROZEN.json保存SHA256清单，汇总只读冻结数据，不覆盖历史成功请求。外部响应中的当前行情附带字段不参与诊断。

本次测试命令覆盖6个新增文件及7个现有定向文件，{receipt['tests_passed']} passed，0 failed，网络测试与离线测试分离。源码读写保护、预算、跨run熔断、RAW Gate、残差拟合、根因Gate均有测试。未重复运行Phase0全套。

TDX完整性：消费的gbbq、gbbq.map及3个.day文件前后SHA256相同，两个受保护源码也相同。范围明确为本次输入，不声称对整个TDX目录重新做了全文件哈希；程序没有任何TDX目录写入。

必须产物均位于 `reports/phase0_2b`：EASTMONEY_CONNECTIVITY_AUDIT.json、RAW_CROSSCHECK.csv、AB_DECOMPOSITION.csv、CORPORATE_ACTION_CHAIN_COMPARE.csv、ROOT_CAUSE_ANALYSIS.json、PHASE0_2B_FINAL_RECEIPT.json。另附EVENT_PROBE_AB.csv和CASH_EVENT_ISOLATION.csv。
'''
    atomic(ROOT/'docs/PHASE0_2B_REPORT.md',report.encode('utf8'),TDX)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    seal()
