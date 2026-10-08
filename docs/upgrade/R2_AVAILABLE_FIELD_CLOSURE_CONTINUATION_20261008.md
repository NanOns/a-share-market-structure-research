# R2 已有真实源字段逐项闭环

依据外审 R2-03/R2-07 和总任务卡 R2；接续 FIELD_INVENTORY_V5（110 行，16 已验收），独立审计 AUD_R2_AVAILABLE_FIELD_CLOSURE。不能以矩阵中有数值等同业务域完成，不能把不可判定条件映射成明示等待或失效条件。

已定位工程缺口：股票核心因子投影只读 advanced/sector registry，遗漏已存在的 V4_03 / V4_04 注册表单位，真实值仍正确但单元 unit 错标 OWNER_UNIT_NOT_DECLARED。版本合同 R2_BOUND_OWNER_UNIT_PROJECTION_V1 只读取并冻结实际注册表映射，不缩放数值、不变更因素算法。调整价格字段标原生调整坐标，收益小数与百分点分开。已接受 corrected 历史不得因注册表写 PIT 就升级 AS_RECORDED。

范围：逐一证明当前源已可用字段的源适配、日期、单位、原生值、真实 IAB 点击。板块 RS5/20 和 participation median、同日 overlap/独有成员；股票压缩、相对市场、风险规则与身份/行业概念；Focus 类型化状态/观察/实际到期；市场与诊断、corrected 比较、首页字段分别建立数值或结构 oracle。数值不适用项以 structural_oracle 验收，numeric_oracle_applicable=false，不机械置 true。缺源项独立 owner/合同/证据归因。

入口 Phase 0 DEGRADED_PASS；TDX 全路径只读，无 scanner。每个真实就绪字段必须实源 oracle、IAB 来源单元和两桌面；变化需新 snapshot/UI 联合 CAS 失败回滚与日更准入后继 NOOP；既有源值不变须全量核对。M10 Amount A、严格历史 PIT、未获历史成员/模型 known_at、分钟触板及官方事件均独立开放。

阶段 IN_PROGRESS；下一关：单位元数据适配和各字段实际源 oracle。
