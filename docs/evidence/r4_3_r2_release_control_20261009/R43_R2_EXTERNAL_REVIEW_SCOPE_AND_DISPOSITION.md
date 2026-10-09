# R43 R2 外审范围与逐域处置

最终候选 `e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8`。本轮最新用户明确要求立即生产切换并不等待批准，实际使用独立的USER_AUTHORIZED_SCOPED_OPERATIONAL_V1合同与用户请求证据。未生成独立外审通过对象，外审签署人、签名和独立全量重算均为NOT_VERIFIABLE；审查身份不以修复代理自测替代。

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
