# R2 连续日更接入合同

上一阶段 Focus 价格路径/到期结果读域已通过来源、IAB、联合回滚及正式 CAS。依照 R2-05 原授权继续修复；旧阶段证据冻结，不覆盖 R1/R2 收据。

本阶段先完成独立连续 driver：从逐日接受的 states、交易日历、实际 RAW 和本地 GBBQ 驱动新 journal 版本，历史绑定不变，失败不推进 production。真实既有两日隔离演练；无新交易日零请求 no-op。每步分别记录 DM01 输入、owner/field QA、projection、snapshot/UI、journal、Forward due；只能对实际跑过的完整步骤给 PASS。

完整日链的已知额外缺口：旧 FP06 构建器从在线快照取目标日，会在 source 已推进、joint 尚未切换时仍取旧日；旧 FP02 builder 更新 legacy pointer，joint reader 仍读旧版本。需做 successor 修复，不能以测试或单独 journal 演练关闭全链。

边界：TDX 只读、E/F 临时空间、项目产物原子写；corrected 历史不冒充 strict PIT。9/29 板块成员首获源尚未查到，不能把9/30成员倒灌9/29。旧PG不可核对独立保留。自动写入准入与只读发布分离；尚未验收的写能力不放开。

状态：IN_PROGRESS。下一关：连续 driver 实源两日验证，再接 snapshot/UI 全链。
