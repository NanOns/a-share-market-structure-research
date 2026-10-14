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
    const progress = document.createElement('div'); progress.setAttribute('aria-live','polite');
    const link = document.createElement('a'); link.href='/v4/research/diagnostics?tab=jobs'; link.textContent='查看日更进度';
    const bar=document.createElement('progress'); bar.hidden=true;
    const history=document.createElement('details');
    const title=document.createElement('summary');title.textContent='阶段记录与已完成日期';
    const stages=document.createElement('pre');stages.style.whiteSpace='pre-wrap';history.append(title,stages);
    let latestJob=null;
    history.addEventListener('toggle',async()=>{
      if(!history.open||!latestJob)return;
      const abort=new AbortController();const timer=setTimeout(()=>abort.abort(),4000);
      try{
        const reply=await fetch('/api/v4/operations/daily-update/jobs/'+encodeURIComponent(latestJob)+'/events',{signal:abort.signal,cache:'no-store'});
        if(!reply.ok)throw Error('events unavailable');
        const data=await reply.json();
        stages.textContent=(data.events||[]).map(e=>e.timestamp+' · '+e.stage+' · '+e.event_code).join('\n')||'尚无阶段记录';
      }catch(_){stages.textContent='阶段记录暂不可用';}finally{clearTimeout(timer);}
    });
    box.append(condition, state, link, progress, bar, history); document.body.prepend(box);
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
    const refreshProgress=async()=>{
      const abort=new AbortController(); const timer=setTimeout(()=>abort.abort(),4000);
      try{
        const response=await fetch('/api/v4/operations/daily-update/progress',{cache:'no-store',signal:abort.signal});
        if(!response.ok)throw Error('progress unavailable');
        const p=await response.json();latestJob=p.job_id;
        const count=Number.isInteger(p.processed)&&Number.isInteger(p.total)&&p.total>0;
        bar.hidden=!count; if(count){bar.max=p.total;bar.value=p.processed;}
        const elapsed=p.elapsed_seconds==null?'未知':Math.floor(p.elapsed_seconds)+'秒';
        progress.textContent=`页面已发布日 ${p.last_published_trade_date||'待确认'} · 生成目标 ${p.target_trade_date||'无'} · 模式 ${p.mode||'待确认'} · ${p.stage||p.stage_state} ${count?p.processed+'/'+p.total+' '+(p.unit||''):''} · ${p.recent_message||''} · 耗时 ${elapsed} · ${p.finished_at?'完成时间 '+p.finished_at:'最近进展 '+(p.last_progress_at||'未开始')+' · 心跳 '+(p.heartbeat_at||'未确认')}${p.error_code?' · 错误 '+p.error_code:''}${p.stage_state==='RUNNING'&&!p.finished_at&&p.seconds_since_progress>120?' · 近期无进展，请查看阶段详情':''}`;
      }catch(_){progress.textContent='日更进度暂不可用';bar.hidden=true;}
      finally{clearTimeout(timer);}
    };
    refresh();refreshProgress();setInterval(()=>{if(!document.hidden){refresh();refreshProgress();}},5000);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
