# R4 外审后定点修复结果（2026-10-10）

新版已加载到真实28765，主要修复已交付；整体仍为 **EXTERNAL_ACCEPTANCE_BLOCKED**，只申请 **EXTERNAL_RECHECK_REQUESTED**。FP13的breadth503故障隔离/恢复尚未实测，正式源与模型权限门保持关闭，开发方不自签独立PASS。

BASE_SHA `5ad4bb8da48196d9e902d48ece510a15136c4210`；RESULT_CODE_SHA `35177acc7b5f412e81fecb54ac3b7cbb93319c57`；生产加载代码SHA `59430bcf4e49ee866f9111c667d5f7537bb862a1`，PID49428、端口28765。最终归档提交以10_GIT_REMOTE_READBACK_RECEIPT给出，避免自引用。T0=2026-10-09。运营Head `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；strict PIT Head `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`，前后字节一致。新增正式Owner：无。

| 包 | 根因、改变与实际证据 | 独立保留门 |
|---|---|---|
| E | 旧9路409因token拒绝机制可复现，原请求token未留证故不臆断；新脚本保留全部URL/HTTPError正文。按用户追加明确授权强关41528，再取证启动49428；真实新生产9路×3token符合预期，十二browser截图/DOM及历史/Focus/搜索分页验证 |503恢复未实测，FP13独立签收及FP14全发布未获准 |
| D | 旧全true可放行且六字段NOT_READY；修后caller dict/bool无法授生产权限，候选展示与可信入口分离、null字段SOURCE_INCOMPLETE一致 |正式registry/first-asof/Head-CAS/外审adapter缺失，生产能力关闭；旧DB22项BLOCKED |
| B | 原始Native输入SHA、窗口、成员版本和数值核验，已可用dq5/参与度/成员继续服务；不重复400空值 |六正式Producer无已准入源，恢复数0，FORMAL_OWNER_BLOCKED |
| C | 新隔离future first-capture预检：完整eligible/ineligible、独立writer grant、Owner/revision/source SHA、冻结参数和成员版本 |2290旧事件1377首获晚于T0、913重建，不能补造入组；真实分母null、无生产写权/OOS声明 |
| A |无新原件线索，保留旧证据SHA和准确有限搜索结论；无历史重算 |H21缺20日当时原件，NOT_VERIFIABLE、FORMAL_H21_BLOCKED |

集成定点测试实际退出0，63 passed（32 FEP、24 capture、7 chart/focus）；旧43/109/LOO/金额大样本未重跑。各包保留实际输入、数值、source SHA/窗口、反例与oracle/ref。新增代码和证据对应提交不冒充外审独立执行。

实际browser：六入口×1366x768/1920x1080；30162810/09失效、实际图表与Focus INVALIDATED时间线；6883499/30收盘13.240；跨入口研究T0保持；搜索/筛选461/分页1→2→1；市场宽度上涨2989、下跌2107、平盘113、未知15，分母5224、实际行情5210、Native金额19003.65亿元。实际四轴由home与市场页面显示，不把未注册/market/axes探测视为正式指标。Cohort/settlement/FEP的HTTP200+SOURCE_INCOMPLETE只算正确缺源表达。

用户追加指令“没有可视化操作入口 你直接强行关闭 旧服务 然后开启新服务 加载新代码”优先于附件正常关闭限制；强关动作和正常启动分别留证，不伪记正常退出。旧失败记录OLD_与旧browser保留，新browser在new_production。没有强关其它进程、修改ACL或创建Windows服务。

TDX只读，Accepted Head/旧冻结/AUTO与last-good未改；无10/12模拟、真实评分、新模型权限、外部复权或交易。未来真实capture沿用DD R2.2与独立准入。Git push/远端SHA与Drive bytes/SHA另列09/10收据，测试和推送都不代表独立验收。


## 续轮更新

详见11_CONTINUATION/CONTINUATION_RESULT.md：E的双尺寸受控503验证通过；D隔离DB50项通过；C已接实际DD预检。正式来源及FP14外部验收仍阻塞。
