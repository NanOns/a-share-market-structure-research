"""Read back scoped artifacts and retain explicit failed release gates."""
import collections
import gzip
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_three_day_repair_r1 import OUT,load,DAYS
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import validate


def gz(binding):
    assert ref(binding['path'])['sha256']==binding['sha256']
    return [json.loads(l) for l in gzip.open(ROOT/binding['path'],'rt',encoding='utf8')]


def main():
    replay=load(str((OUT/'core_owner_r2/OWNER_REPLAY_PER_DAY.json').relative_to(ROOT)))
    beforeafter=[];matrix=[];failures=[]
    for r in replay:
        rows=gz(r['owner']);prior=gz(r['prior_core_in_target_coordinate'])
        adjusted={x['security_id']:x for x in load(r['sources']['adjusted']['path'])['rows']}
        reasons=collections.Counter();known=collections.Counter()
        for row in rows:
            ready=adjusted.get(row['security_id'],{}).get('adjustment_readiness')=='READY'
            for field,cell in row['fields'].items():
                if cell['value'] is not None:known[field]+=1
                if cell.get('window_end_trade_date') and cell['window_end_trade_date']>r['trade_date']:failures.append([row['security_id'],field,'FUTURE_WINDOW'])
                if not ready and cell['value'] is not None:failures.append([row['security_id'],field,'CAPABILITY_BYPASS'])
            if row['fields']['atr20']['value'] is None:reasons[row['fields']['atr20']['unknown_reason']]+=1
        beforeafter.append(dict(trade_date=r['trade_date'],staged_core_rows=len(rows),staged_known=dict(known),
            staged_prior_atr20_known=sum(x['fields']['atr20']['value'] is not None for x in prior),
            atr20_unknown_reasons=dict(reasons),live_owner_replacement=False,live_breakout_unknown_unchanged=True))
        matrix.append(dict(**r,CORE_PROFILE='OWNER_NOT_MATERIALIZED_IN_THIS_REPLAY',
            STRUCTURE='OWNER_NOT_MATERIALIZED_IN_THIS_REPLAY',historical_membership='EXACT_20260930_ONLY',
            release_acceptance='NOT_GRANTED',published_at=None,publication_timestamp_reason='STAGING_ONLY_NOT_FORMALLY_PUBLISHED'))
    write(OUT/'B_THREE_DAY_SOURCE_AND_OWNER_MATRIX.json',matrix)
    write(OUT/'REAL_FIELD_BEFORE_AFTER.json',beforeafter)
    sector=load('config/v4_sector_operational_authority_v1.json');native=gz(sector['native'])
    reason_counts=collections.defaultdict(collections.Counter);per_sector=[]
    for row in native:
        reasons={k:v.get('reason_code') for k,v in row['fields'].items() if v.get('value') is None}
        for k,v in reasons.items():reason_counts[k][str(v)]+=1
        per_sector.append(dict(sector_id=row['sector_id'],target_trade_date=row['target_trade_date'],missing_dependencies=reasons))
    write(OUT/'OWNER_DEPENDENCY_ROOT_CAUSE.json',dict(sector_rows=len(native),per_sector=per_sector,
        sector_field_reason_counts={k:dict(v) for k,v in reason_counts.items()},
        producer_binding=ref('scripts/build_fp06_sector.py'),
        missing_producer_arguments=['prior','prior_memberships','prior_date','prior_sector_rows','seed','seed_capability','prior_seed'],
        current_seed_root='SOURCE_PRESENT_NOT_INGESTED_OR_OWNER_NOT_MATERIALIZED_REQUIRES_ORIGINAL_BASE_SEED_BINDER',
        history_member_root='EXACT_DATE_MEMBERSHIP_UNBOUND_DISTINCT_FROM_FIRST_AVAILABLE_PROOF',
        stock_prior_core='NOW_STAGED_IN_TARGET_COORDINATE_NOT_FORMALLY_ACCEPTED_OR_WIRED_TO_STRUCTURE',
        remaining=['CORE_PROFILE daily output','accepted transformation/previous profile binder','Base/Seed/Rotation original producer','LOO','conditional Owner contracts']))
    joint=load('config/v4_joint_release_authority_v1.json');validate(ROOT,joint)
    baseline=load(str((OUT/'ENTRY.json').relative_to(ROOT)))['backup']
    changed=[p for p,b in baseline.items() if ref(p)['sha256']!=b['sha256']]
    assert not changed and not failures,(changed,failures)
    noop=load('runtime/research_daily/DAILY_LATEST.json')
    write(OUT/'DAILY_NOOP_READBACK.json',noop)
    write(OUT/'E_POST_RELEASE_READBACK_AND_ROLLBACK.json',dict(result='NO_RELEASE_GATE_NOT_PASSED',
        live_joint_validation='PASS',baseline_authority_changes=changed,staging_capability_and_date_failures=failures,
        no_new_day=noop['status'],source_requests=noop['source_requests'],pointer_preserved=noop['pointer_preserved'],
        new_successor_activated=False,new_successor_rollback='NOT_EXECUTED_NO_ACCEPTED_SUCCESSOR',
        wrong_date_adjustment_owner_fault_drills='NOT_EXECUTED_THIS_ROUND',browser_smoke='NOT_EXECUTED_THIS_ROUND'))
    write(OUT/'D_HISTORICAL_CORRECTED_VS_PIT_SEPARATION.json',dict(strict_pit_pass_days=0,corrected_owner_staged_days=list(DAYS),
        first_observed_backdated=False,model_published_at_historically_proven=False,
        first_available_unproven_does_not_imply_raw_absent=True,live_T0_modified=False))
    write(OUT/'F_INDEPENDENT_AUDIT_DISPOSITION.md',('''# 三日修复 R1 分域验收处置

本轮仅取得源事实盘点与隔离 CORE 补算的限定通过；全任务未完成，E1–E6 全量及发布门槛未通过，不是外部验收。

- PASS：三日接受 RAW 与原始 ZIP 的 OHLC/股数/元金额 93804 项核对；身份有效区间 15669 行；可接受原生复权四价 60424 项。
- PASS（限定）：原 CORE_FACTOR_V1 按目标日重建及前日同目标坐标 CORE；MA20/ret5/ATR20 独立算式复核，详见 core_owner_r2。保留 176/日无复权权限及停牌/短窗口 UNKNOWN。未生成完整 Profile、突破/支撑、Base/Seed 或 Rotation。
- PASS（限定）：六个 Focus 样本以原始 GBBQ 参数计算仿射变换和收益；重新读取 297/469 observations；117 入组、585 PENDING、due=0。
- PASS：真实日更 NO_NEW_COMPLETED_SESSION，source_requests=0；当前联合校验通过，基线权限及线上指针字节一致。
- FAIL：E2/E3/E4 全量 Owner 消费闭环，E5 全部语义与异常矩阵尚未完成。历史成员未绑定和未执行 producer 与严格 PIT 未证明分开登记。
- NOT_VERIFIABLE：9/28、9/29 精确日期板块成员、历史首获证明；当前本地搜索不构成全硬盘或所有公开来源不存在的证明。
- NOT_EXECUTED：新 successor 发布、对应回滚与故障矩阵、浏览器验收；未满足发布准入，未改生产。

首次隔离补算候选因缺接受复权权限门被明确拒绝，旧输出保留；R2 加入逐证券接受权限门及目标坐标日边界。数值结果不能直接升级生产能力。

阶段记录偏差：首轮 B entry 在进程开始后补记，已如实记录；R2 entry 在计算前写入。完整跨域数据源时间元数据、模型发布时间与来源审核仍未闭合。

下一步：先完成原 Base/Seed、Core Profile/结构 producer 的真实依赖绑定及按日生产，再进行全字段正反边界样本、板块五例比较、受控发布/回滚。此次提交推送仅归档，不能当下一门槛外部签收。
''').encode('utf8'))
    write(OUT/'CROSS_CUTTING_AUDIT_ITEMS.json',dict(items=[
        dict(id='THREE_DAY_ADJUSTMENT_CAPABILITY_SCOPE_R1',scope='All historical owner replays',evidence=ref(OUT/'B_FIRST_ATTEMPT_REJECTION.json'),status='OPEN',acceptance='Per-security accepted readiness, source event interval and model binding independently reconciled; original staging remains rejected'),
        dict(id='THREE_DAY_OWNER_BINDER_COMPLETENESS_R1',scope='Base/Seed/Profile/Structure/LOO across dates',evidence=ref(OUT/'OWNER_DEPENDENCY_ROOT_CAUSE.json'),status='OPEN',acceptance='Original producers published per target and consumers validated; not satisfied by numeric factor replay'),
        dict(id='THREE_DAY_FULL_SOURCE_DISCOVERY_R1',scope='Physical sources, effective memberships and historical model timestamps',evidence=ref(OUT/'LOCAL_SOURCE_DISCOVERY.json'),status='OPEN',acceptance='Complete configured source roots and supported historic membership contracts; no absence claim from bounded search')]))
    print(json.dumps(dict(result='SCOPED_CORE_STAGING_PASS_FULL_REPAIR_INCOMPLETE',per_day=beforeafter,sector_rows=len(native),capability_date_failures=failures)))


if __name__=='__main__':main()
