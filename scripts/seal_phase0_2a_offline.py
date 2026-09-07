"""Seal existing Phase 0.2A evidence without network access or recalculation."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from phase0_1_runner import atomic_json, atomic_text
from phase0_2a_runner import _csv_text
from tdx.gbbq_reader import file_sha256
from tdx.tdx_audit import snapshot_day_files, raw_manifest_fingerprint
from validation.external_qfq import ExternalBar, compare_ohlc


def seal():
    tdx = Path('D:/new_tdx')
    out = ROOT / 'reports/phase0_2a'
    recovered = json.loads((out / 'RECOVERED_FIRST_RUN_EVIDENCE.json').read_text(encoding='utf-8'))
    # Freeze the failed rerun before replacing the canonical report. Rerunning
    # this offline seal always reads this immutable snapshot.
    for name in ('EXTERNAL_QFQ_CROSSCHECK.json', 'EXTERNAL_SOURCE_AUDIT.json', 'PHASE0_2A_FINAL_RECEIPT.json'):
        snapshot = out / 'failed_rerun_001' / name
        if not snapshot.exists():
            atomic_json(snapshot, json.loads((out / name).read_text(encoding='utf-8')), tdx)
    cross = json.loads((out / 'failed_rerun_001/EXTERNAL_QFQ_CROSSCHECK.json').read_text(encoding='utf-8'))
    source = json.loads((out / 'failed_rerun_001/EXTERNAL_SOURCE_AUDIT.json').read_text(encoding='utf-8'))
    receipt = json.loads((out / 'failed_rerun_001/PHASE0_2A_FINAL_RECEIPT.json').read_text(encoding='utf-8'))
    restored = {(r['security_id'], r['date']): r for r in recovered['rows']}
    for row in cross['rows']:
        previous = restored.get((row['security_id'], row['date']))
        if previous:
            bar = ExternalBar(row['date'], *[Decimal(str(previous[f'external_{f}'])) for f in ('open', 'high', 'low', 'close')])
            row.update(compare_ohlc(row, bar))
            row['external_source'] = 'TENCENT'
            row['notes'] = 'Recovered from first-run displayed tool output; first-run raw response body not retained; external RAW diagnosis incomplete'
            row['evidence_provenance'] = 'FIRST_RUN_TOOL_OUTPUT'
        else:
            row.update(compare_ohlc(row, None))
            row['notes'] = 'First-run per-point external values not retained after overwrite; rerun HTTP 501; no invented values'
            row['evidence_provenance'] = 'LOCAL_VALUE_ONLY_EXTERNAL_EVIDENCE_UNAVAILABLE'
    detailed = [r for r in cross['rows'] if r['external_open'] is not None]
    matched = sum(r['within_tolerance'] for r in detailed)
    failed = len(detailed) - matched
    historical = {k: v for k, v in recovered.items() if k != 'rows'}
    cross.update({
        'status_distribution': {'LOCAL_MATCHES_EXTERNAL': matched, 'LOCAL_MISMATCH_REQUIRES_REVIEW': failed, 'UNVERIFIABLE_EXTERNAL': 128-len(detailed)},
        'fixed_sample_passed': matched, 'fixed_sample_failed': failed, 'fixed_sample_unverifiable': 0,
        'verified_point_count': len(detailed), 'matching_point_count': matched, 'mismatch_point_count': failed,
        'unverifiable_point_count': 128-len(detailed), 'match_ratio': matched/len(detailed),
        'historical_first_run_summary': historical,
        'systematic_mismatch_detected': None,
        'systematic_mismatch_by_type': {'CASH_DIVIDEND': '0.069 CNY common shift in four fields; cause unconfirmed', 'BONUS_TRANSFER_AND_CASH': '0.388-0.393 CNY shift; cause unconfirmed'},
        'complex_types_pass': False,
        'evidence_completeness': 'PARTIAL_AFTER_OVERWRITE_RECOVERY',
        'systematic_mismatch_suspected': True,
    })
    # Aggregate the two recorded batch runs; exploratory probes are separately
    # disclosed, rather than inventing exact counts or timestamps for them.
    for audit in source['sources']:
        counts = recovered['source_counts'].get(audit['source_name'], {})
        audit['failed_rerun_request_count'] = audit['request_count']
        audit['first_run_request_count'] = counts.get('request_count', 0)
        for key in ('request_count', 'success_count', 'failure_count'):
            audit[key] += counts.get(key, 0)
        if audit['source_name'] == 'TENCENT':
            audit['first_success_time'] = recovered['first_success_time']
            audit['last_success_time'] = recovered['last_success_time']
            audit['request_limit_exceeded'] = True
        audit['query_parameters_note'] = 'See failed rerun snapshot for second-run parameters; first Tencent run used day/qfq, 40 rows, +/-12 calendar days'
    source.update({
        'total_http_request_count': sum(s['request_count'] for s in source['sources']),
        'request_count_scope': 'TWO_BATCH_RUNS_ONLY; exploratory probes excluded',
        'request_budget_compliance': False,
        'historical_defect': 'Second batch issued 384 Tencent requests, exceeding the intended 200 ceiling; cap was only descriptive in old code',
        'repair': 'Enforced shared Tencent QFQ/RAW budget; terminal HTTP errors open circuit; completed reports cannot be overwritten by runner',
        'additional_exploratory_access': 'Eastmoney and Tencent probes plus public Sina pages/scripts/factor endpoints occurred; not included in numeric batch counts; no independent Sina QFQ OHLC accepted',
        'external_production_integration': False,
    })
    tests = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=ROOT, capture_output=True, text=True)
    passed = re.search(r'(\d+) passed', tests.stdout)
    day_paths, _ = snapshot_day_files(tdx)
    receipt['gbbq_sha256_after'] = file_sha256(tdx / 'T0002/hq_cache/gbbq')
    receipt['gbbq_map_sha256_after'] = file_sha256(tdx / 'T0002/hq_cache/gbbq.map')
    receipt['day_metadata_manifest_after'] = raw_manifest_fingerprint(day_paths)
    unchanged = all(receipt[a] == receipt[b] for a, b in (
        ('gbbq_sha256_before', 'gbbq_sha256_after'), ('gbbq_map_sha256_before', 'gbbq_map_sha256_after'),
        ('day_metadata_manifest_before', 'day_metadata_manifest_after')))
    receipt.update({
        'run_time': datetime.now().astimezone().isoformat(), 'seal_method': 'OFFLINE_EXISTING_EVIDENCE_ONLY',
        'final_status': 'BLOCKED_FOR_FORMAL_ADJUSTMENT',
        'external_sources_used': ['TENCENT'], 'fixed_sample_passed': matched, 'fixed_sample_failed': failed,
        'fixed_sample_unverifiable': 0, 'verified_point_count': len(detailed), 'matching_point_count': matched,
        'mismatch_point_count': failed, 'unverifiable_point_count': 128-len(detailed), 'match_ratio': matched/len(detailed),
        'historical_first_run_summary': historical, 'evidence_completeness': 'PARTIAL_AFTER_OVERWRITE_RECOVERY',
        'systematic_mismatch_detected': None, 'systematic_mismatch_suspected': True,
        'manual_ui_gate': 'NOT_WAIVED', 'manual_ui_waiver_reason': 'FOUR_FIXED_SAMPLE_MISMATCHES_AND_INCOMPLETE_BATCH_EVIDENCE',
        'adjustment_status': 'UNRESOLVED_EXTERNAL_QFQ_MISMATCH', 'project_price_basis': 'RAW',
        'formal_trend_scanners_allowed': False, 'tdx_source_unchanged': unchanged,
        'tests_passed': int(passed.group(1)) if passed else 0, 'tests_failed': int(tests.returncode != 0),
        'test_output': tests.stdout.strip(), 'next_allowed_phase': 'NONE',
        'warnings': ['Historical batch 97/120=80.83% is summary-only; only five external OHLC rows recoverable',
                     'Raw-basis and independent-source diagnostics did not close; cause not attributed conclusively to local algorithm',
                     'Second batch exceeded request budget and overwrote first evidence; both defects repaired and disclosed'],
        'errors': ['FIXED_QFQ_SAMPLE_MISMATCH_4_OF_5', 'BATCH_EVIDENCE_INCOMPLETE'],
        'minimal_reproduction': next(r for r in detailed if r['security_id']=='SH.600519' and r['date']==20250625),
        'possible_causes': ['Local/external corporate-action history or parameter revisions', 'Different raw history or precision', 'External QFQ convention differences'],
    })
    atomic_json(out / 'EXTERNAL_QFQ_CROSSCHECK.json', cross, tdx)
    atomic_text(out / 'EXTERNAL_QFQ_CROSSCHECK.csv', _csv_text(cross['rows']), tdx, bom=True)
    atomic_json(out / 'EXTERNAL_SOURCE_AUDIT.json', source, tdx)
    atomic_json(out / 'PHASE0_2A_FINAL_RECEIPT.json', receipt, tdx)
    table = '\n'.join('| '+ ' | '.join([
        r['security_id'], str(r['date']),
        '/'.join(f"{r[f'local_{f}']:.2f}" for f in ('open','high','low','close')),
        '/'.join(f"{r[f'external_{f}']:.3f}" for f in ('open','high','low','close')),
        '/'.join(f"{r[f'diff_{f}']:+.3f}" for f in ('open','high','low','close')),
        'PASS' if r['within_tolerance'] else 'MISMATCH'])+' |' for r in detailed)
    report = f'''# Phase 0.2A 外部前复权交叉验证报告

最终状态：`BLOCKED_FOR_FORMAL_ADJUSTMENT`。固定五点中四点超过 0.01 元容差，自动验收不能豁免。该状态阻止正式复权上线，不代表已经证明本地解码或仿射公式错误；根因尚未完成双源和原始行情排查。

## 数据与来源

生产数据源始终为 `LOCAL_TDX_ONLY`。参考查询为东方财富日 K `klt=101,fqt=1` 与腾讯 `day,qfq`。东财批量访问失败；腾讯首轮返回了数据。来源：[东方财富公开接口](https://push2his.eastmoney.com/api/qt/stock/kline/get)、[腾讯公开前复权接口](https://web.ifzq.gtimg.cn/appstock/app/fqkline/get)。字段顺序均为日期、开、收、高、低，已映射为 OHLC。腾讯不复权诊断接口与 QFQ 严格分离。

## 固定五点（O/H/L/C，差值=本地−外部）

| 股票 | 日期 | 本地 | 腾讯 | 差值 | 结果 |
|---|---:|---|---|---|---|
{table}

最小复现：SH.600519 20250625 四价均偏低 0.069 元，超过 0.01 元容差；这不是已知的 20060526 开盘孤立特例。格力 20150702 也存在约 0.39 元偏移。可能涉及公司行为参数、历史修订、原始价格差异或外部复权口径；目前证据不足以唯一归因，不修改复权核心。

## 批量覆盖与证据限制

首轮实际覆盖 32 只股票、128 日期点、512 个价格，沪深主板、创业板、科创板和北交所均在计划内。首轮统计为 120 点可查询、97 点匹配、23 点不一致、8 点不可查询，匹配率 **80.83%**，未达到 95%。首轮固定样本为 1/5。

收尾发现第二轮全部失败，但覆盖了首轮产物。工具输出中仍可恢复上述首轮统计及五个完整 OHLC 点，其余外部逐点数值未保留，不能重建。因此当前 CSV/JSON 保留 128 行本地样本，但只有五行含已恢复外部值，其余标记 `UNVERIFIABLE_EXTERNAL` 并说明证据缺失。当前可复算明细匹配率为 **1/5=20%**，与首轮 97/120 的统计口径不同；不得混用或虚构其余数据。

原失败重跑产物冻结于 `reports/phase0_2a/failed_rerun_001/`；恢复依据在 `RECOVERED_FIRST_RUN_EVIDENCE.json`。没有为修复审计再次请求同批数据。

## 执行偏差与修复

第二轮实际发出 384 次腾讯失败请求，原先代码未真正执行报告所称的 200 次限制。两轮批量合计腾讯 512 次、东财 6 次；另有少量交互预检，不包含在该精确计数内。此前关于请求始终受限的进度说明不准确。全部请求现已停止。

已补充：同一提供商 QFQ/RAW 共用硬上限；HTTP 501 等明确错误立即停止该源；三次连续失败停止后续样本；禁止覆盖完成的网络报告；QFQ 解析不再静默回退原始 `day`；其他样本的源冲突不能掩盖固定点失败。离线封板脚本可重复运行，不触发网络。

## 安全、测试与最终闸门

- 源未变化：`{unchanged}`。GBBQ、map 内容哈希与全部日线元数据指纹均匹配 Phase 0.2。
- 测试：{receipt['tests_passed']} passed，{receipt['tests_failed']} failed（包括请求预算、熔断、字段与日期映射、验收判定；离线测试不联网）。
- `PROJECT_PRICE_BASIS=RAW`；`FORMAL_TREND_SCANNERS_ALLOWED=false`。
- `MANUAL_UI_GATE=NOT_WAIVED`；`NEXT_ALLOWED_PHASE=NONE`。
- 系统性差异：疑似；本地算法错误：未被唯一证实。固定四点不一致与证据不完整足以阻止正式上线。

## 产物

- EXTERNAL_QFQ_CROSSCHECK.csv：UTF-8 BOM，128 点，本地/外部/差值及状态。
- EXTERNAL_QFQ_CROSSCHECK.json：相同明细、首轮统计与证据限制。
- EXTERNAL_SOURCE_AUDIT.json：两轮请求统计、失败原因及执行偏差。
- PHASE0_2A_FINAL_RECEIPT.json：完整状态、最小复现与源完整性。
- RECOVERED_FIRST_RUN_EVIDENCE.json、failed_rerun_001/：恢复依据及失败原件。

本阶段完成自动核验和失败封板。正式因子阶段保持禁止；不再把本任务改为要求用户手工抄录五点。
'''
    atomic_text(ROOT / 'docs/PHASE0_2A_REPORT.md', report, tdx)
    print(json.dumps({k:receipt[k] for k in ('final_status','fixed_sample_passed','fixed_sample_failed','tests_passed','tests_failed','tdx_source_unchanged')}, indent=2))


if __name__ == '__main__':
    seal()
