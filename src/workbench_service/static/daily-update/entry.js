// Independent daily center entry. Frozen R43 business views remain unchanged.
const dailyLink=document.createElement('a');dailyLink.href='/v4/research/data-update';dailyLink.textContent='数据更新';dailyLink.style.marginLeft='16px';document.querySelector('nav')?.append(dailyLink);
document.addEventListener('click',event=>{const link=event.target.closest('a');if(link?.pathname==='/v4/research/data-update'){event.preventDefault();event.stopImmediatePropagation();location.assign(link.href)}},true);
const dailyMain=document.querySelector('main');
function dailyEntryControls(){
 for(const node of dailyMain?.querySelectorAll('p')||[])if(node.textContent.startsWith('日更入口：python'))node.textContent='日更状态与操作请使用上方后台数据更新入口。';
 if(!dailyMain||!['/v4/research/home','/v4/research/diagnostics'].includes(location.pathname)||dailyMain.querySelector('[data-daily-center]'))return;
 const box=document.createElement('section');box.dataset.dailyCenter='true';box.setAttribute('aria-label','后台数据更新');box.style.cssText='padding:12px;margin-bottom:16px;border:1px solid #dbe2e9;border-radius:8px';
 const message=document.createElement('span');message.setAttribute('role','status');
 for(const [label,route,body] of [['检查更新','probe',{}],['立即补齐','jobs',{mode:'CATCH_UP'}]]){
  const button=document.createElement('button');button.textContent=label;button.style.marginRight='12px';
  button.onclick=async event=>{event.stopPropagation();button.disabled=true;try{const response=await fetch('/api/v4/operations/daily-update/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-V4-Operation':'daily-update','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(body)});const result=await response.json();if(!response.ok)throw Error(result.reason||result.code);message.textContent='后台任务 '+result.job_id+' 已登记；在日更中心查看进度。';await dailyEntryStatus()}catch(error){message.textContent='任务未登记：'+error.message}finally{button.disabled=false}};
  box.append(button);
 }
 const settings=document.createElement('a');settings.href=dailyLink.href;settings.textContent='自动更新设置';settings.style.marginRight='16px';box.append(settings,message);dailyMain.prepend(box);
}
if(dailyMain)new MutationObserver(dailyEntryControls).observe(dailyMain,{childList:true});
dailyEntryControls();
async function dailyEntryStatus(){try{const response=await fetch('/api/v4/operations/daily-update/status');if(response.ok){const value=await response.json();dailyLink.textContent=`数据更新 · 截至 ${value.last_good_trade_date} · ${value.missing_sessions.length?'待补 '+value.missing_sessions[0]:'已同步'}`}}catch{}}
dailyEntryStatus();setInterval(dailyEntryStatus,15000);
