"""Evidence-based ingress matrix and next work packages; no full-product PASS."""
import json,sys,hashlib,zipfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OUT=ROOT/'docs/evidence/r43_r2_fp_entry_20261009'
PACKAGES=[
('FP01','生产语义与版本化发布合同','限定运营读取与旧权限隔离；用户原始事件找到','独立回读原会话；未来权限更改必须调用 USER_PERMISSION_ORIGINAL_EVENT_GATE_V2，并独立校验范围与发布门'),
('FP02','生产数据总线','10/08 Head 正常、5224画像、5209行情','独立日期的 Source QA/身份/生命周期/GBBQ 与 operational successor builder；不能扩写固定四日 DATES'),
('FP03','BFF及字段合同','具体缺失 Owner/阶段、错误 token409、越界日期400','补全各缺失 route 的真实 producer/schema；数值/单位/窗口/时点抽样核验'),
('FP04','六入口框架','六导航可达、10/08日标、首页运行异常修复','补齐独立区块失败隔离与中文显示；原六入口联调1366/1920/Edge'),
('FP05','今日总览与市场四轴','四轴可读；变化/风险/net-information缺失明确','接入真实变化/风险/去重净信息 Owner；无源不能显示0或无风险'),
('FP06','板块研究与轮动','400板块、煤炭32成员；时间线缺失不再阻断成员','绑定 dated timeline/overlap owner；递归Rotation独立oracle另项，不声称严格历史PIT'),
('FP07','个股画像与图表','真实代码搜索与F/R/成员关联可读；图表Owner明确缺失','复用真实历史/原生调整坐标，接入日周月chart；证券中文名称/别名及H解释Owner缺口定点修复'),
('FP08','Focus生命周期','2477关注对象和真实事件读域可读','逐字段检查Episode/T0/Anchor/Observation/outcome；自动写入与读域独立门'),
('FP09','市场指数涨跌停与事件','四轴已接；breadth/indices/limits/ladders路由缺失明确','复用冻结RAW/价格规则/market input_bindings中的真实Owner，适配各子路由；逐项数值对账'),
('FP10','Forward结算与风险研究','statistics/plans/fep/settlement缺失Owner已登记','接入真实enrollment/期限/结算/FEP权限链；统计未成熟保持pending，不伪造分母'),
('FP11','诊断与旧模块','sources当期可读；health/fep子页缺失明确','接入dated健康/源/规则/FEP诊断；旧日更脚本显式迁移，不能误改PIT Head'),
('FP12','PIT回放与比较','当期replay/compare无Owner；旧9/30独立上下文保持','接入freeze/as_of/compare合同；四日运营重建不冒充严格历史PIT'),
('FP13','全站浏览器验收','IAB六入口、搜索、详情和成员实际截图/DOM','完成每域真实功能、数值、Edge1366/1920、离线/失败隔离/性能；不能以HTTP200宣布通过'),
('FP14','生产发布与日常运营','限定适配器原端口重启读取成功；数据Head未改','FP13完整合同过门后独立UI/read联合CAS发布、失败回滚与真实每日successor；当前不授予FULL_PRODUCT')]

def main():
    live=json.loads((OUT/'LIVE_HTTP_AND_RESTART_READBACK.json').read_bytes())
    qa=json.loads((OUT/'R43_R2_CONTROL_STATUS_NAMESPACE_QA.json').read_bytes())
    daily=json.loads((OUT/'R43_R2_NEXT_SESSION_PIPELINE_QA.json').read_bytes())
    entry=json.loads((OUT/'ENTRY_STAGE_CONTRACT.json').read_bytes())
    assert all(sha(ROOT/p)==h for p,h in entry['protected'].items())
    tasks=OUT/'next_tasks'
    table=['# FP01–FP14 最新合同入场与缺口矩阵','',
           '最新 Drive 合同 17tbCyE-gYhe2pwoy2gLFeoNNwq9NPKxu 已读取；原文存 DRIVE_LATEST_FP_TASKS.md。最新 R43 交接 1fXrGxfkNq0rSqPtPkmaI1zt2ezVH0f-T 已回读。父设计 REV2 §62A–§69、§81.2 与既有升级/失败记录仍适用。',
           '', '本轮为原合同下的第一批工程入场、控制面修复及实际缺口QA，不改写设计。已有 FP 历史工程成果继续沿用，不把旧阶段测试或本轮数据读取计作10/08完整FP验收。FP14历史BLOCKED保持。',
           '', '| 包 | 实际状态/证据 | 下一工作包 | 正式验收 |','|---|---|---|---|']
    existing=list((ROOT/'docs/evidence/fp01_20261008/tasks').glob('*.md'))
    for code,title,known,next_task in PACKAGES:
        number=code[2:];contract=next((p.relative_to(ROOT).as_posix() for p in existing if p.name.startswith(number+'_')), 'DRIVE_LATEST_FP_TASKS.md')
        table.append(f'| {code} {title} | {known} | {next_task} | NOT_GRANTED_BY_THIS_RUN |')
        text=f'# {code} 下一轮定向任务卡\n\n原合同：`{contract}`；最新 Drive 合集：`17tbCyE-gYhe2pwoy2gLFeoNNwq9NPKxu`。这是一张原合同续办卡，不另造设计或降低范围。\n\n现状：{known}。\n\n执行：{next_task}。沿用未变的 S/四日 Owner 字节，不重抓551MB ZIP，不修改 TDX，不覆盖旧 PIT，不混用9/30替代10/08。\n\n验收：按原 {code} 合同 feature→producer→source→API→UI→test→screenshot 逐项核验；用真实来源、上下文token、数值抽样及浏览器证明。缺失Owner精确标注，不能以HTTP200、工程测试或统计未成熟冒充整体通过。记录阶段合同、证据、验收和下一阶段，完成后commit+push及Drive归档回读。\n\n当前正式结果：NOT_GRANTED_BY_THIS_RUN；外部数值与权限来源审计单独跟踪。下一步仅沿原调度依赖执行，不能跳过FP13进入完整FP14发布。\n'
        atomic(tasks/(code+'_NEXT_TASK.md'),text.encode())
    table+=['','## 真实HTTP路由覆盖','', '| 路由 | HTTP | 数据状态 | 缺失Owner/阶段 |','|---|---|---|---|']
    for r in live['records']:
        p=r['payload'];gap=p.get('gap') or {};route=r['url'].split('28765')[-1].split('?')[0]
        table.append(f"| {route} | {r['status']} | {p.get('status','ENVELOPE_READ')} | {gap.get('missing_owner','')} {gap.get('task_stage','')} |")
    table+=['','六入口真实生产浏览器快照见 LIVE_BROWSER_SIX_ENTRY_QA.json 和 live_browser_*.jpg/.txt。当前使用 IAB；Edge专用、两种尺寸完整全站验收尚未授予。首页已暴露并修复原JS的缺失列表.length异常；板块缺失timeline/overlap不再阻断实际成员。',
            '',f"P0-A：{qa['status']}，{len(qa['records'])} 隔离HTTP；原端口实际读回 {len(live['records'])} HTTP，含409/400反例。P0-B：本机原始用户事件可回读，独立外部签收未授予。P0-C：{daily['status']} / {daily['reason']}，last-good={daily['last_good_trade_date']}。",'',
            '下一阶段：上述定向工作包逐包工程和外部验收；完整FP01–FP14尚未通过，Rotation全状态机验证独立跟踪。']
    atomic(OUT/'FP01_FP14_LATEST_CONTRACT_INGRESS_AND_GAP_MATRIX.md','\n'.join(table).encode())
    result=dict(contract_id='R43_R2_FP_ENTRY_ACCEPTANCE_V1',recorded_at=datetime.now(timezone.utc).isoformat(),
                engineering_acceptance='SCOPED_CONTROL_REPAIR_AND_FP_INGRESS_PASS_WITH_REGISTERED_DEBT',
                full_product_acceptance=False,independent_external_acceptance=False,
                control_QA=qa['status'],live_HTTP=len(live['records']),next_session=daily['status'],
                authority_origin='LOCAL_ORIGINAL_USER_EVENT_REPLAY_VERIFIED_EXTERNAL_REPLAY_PENDING',
                protected=entry['protected'],next='PER_PACKAGE_NEXT_TASKS_UNDER_ORIGINAL_CONTRACTS')
    atomic(OUT/'STAGE_ACCEPTANCE.json',canonical(result))
    # Finalize evidence through atomic replacement, including captured screenshot bytes.
    for p in OUT.rglob('*'):
        if p.is_file():atomic(p,p.read_bytes())
    print(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':main()
