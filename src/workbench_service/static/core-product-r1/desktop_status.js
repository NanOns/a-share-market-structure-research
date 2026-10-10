/* Desktop presentation only; original accepted HTML and research data stay intact. */
(() => {
  const mount = () => {
    if (document.getElementById('daav4-capture-status')) return;
    const box = document.createElement('aside');
    box.id = 'daav4-capture-status'; box.setAttribute('aria-label', '采集与引擎运行条件');
    box.style.cssText = 'background:#fff4cd;color:#332600;border-bottom:1px solid #bf9226;padding:10px 14px;font:14px/1.5 sans-serif;overflow-wrap:anywhere';
    const condition = document.createElement('div');
    condition.textContent = 'CAPTURE_REQUIRES_APP_RUNNING · 真实采集需要电脑可用、用户已登录、应用及引擎运行、自动日更未暂停且来源可用。补日更不能补造首次观测。';
    const state = document.createElement('div'); state.setAttribute('aria-live', 'polite');
    box.append(condition, state); document.body.prepend(box);
    const refresh = async () => {
      const abort = new AbortController(); const timer = setTimeout(() => abort.abort(), 2500);
      try {
        const reply = await fetch('/api/v4/desktop/status', {cache:'no-store',signal:abort.signal});
        if (!reply.ok) throw new Error('status unavailable');
        const data = await reply.json();
        const auto = data.auto_daily_enabled === true ? '开启' : data.auto_daily_enabled === false ? '暂停' : '待确认';
        state.textContent = `引擎：${data.engine_state} · 自动日更：${auto} · 版本：${data.BUILD_RELEASE_ID} · 观测：${data.observed_at}。数据日期以研究页面原上下文为准。`;
      } catch (_) {
        state.textContent = '当前引擎与调度状态未确认，可能已停止；已有页面内容不能证明正在采集。';
      } finally { clearTimeout(timer); }
    };
    refresh(); setInterval(refresh, 5000);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
