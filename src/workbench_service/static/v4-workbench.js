'use strict';
(() => {
  const modules=['summary','radar','entity','sector','cohort','settlement','health'];
  const labels={effective_event:'状态变化',primary_scenario:'场景',counterevidence:'证据 / 风险',trade_date:'来源交易日',entity_id:'对象',signal_type:'信号类别',eligibility_state:'资格',priority_bucket:'优先级',source_security_key:'股票代码',close:'收盘价',open:'开盘价',high:'最高价',low:'最低价',list_date:'上市日期',scenario:'场景',scenario_status:'场景状态',state:'研究状态',final_eligibility:'最终资格',state_freshness:'状态时效',health:'健康',maturity:'成熟度',sector_id:'板块编码',sector_name:'板块',member_count:'已接受成员数',algorithm_state:'板块算法状态',T0:'冻结 T0',cohort_namespace:'样本命名空间',enrollment_id:'入组身份',evidence_class:'证据类型',horizon:'期限',outcome_status:'观察结果',due_date:'到期日',outcome_revision:'结果修订',component:'数据组件',row_count:'记录数',quality:'来源质量'};
  let context=null,generation=0;
  const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;};
  const fmt=value=>value===null?'无 / 不适用':typeof value==='object'?JSON.stringify(value):String(value);
  async function fetchModule(module,params={}){
    const query=new URLSearchParams(params);const response=await fetch('/api/v4/current/'+module+(query.size?'?'+query:''),{cache:'no-store'});
    const payload=await response.json();if(!response.ok)throw Error(payload.code+' · '+(payload.reason||''));return payload;
  }
  function render(module,payload){
    if(payload.context_token!==context.context_token)throw Error('上下文已变更，请刷新页面');
    const target=document.querySelector('#'+module+' .content');target.replaceChildren();
    target.append(node('span',payload.source_mode,'badge mode'),node('span',' '+payload.module_status+' · '+payload.total+' 条','badge'));
    if(payload.module_status==='EMPTY_VALID')target.append(node('p','当前 accepted context 无符合条件对象','note'));
    if(payload.module_status==='PENDING')target.append(node('p','PENDING · 当前尚无已验证成熟结果，保留 T0 与期限状态。','note'));
    if(module==='summary')target.append(node('p','今日变化：'+payload.metadata.today_change+'；下方保留最近已接受变化。','note'));
    if(module==='sector')target.append(node('p','成员关系已接受；板块算法状态保留其历史或能力缺口。','note'));
    const cards=node('div',undefined,'cards');
    for(const item of payload.items){
      const card=node('article',undefined,'record');card.append(node('strong',item.display_name||item.entity_id||module));
      const unknown=[];const sources=[];
      for(const [key,cell] of Object.entries(item.fields)){
        if(cell.quality==='UNKNOWN'){unknown.push({field:labels[key]||key,reason:cell.reason,source:cell.source});continue;}
        const field=node('div',undefined,'field');field.append(node('span',labels[key]||key,'label'),node('span',fmt(cell.value),'value'),node('span',cell.quality,'quality'));card.append(field);sources.push({field:key,quality:cell.quality,...cell.source});
      }
      if(unknown.length){const details=node('details');details.append(node('summary',unknown.length+' 项来源缺口 / UNKNOWN'),node('pre',JSON.stringify(unknown,null,2)));card.append(details);}
      const details=node('details');details.append(node('summary','核验来源 · '+payload.context.accepted_trade_date),node('pre',JSON.stringify(sources,null,2)));card.append(details);cards.append(card);
    }
    target.append(cards);
    if(payload.total>payload.items.length)target.append(node('p','当前显示 '+payload.items.length+' 条，共 '+payload.total+' 条。输入代码或名称精确筛选。','muted'));
    if(module==='health'){target.append(node('p','等待下一 accepted input · 最近一次已接受日期 '+payload.context.accepted_trade_date,'note'),node('pre',JSON.stringify(payload.metadata,null,2)));}
    if(module==='summary' && payload.metadata.last_accepted_why_now){const details=node('details');details.append(node('summary','最近已接受 Why Now / 可观察证据'),node('pre',JSON.stringify(payload.metadata.last_accepted_why_now,null,2)));target.append(details);}
  }
  async function load(module){
    const currentGeneration=generation;
    const q=document.querySelector('[data-query="'+module+'"]')?.value||'';
    const state=document.querySelector('[data-state="'+module+'"]')?.value||'';
    try{const payload=await fetchModule(module,{context_token:context.context_token,q,state,limit:module==='health'?'30':'6'});if(currentGeneration===generation)render(module,payload);}
    catch(error){if(currentGeneration===generation)document.querySelector('#'+module+' .content').replaceChildren(node('p','SOURCE_INVALID · '+error.message,'error'));}
  }
  async function refresh(){
    generation++;const banner=document.querySelector('#status');
    try{
      context=await fetchModule('context');const c=context.context;banner.replaceChildren(node('strong','当前展示：'+c.accepted_trade_date+' 已接受 V4 状态'),node('p',context.status+' · '+c.freshness_state));
      const identity=node('div',undefined,'identity');for(const [label,value] of [['当前阶段',c.stage],['数据更新时间',c.data_updated_at],['Data head',c.data_head_digest.slice(0,16)],['Stage head',c.stage_head_digest.slice(0,16)]]){const block=node('div');block.append(node('span',label,'muted'),node('strong',value));identity.append(block);}banner.append(identity);
      document.querySelector('#token').textContent='固定上下文 '+context.context_token.slice(-16);
      const params=new URLSearchParams(location.search);if(params.get('q'))document.querySelector('[data-query="entity"]').value=params.get('q');
      await Promise.all(modules.map(load));window.V4Context=context;
    }catch(error){banner.replaceChildren(node('p','SOURCE_INVALID · '+error.message,'error'));}
  }
  let timer;document.querySelectorAll('[data-query],[data-state]').forEach(input=>input.addEventListener(input.tagName==='SELECT'?'change':'input',()=>{clearTimeout(timer);timer=setTimeout(()=>load(input.dataset.query||input.dataset.state),250);}));
  document.querySelector('#refresh').addEventListener('click',refresh);refresh();
})();
