# 当前生产硬阻断与非阻断 V1

当前已验证的行情、当期市场四轴、板块强度与重叠、个股现有因子/趋势、Focus corrected 读域和 Forward 计划读域继续开放。FULL_PRODUCT_RELEASE_PASS 未取得；原 60/110 字段范围不升级。

以下阻断对应能力，均不是全站总开关：

- 板块轮动：378/378 output_state 仍 UNKNOWN；9/29 日期归属的可信成员未绑定，breadth_delta3 也需要更长的真实日期链；seed_width 缺 Base/Seed 原生信号。emergence、confirmation、maturity、health 等未发布的 Owner 能力不能用强度值替代。
- 个股结构：basic_breakout_state 全 5213 UNKNOWN，其中 5037 缺精确前日 ATR 发布和跨基准变换，176 还缺接受复权；support_state 缺完整接受来源元数据。relative_market_state 需要的历史增量因子未绑定；relative_sector_state 缺可接受 LOO 覆盖。不能把单日 rel_market_5 等同于完整 relative_state。
- waiting_for/invalid_if/H1/H2：没有显式 Owner 的条件不得猜测；缺失谓词列表只作依赖证据。任意代码的 NOT_IMPLEMENTED、OUTSIDE_UNIVERSE 统一来源表达仍有工程工作，本轮没有把它列为完成。
- 当前 LOO、生命周期与真实两日板块比较仍需 Owner 输入和算法验收。板块 amount、rank_velocity、entered/exited 等有潜在聚合或映射路径，尚未证明是纯 adapter 漏读，保留单独字段债务。

可延期的证明/样本积累：旧 9/28～9/30 严格 PIT 仍 0/3；首次观察时间不能回填首次可用时间。Forward 117 入组、585 计划、117 T0 冻结，真实 due=0，未成熟不阻断今日研究；真实到期前不能用夹具验收代替。Focus 766 观察的 READY66/PARTIAL572/UNAVAILABLE128 不改账，前日缺的原生 Core 不倒灌。

可选来源或额外能力：可信事实消息、分钟触板/炸板、外部竞争假设源。暂无可靠来源时按域降级，不进行新网络采集，不作为全站开放条件。

完整的 50 行版本化台账见 R2_VERSIONED_FIELD_DEBT_LEDGER.json。分类是本轮初次分流，不等于已完成所有 Owner 设计：其中没有一项因测试通过被自动关闭。parent_episode_id 的 null 可能是合法根 episode，仍需重入样本确认 nullable 语义，不能直接当成未实现。
