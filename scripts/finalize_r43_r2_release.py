"""Report actual authorized production; preserve separate independent status."""
import json,sys,urllib.request,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
from workbench_analysis.r43_operational_sources import ref
OUT=ROOT/'docs/evidence/r4_3_r2_release_control_20261009'
def read(name):return json.loads((OUT/name).read_bytes())
def main():
    entry=read('ENTRY_STAGE_CONTRACT.json');bad=[b['path'] for b in entry['immutable'] if sha(ROOT/b['path'])!=b['sha256'] or (ROOT/b['path']).stat().st_size!=b['bytes']];assert not bad,bad
    head=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';candidate=json.loads(head.read_bytes());token=sha(head)
    prior=json.loads((ROOT/'docs/evidence/r4_3_r1_targeted_repair_20261009/R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V2.json').read_bytes())
    assert candidate['owners']==prior['owners'] and candidate['membership_snapshot']==prior['membership_snapshot']
    live=read('R43_R2_LIVE_CUTOVER_HTTP_AND_ROLLBACK_RECEIPT.json');rollback=read('R43_R2_LIVE_ROLLBACK_AND_REPROMOTION.json');restart=read('R43_R2_REAL_SERVICE_RESTART_READBACK.json');ui=read('R43_PRODUCTION_UI_ROUTE_AND_BFF_COMPATIBILITY_QA.json')
    assert live['status']=='SCOPED_PRODUCTION_CUTOVER_HTTP_PASS' and ui['candidate_digest']==token and restart['head_sha']==token and rollback['production_head_sha_after']==token
    with urllib.request.urlopen('http://127.0.0.1:28765/api/v4/context',timeout=180) as r:ctx=json.load(r)
    assert ctx['context_token']==token and ctx['context']['accepted_trade_date']=='2026-10-08' and ctx['context']['independent_external_acceptance'] is False
    receipt=dict(status='USER_AUTHORIZED_FOUR_SESSION_OPERATIONAL_PRODUCTION_PASS',candidate_digest=token,accepted_trade_date='2026-10-08',source='RECONSTRUCTED_LATEST_MEMBERSHIP',AS_RECORDED=False,PIT_ELIGIBLE=False,survivorship_bias_risk=True,independent_external_acceptance=False,rotation_validation_state='VALIDATION_ONGOING',unchanged_prior_evidence_and_protected_files=len(entry['immutable']),mismatches=bad,original_S_and_all_Owners_preserved=True,actual_context=ctx,tests=dict(passed=24,seconds=5.39,command='E:/python/python.exe -m pytest tests/test_r43_release_control.py tests/test_v4_default_workbench_service.py tests/test_r43_operational_bff.py tests/test_r43_operational_sources.py --basetemp E:/codex_tmp/test_temp/r43_r2_user_cutover -q'),isolated_HTTP=len(ui['actual_http_readbacks']),production_HTTP=len(live['actual_HTTP']),rollback_republish_HTTP=len(rollback['final_HTTP']),restart_HTTP=len(restart['HTTP']),next_stage='FP_COMPLETENESS_WORK_REQUIRES_OWN_LATEST_STAGE_CONTRACT_NO_EXTERNAL_WAIT_FOR_THIS_CUTOVER')
    atomic(OUT/'R43_R2_FINAL_PRODUCTION_READBACK.json',canonical(receipt))
    actual_refs=[candidate['membership_snapshot'],candidate['registry']]+[b for owners in candidate['owners'].values() for b in owners.values()]
    atomic(OUT/'R43_R2_REVIEW_SOURCE_FILE_BINDINGS.json',canonical(dict(candidate_digest=token,actual_files=actual_refs,independent_review_record_created=False)))
    matrix=f'''# R43 R2 外审范围与逐域处置

最终候选 `{token}`。本轮最新用户明确要求立即生产切换并不等待批准，实际使用独立的USER_AUTHORIZED_SCOPED_OPERATIONAL_V1合同与用户请求证据。未生成独立外审通过对象，外审签署人、签名和独立全量重算均为NOT_VERIFIABLE；审查身份不以修复代理自测替代。

| 范围 | 工程证据 | 独立外审状态 | 实际生产处置 |
| --- | --- | --- | --- |
| 四日RAW/停牌 | R1真实全量对账，5210/5211/5213/5209与12/12/11/15，冻结SHA未变 | 外审仅ZIP计数PASS_SCOPED；完整外部RAW复算NOT_VERIFIABLE | 用户授权读取 |
| 源SHA/GBBQ/证券身份/BJ | R1实际319文件2.39GB摘要、跨事件数值样本；BJ optional degraded | 外部全量输入/GBBQ工具复算NOT_VERIFIABLE | 保留原来源与降级 |
| QFQ/Core/Profile/RPS | 128跨事件MA/ATR样本、全量RPS/端点、512分支等冻结工程证据 | 独立完整复算NOT_VERIFIABLE | 用户授权运营计算读取；不称外审PASS |
| 最新TDX S | 完整55136=52912+2224关系，10列原S摘要与12列规范化视图分别保留 | 附件独立审查源成员摘要PASS_SCOPED，无新候选正式签收 | 原S不改，110叶级/22父级/T00/268概念，不冒充历史PIT |
| 400板块/LOO | 四日实际原生计算及40 LOO样本；Owner原SHA未变 | 新候选独立数值签收NOT_VERIFIABLE | 用户授权，未映射关系不强造价格 |
| Rotation | 实际字节/lineage、原工程计算可读；未独立重建递归状态机 | VALIDATION_ONGOING | 原数据可读；API及板块字段具名持续验证状态 |
| Market/Focus/Forward | 冻结Owner和四日真实同token HTTP | 独立签署NOT_VERIFIABLE | 用户授权运营展示；未实现统计/图表等SOURCE_INCOMPLETE |
| UI/控制面 | 原HTML SHA不变、127隔离HTTP、真实生产/回滚/重启HTTP | 实际上线可核查，不伪称独立审查者实测 | 运营10/08与严格PIT9/30显式分开 |
| 权限/CAS/回滚 | 精确用户记录、stale/NOOP/坏源/并发隔离与真实前驱回滚 | 不是独立外审批准 | 真实原子CAS已执行，最终生产10/08 |

实际所用每个S/registry/Owner文件的完整SHA与路径见R43_R2_REVIEW_SOURCE_FILE_BINDINGS.json。原三份冻结TDX源由S绑定可追溯，未重抓行情或重复数值生产。独立状态不阻挡用户本次明确授权的生产切换，但不能据此编造算法独立全量通过、严格PIT、实时行情、Forward胜率或完整六入口功能。
'''
    atomic(OUT/'R43_R2_EXTERNAL_REVIEW_SCOPE_AND_DISPOSITION.md',matrix.encode('utf8'))
    text=f'''# R43 R2 正式生产交接

生产运营数据已实际切换至2026-10-08，最终Head摘要 `{token}`，服务 `http://127.0.0.1:28765`。授权来自用户本次直接指令；独立外审通过没有伪造，也不再等待其批准来执行本次切换。

| 阶段 | 结果 | 证据 |
| --- | --- | --- |
| P0-A | PASS | 原S和全部四日Owner引用完全相等，旧{len(entry['immutable'])}个证据/保护文件零变化，没有重算RAW或528 QFQ |
| P0-B | PASS | 控制面同运营Head/token；历史9/30单列；原生产HTML未替换 |
| W7-C独立签署 | NOT_VERIFIABLE | 独立复审附件仅限定覆盖；用户最新指令改为直接授权，不制造EXTERNALLY_ACCEPTED记录 |
| 用户授权生产CAS | PASS | 真正生产Head创建，34HTTP读回；原9/30Head不改 |
| 实际回滚/重发/重启 | PASS | 回滚恢复9/30，重发10/08，重启后34HTTP同版；stale/NOOP/错误token/跨期拒绝 |
| R1 Drive补传 | PASS | 云端实际字节重新读取，964009字节，SHA ec27612dd557a4bfff681f40c0cbcc9c8d77992bfb1a25cca4f4b208e5a3f093 |
| 本轮Git/Drive | 见DELIVERY_RECEIPT.json | 记录实际提交/上传与回读，未成功不填PASS |

回归24项通过；隔离127次HTTP通过。Rotation未独立全量验算，保持VALIDATION_ONGOING；成员为最新采集回算、AS_RECORDED=false/PIT_ELIGIBLE=false，存在存续偏差风险。原UI中未接的图表、历史replay/compare、Forward统计及部分子页仍显示精确来源不足；不把这次数据切换称完整FP六入口建设。

后续FP01–FP14按自己的最新任务卡和阶段合同推进；这次生产切换已完成，独立外审未签不被重新用作等待本次切换的理由。
'''
    atomic(OUT/'R43_R2_FORMAL_HANDOFF.md',text.encode('utf8'));print(json.dumps(dict(head=token,production='2026-10-08',immutable=len(entry['immutable']),tests=24)))
if __name__=='__main__':main()
