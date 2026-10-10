import * as C from './components.js';
import {read,getContext} from './api.js';
import {labels} from './labels.js';
export async function stockDetail(main,id,signal){
 const box=C.el('section'),controls=C.el('div',undefined,'filters');main.prepend(box);box.append(C.el('h2','技术图表 · 实际成交行情'),controls);
 const period=C.el('select'),basis=C.el('select');period.setAttribute('aria-label','行情周期');basis.setAttribute('aria-label','价格口径');
 for(const [v,t] of [['D','日线'],['W','周线'],['M','月线']]){const o=C.el('option',t);o.value=v;period.append(o);}
 for(const [v,t] of [['QFQ','原生前复权'],['RAW','不复权']]){const o=C.el('option',t);o.value=v;basis.append(o);}
 const plot=C.el('div');controls.append(period,basis);box.append(plot);let generation=0,offset=0;
 async function load(){const rev=++generation;plot.replaceChildren(C.LoadingState());try{const d=await read('stocks/'+id+'/chart',{period:period.value,price_basis:basis.value,limit:120,offset},signal);if(rev!==generation)return;plot.replaceChildren(C.el('p',`截至 ${d.as_of} · ${d.price_basis==='RAW'?'不复权':'截至该日坐标前复权'} · 展示 ${d.items.length} / ${d.total} 根 · 成交量：股 / 成交额：元`),C.Kline(d.items));const source=C.el('button','行情口径与来源');source.onclick=()=>C.EvidenceDrawer(d);plot.append(source);const older=C.el('button','更早行情'),newer=C.el('button','更新行情');older.disabled=!d.has_next;newer.disabled=offset===0;older.onclick=()=>{offset+=120;load();};newer.onclick=()=>{offset=Math.max(0,offset-120);load();};plot.append(older,newer);if(d.period!=='D')plot.append(C.el('p','最后一根 '+(d.items.at(-1)?.period_status||'不可判定')+(d.items.at(-1)?.period_status==='CLOSED_ONLY_READY'?'；正式 Owner 已确认周期结束。':'；当前周期部分行情，禁止按已结束周期解释。')));plot.append(C.el('p','末根 '+(d.items.at(-1)?.trade_date||'无行情')+' 收盘 '+C.displayValue(d.items.at(-1)?.close)));}catch(e){if(e.name!=='AbortError')plot.replaceChildren(C.ErrorState(e,load));}}
 period.onchange=()=>{offset=0;load();};basis.onchange=()=>{offset=0;load();};await load();
 const p=await read('stocks/'+id+'/profile',{},signal);main.append(C.el('h2','入选与未入选解释'),C.el('p','当前资格：'+(p.selection_explanation?.status||'UNKNOWN')+' · 不在候选列表仍有每日画像。'));const keyPrices=C.el('button','关键价、复权坐标与窗口');keyPrices.onclick=()=>C.EvidenceDrawer(p.key_prices);main.append(keyPrices,C.el('p',p.hypothesis_scope));
 const relations=p.membership_relations;main.append(C.el('h2','所属行业与关联概念'));
 for(const [role,title] of [['primary_industry','主行业'],['supporting_concepts','关联概念']]){const section=C.el('section');section.append(C.el('h3',title));const items=(relations?.items||[]).filter(x=>x.role===role);if(!items.length)section.append(C.el('p',relations?.owner_gap?.includes(role)?'关系来源不足':'当前来源未列出该类关系'));for(const item of items)section.append(item.href?C.link(item.display_name+' · '+(item.sector_type==='INDUSTRY'?'行业':'概念'),item.href):C.el('span','关系身份来源不足'));main.append(section);}
 const relationSource=C.el('button','行业与概念关系来源');relationSource.onclick=()=>C.EvidenceDrawer(relations);main.append(relationSource);
 main.append(C.el('h2','事实 F / 研究状态 R / 假设 H'));
 for(const [name,fields] of [['事实',p.F],['研究状态',p.R]])main.append(C.el('h3',name),C.DataTable({items:Object.entries(fields).map(([k,v])=>({display_name:labels[k]||k,fields:{value:v}}))},['value'],'fields'));
 main.append(C.el('h3','当前变化原因与待补证据'));
 const hypotheses=p.competitive_hypotheses;main.append(C.el('h3','竞争解释 · 条件性研究假设'));
 if(hypotheses?.status==='READY'){for(const h of hypotheses.items){const section=C.el('section');section.append(C.el('h4',h.title),C.el('p','当前条件支持：'+(h.current_support?'是':'不足')),C.el('p','反证：'+h.counterevidence),C.el('p','下一判别条件：'+h.next_discriminator));const source=C.el('button','支持事实与来源');source.onclick=()=>C.EvidenceDrawer({support:h.support,evidence:hypotheses.evidence,scope:hypotheses.scope});section.append(source);main.append(section);}}else main.append(C.EmptyState('竞争解释所需事实来源不足：'+(hypotheses?.missing_fields||[]).join('、')));
 for(const [key,title] of [['why_now','当前变化原因'],['waiting_for','等待条件'],['invalid_if','失效条件'],['hypothesis','研究假设']]){const field=p.owner_explanations?.[key];const section=C.el('section');section.append(C.el('h4',field?.basis==='MISSING_PREDICATE_EVIDENCE_ONLY'?'待补判定证据（owner 未发布等待条件）':title));if(!field?.source||field.source.quality==='UNKNOWN')section.append(C.EmptyState('来源未提供可用的'+title+'；责任 owner 与原因见证据。'));else if(Array.isArray(field.value))section.append(C.el('p',field.value.length?field.value.map(C.displayValue).join('、'):'已发布列表为空'));else section.append(C.el('p',C.displayValue(field.value)));const evidence=C.el('button',title+'来源');evidence.onclick=()=>C.EvidenceDrawer({field:key,...field,owner_specific_debt:p.owner_specific_debt.filter(d=>d.field===key)});section.append(evidence);main.append(section);}
 const b=C.el('button','未入选原因、等待条件与证据');b.onclick=()=>C.EvidenceDrawer(p);main.append(b);
 const focus=C.el('button','关注事件时间线');focus.onclick=async()=>C.EvidenceDrawer(await read('focus/'+id+'/timeline',{limit:200},signal));
 const structure=C.el('button','结构锚点与事件');structure.onclick=async()=>C.EvidenceDrawer(await read('stocks/'+id+'/timeline',{limit:200},signal));main.append(focus,structure);
}
export function stockExport(signal){
 const box=C.el('div'),button=C.el('button','导出当前筛选全量画像 CSV'),cancel=C.el('button','取消导出'),status=C.el('span');cancel.hidden=true;box.append(button,cancel,status);
 button.onclick=async()=>{button.disabled=true;cancel.hidden=false;const controller=new AbortController();const abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});cancel.onclick=abort;
 try{const params=Object.fromEntries(new URLSearchParams(location.search));delete params.offset;const rows=[],seen=new Set();let offset=0,total,token;
 do{const d=await read('stocks',{...params,limit:200,offset},controller.signal);if(token&&token!==d.context_token)throw Error('导出期间版本变化，请重试');token=d.context_token;if(total!==undefined&&total!==d.total)throw Error('导出分母变化');total=d.total;
 for(const row of d.items){if(seen.has(row.entity_id))throw Error('导出身份重复');seen.add(row.entity_id);rows.push(row);}if(!d.items.length&&offset<total)throw Error('导出分页缺失');offset+=d.items.length;status.textContent=`已读取 ${offset} / ${total}`;}while(offset<total);
 if(rows.length!==total)throw Error('导出行数不一致');const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';const keys=['close','scenario','final_eligibility','primary_industry'];
 const csv=[['名称','代码','截至日',...keys.map(k=>labels[k])],...rows.map(r=>[r.display_name,r.symbol,r.trade_date,...keys.map(k=>r.fields[k]?.value)])].map(row=>row.map(quote).join(',')).join('\r\n');
 const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=C.link('下载',url);a.download='V4_全量筛选画像.csv';box.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);status.textContent=`已导出 ${total} 条 · 同一快照`;
 }catch(e){status.textContent=e.name==='AbortError'?'导出已取消，可重新导出':'导出失败：'+e.message;}finally{signal?.removeEventListener('abort',abort);button.disabled=false;cancel.hidden=true;}};return box;
}
