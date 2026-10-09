"""Summarize actual executed artifacts without fabricating external acceptance."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src')]
from workbench_analysis.corrected_owner_replay import load,ref
from workbench_analysis.market_source_acquisition import write
from workbench_analysis.tdx_official_daily_source import _atomic_write
OUT=ROOT/'docs/evidence/r4_3_four_session_closeout_20261009'

def main():
    required=['00_ENTRY_DRIVE_HEAD_AND_PROTECTED_DIGESTS.json','01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json','02_TDX_MEMBER_SNAPSHOT_S_AND_0930_PIT_DIFF.jsonl.gz','03_FOUR_SESSION_UNIVERSE_BAR_SUSPENSION_BJ_RECONCILIATION.csv','04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json','05_FOUR_SESSION_RAW_QFQ_CORE_PROFILE_NUMERIC_ORACLE.json','06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json','07_FIELD_LINEAGE_AND_UNKNOWN_REASONS_BY_DATE.csv','08_CANONICAL_IDENTITY_AND_CORRECTED_OWNER_ADMISSION.json','09_NEW_OPERATIONAL_PUBLICATION_POLICY_AND_OLD_PIT_MIGRATION.md','10_SUCCESSOR_ATOMIC_CAS_BAD_SOURCE_ROLLBACK_QA.json','11_FOUR_SESSION_LIVE_API_SAME_CONTEXT_AND_UI_READBACK.json','12_INDEPENDENT_EXTERNAL_REVIEW_AND_FIX_REGISTER.md','13_ALL_TEST_COMMANDS_SHA_AND_SCOPE.json']
    bindings=[ref(ROOT,OUT/n) for n in required]
    numeric=load(OUT/required[5]);sector=load(OUT/required[6]);cas=load(OUT/required[10]);focus=load(OUT/'owner_v3/FOCUS_FORWARD_REPLAY.json')
    assert not numeric['errors'] and cas['production_data_head_moved'] is False
    snapshot=load(OUT/'MEMBER_SNAPSHOT_S.json')
    status=dict(final_status='EXTERNAL_ACCEPTANCE_BLOCKED',source_and_numeric='FOUR_SESSION_SOURCE_AND_NUMERIC_PASS',operational='FOUR_SESSION_OPERATIONAL_RECONSTRUCTED_PASS',production='NOT_GRANTED_INDEPENDENT_EXTERNAL_ACCEPTANCE_ABSENT',strict_PIT='STRICT_HISTORICAL_PIT_NOT_GRANTED',W8='NOT_AUTHORIZED',evidence=bindings)
    write(OUT/'R43_FINAL_ENGINEERING_ACCEPTANCE.json',status)
    lines=['# R4.3 四日闭环外审交接','', '**唯一最终状态：EXTERNAL_ACCEPTANCE_BLOCKED**。工程重建和候选 QA 已执行；未收到针对本轮实际字节的独立外部验收，生产未切换。','',
      '- FOUR_SESSION_SOURCE_AND_NUMERIC_PASS：已通过既有正式 required 四板范围的四日证券、RAW、停牌、GBBQ/复权、Core/Profile 独立工程复算。北交所继承 optional DEGRADED_BSE，未宣称全市场 PASS。',
      '- FOUR_SESSION_OPERATIONAL_RECONSTRUCTED_PASS：同一最新通达信 S 已实际计算行业/概念 Native、LOO、Seed、B0、Rotation、股票/市场与事后 Focus/Forward。',
      '- FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS：未获准。线上仍为 2026-09-30；候选 10/08 HTTP/API/UI 读回与正式生产读回分开。',
      '- STRICT_HISTORICAL_PIT_NOT_GRANTED；W8 页面剩余缺陷任务未启动。','',
      '| 工作包 | 结果 | 实际证据／下一步 |','|---|---|---|',
      '| W0 | PASS | HEAD/任务/AGENTS/原 85 证据及源 SHA 入场；89 绑定复核未变化 |',
      '| W1 | PASS | 133 行业（110 叶级、23 父级解释层）、268 概念，55136 关系；2224 未映射关系完整隔离，T00 无有效成员另列 |',
      '| W2 | PASS | RAW 5210/5211/5213/5209，真实停牌 12/12/11/15，非停牌缺 BAR 0；GBBQ 193554 事件；新 lifecycle/special |',
      '| W3 | PASS | 实际新 owner_v3 重建；128 多样性真实数值样本，41786 RPS 和26119前驱差分复核，128 Profile样本及103680日涨跌限检查 |',
      '| W4 | PASS | 四日各400计算板块，40独立LOO样本；真实成员移动及重复确定性测试通过，原9/30成员digest保留 |',
      '| W5 | PASS（字段级降级） | 原结构+可证事后突破观察、四轴、日K限制、真实锚定Focus/Forward；缺episode前态／日内源等保留具名未知 |',
      '| W6 | PASS（候选工程） | 版本化发布合同，实际E盘CAS/并发/坏源/故障/NOOP/stale/回滚，候选HTTP及UI同版读回 |',
      '| W7 | NOT_VERIFIABLE | 缺独立外部审查与正式准入签名；未执行生产CAS，无CUTOVER_PASS |',
      '| W8 | NOT_VERIFIABLE | W7未过，顺序门未放行 |','',
      '快照 S：`'+snapshot['membership_snapshot_id']+'`；实际采集 `'+snapshot['membership_observed_at']+'`。全链保留 RECONSTRUCTED_LATEST_MEMBERSHIP / AS_RECORDED=false / PIT_ELIGIBLE=false / survivorship_bias_risk=true。','',
      '四日板块实际结果：','```json',json.dumps([{k:r.get(k) for k in ['trade_date','sector_count','relative_sector_known','rotation_counts','b0_counts']} for r in sector['owners']],ensure_ascii=False,indent=2),'```','',
      'Focus/Forward 结果：','```json',json.dumps({k:focus[k] for k in ['episodes','events','outcomes']},ensure_ascii=False,indent=2),'```','',
      '外审必须检查实际 Git LFS 对象字节，而非指针；验收须绑定最终候选 digest 和审查者。独立审计项与现阶段门分别登记于 12。原9/30 last-good与strict PIT不被新代理口径覆写。','',
      '源码入口：`scripts/build_r43_operational_successor.py`；候选服务：`scripts/serve_r43_candidate_preview.py --port 8768`。有独立有效外审记录后才可调用新CAS；固定生产head路径及authority均由新合同约束。','',
      '完整证据字节及SHA：','```json',json.dumps(bindings,ensure_ascii=False,indent=2),'```']
    _atomic_write(OUT/'R4_3_EXTERNAL_AUDIT_HANDOFF.md',('\n'.join(lines)+'\n').encode(),tdx_root=Path('D:/new_tdx'))
    print(json.dumps(status['final_status']))

if __name__=='__main__':main()
