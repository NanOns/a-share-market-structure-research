# R4 外审后定点修复结果（2026-10-10）

本轮代码修复与范围化证据已交付；整体仍为 **EXTERNAL_ACCEPTANCE_BLOCKED**，只申请 **EXTERNAL_RECHECK_REQUESTED**。E 旧生产进程未正常退出，不能宣称部署完成。开发方没有自签正式 Owner 或发布门。

BASE_SHA `5ad4bb8da48196d9e902d48ece510a15136c4210`；RESULT_CODE_SHA `5ad4bb8da48196d9e902d48ece510a15136c4210`。最终归档提交由 Git 远端读回收据给出，避免报告自引用。T0=2026-10-09；运营 Head `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`，严格 PIT Head `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`，前后字节一致。正式新增 Owner：无。

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
