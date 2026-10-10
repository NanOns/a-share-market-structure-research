# 整体打包 S1 实施合同

合同：`V4_WINDOWS_PACKAGE_S1_EXECUTION_V1`。用户于2026-10-10明确要求按最新设计开始实现；沿用 `V4_WINDOWS_FULL_PACKAGE_DESIGN_R2_1_20261010`，精确设计身份见 S0_STAGE_RECEIPT.json。S0代码与证据已在 `0fd1f52f` 提交推送，结果为 S0_PASS_ENGINEERING_CONTRACT_AND_ISOLATED_BOUNDARIES。

本门交付 Windows x64 PyInstaller onedir 主EXE，内置 Python、实际可达模块、原目录映射、合同原件与网页资源，以及本地 Git 历史校验组件。程序目录位于 G 盘版本目录，工作区为已核验的独立 G 盘数据根；临时、测试、构建均在 G 盘。

验收分开记录：源码回归、冻结EXE运行/事务模拟、真实Win32托盘的程序驱动动作、冻结EXE归档输入完整数值日更。前两类不能替代后者。托盘程序驱动功能检查不能写成真实鼠标点击、两个物理屏幕或Windows重启证明。

完整日更使用 `V4_EXPLICIT_ARCHIVE_CAPTURE_REPLAY_V1` 明确回放：把原始ZIP字节重新捕获到测试工作区，SHA核验后由原提取器、来源准入、Owner数值算法、周月QA、CAS及六HTTP回读执行。原来源观测时间保留；本次执行、回放捕获时间单列。产物及工作区归档标为REPLAY，first_capture_claim=false，不写真实Head，不授予PIT或正式Owner准入。

故障矩阵要求：原队列对超时执行八次有界尝试后终止；来源SHA失配阻断且无盲重试；合法数值候选的旧CAS拒绝、错误回读恢复前驱；EXE在CAS待回读阶段实际异常退出，下一次同身份EXE按原recover恢复，然后合法发布至COMMITTED。维护期间读服务和真实已提交Head保护另由生命周期测试证明。

每次实际EXE运行绑定EXE SHA、包manifest、工作区、输入/输出引用、实际时刻、事务、前后Head。只有完整链和故障矩阵均通过才记录FROZEN_EXE_END_TO_END_PASS；物理UI、安装升级及真实登录/生产接管各自保持未验收直到有独立证据。生产28765继续运行；真实Head、调度设置和既有冻结不动。

独立审计项PKG-A01至A06分别更新证据，外部接受仍NOT_GRANTED。S1全部接受条件满足后，下一门才是S2安装器/实机与独立授权的生产接管；提交推送不等于外审或生产切换。
