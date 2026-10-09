// Independent daily center entry. Frozen R43 business views remain unchanged.
const dailyLink=document.createElement('a');dailyLink.href='/v4/research/data-update';dailyLink.textContent='数据更新';dailyLink.style.marginLeft='16px';document.querySelector('nav')?.append(dailyLink);
document.addEventListener('click',event=>{const link=event.target.closest('a');if(link?.pathname==='/v4/research/data-update'){event.preventDefault();event.stopImmediatePropagation();location.assign(link.href)}},true);
const dailyMain=document.querySelector('main');
if(dailyMain)new MutationObserver(()=>{if(location.pathname.startsWith('/v4/research/diagnostics')&&!dailyMain.querySelector('[data-daily-center]')){const link=document.createElement('a');link.href=dailyLink.href;link.textContent='进入数据更新中心';link.dataset.dailyCenter='true';dailyMain.prepend(link)}}).observe(dailyMain,{childList:true});
async function dailyEntryStatus(){try{const response=await fetch('/api/v4/operations/daily-update/status');if(response.ok){const value=await response.json();dailyLink.textContent=`数据更新 · 截至 ${value.last_good_trade_date} · ${value.missing_sessions.length?'待补 '+value.missing_sessions[0]:'已同步'}`}}catch{}}
dailyEntryStatus();setInterval(dailyEntryStatus,15000);
