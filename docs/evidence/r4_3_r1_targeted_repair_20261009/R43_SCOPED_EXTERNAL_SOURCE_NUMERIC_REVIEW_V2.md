# R4.3 R1 限定来源/数值工程复核 V2

结论：限定工程数值复核 PASS；独立外部签收 NOT_VERIFIABLE；生产准入 NOT_GRANTED。本报告由执行修复任务的工程代理生成，不是独立外部审查者签收，绝不签发 EXTERNALLY_ACCEPTED_R43_OPERATIONAL。

可复现命令：`E:/python/python.exe scripts/audit_r43_r1_scoped_numeric.py`。全部输出进入新的 R1 证据目录，原冻结证据不覆盖。运行源码、派生执行源码 SHA、各命令退出码及实际文件 SHA 位于 R43_R1_SCOPED_NUMERIC_REVIEW_RECEIPT.json、R1_EXECUTION_*.json 和 R43_R1_ACTUAL_BYTES_FULL_SHA.json。

实际读取 hydrated Git LFS 数据字节，拒绝 pointer；完整 SHA 覆盖成员、Owner、原冻结 native ZIP/GBBQ、相关绑定和冻结证据。未读取或重组 Drive 17 段备份，本报告不冒称 Drive 外部复算。保留原 9/30 快照保护绑定。

独立读原 S 的所有55,136行确认其字段全集只有10列，确实不含 industry_level/primary_industry_rank_eligible。行业层级由 source 中 DERIVED_PARENT 推导；当前 capture 新增12列与 legacy 冻结S schema不同，不能据此伪造原 legacy verifier失败。该函数矛盾的真实失败/修复以 P0-A 新收据为准。原关系完整digest和原 9/30 50,162关系/378板块实际SHA均保持。

重新执行原独立数值 oracle（输入保持冻结，输出定向新目录）：四日 native RAW 与停牌全量对照、T-1/T-3、128 个跨事件/短上市/停牌/普通真实样本的当前与前驱 MA/ATR/QFQ、全量 RPS 排序与可用精确端点、512 Profile 分支、dated daily limit Decimal 校验。详见新 03/05 系列结果。

新独立算法直接解析三份native冻结源并还原所有55,136个10列字典，完整digest与原S完全一致；不导入生产parser/normalization。核对55,136=52,912+2,224关系、多对多key唯一性，覆盖全部401源组。实际数据为110合法叶级、22 derived父级、268概念，另1个T00未分类placeholder；旧收据与任务卡的“23父级”真实 FAIL，不把 T00 改名成不存在的第23父。独立审计项 R43-R1-CROSS-TAXONOMY-DENOMINATOR 的事实已单独记录。每日期 400 板块成员集合与 ret1/5/20/60 中位数、breadth 与 MA20 width 直接重算；40 个 LOO 样本重新排除目标股票取独立中位数并核对实际相对替代值。T00 只有源关系且无合法成员，不造价格。父级分群保留；未映射按关系分母、北交所 optional degraded 不擅改。

运营回算 lineage、AS_RECORDED=false、PIT_ELIGIBLE=false、survivorship_bias_risk=true 在实际 native、relative、Rotation、enriched Profile 行逐一校验。Rotation 仅复核实际字节/lineage，未以新的独立实现重推完整状态机；未声称严格历史 PIT、盘中事件或成熟 Forward 统计。

下一门：最终实际候选 digest 的独立外部来源/数值/兼容范围签收。旧版本工程 PASS 或旧外审不替代新候选签收；本工程复核不能满足该身份门，不能据此执行生产 CAS 或启动 FP-01～FP-14。
