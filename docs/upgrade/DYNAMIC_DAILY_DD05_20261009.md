# DD05 实际工作台入口与状态

执行合同：V4-DYNAMIC-DAILY-R1.1 DD05，继承 DD01–DD04 的日历、源门、单队列和发布权限；使用原冻结工作台脚本加独立日更入口，不修改旧生产脚本字节。

首页与数据诊断页提供实际“检查更新”“立即补齐”按钮和“自动更新设置”入口；按钮调用正式端口的同一 Job API，展示真实任务 ID。独立日更中心提供目标日期、AUTO 持久开关、逐日状态、来源校验、阶段 SHA、重试、取消、事件日志和发布前驱记录。缺源时保留最后有效 Head。

真实验收：正式端口 28765；内置浏览器 1366/1920；暂停后实际停止并重启后台服务，暂停设置、任务 ID 和 Head SHA 均保持，随后页面恢复 AUTO。诊断页预检登记真实任务 `7768cb55435e4f5bbfebf0f52c71502b`；补齐复用 AUTO 任务 `a85707e650bb42c296fcfec196eabdf3`。截图及重启收据位于本阶段 evidence 目录。

用户明确将 Chrome/Edge 改为默认内置浏览器，修订见 `BROWSER_SCOPE_AND_CLOSE.json`。任务页面现已关闭，用于 DD07 无页面后台执行验证。

验收结果：ENGINEERING_PASS_REAL_TRIGGER_PERSISTENCE_LAYOUT；真实新日期 CAS 后 UI 截止与阶段 SHA 的最后读回交由 DD07；独立外审 NOT_GRANTED。下一阶段：真实自动日更、发布后恢复和完整归档。
