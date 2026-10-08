import * as C from './components.js';
import {read} from './api.js';
import {labels} from './labels.js';
export async function stockDetail(main,id,signal){
 const box=C.el('section'),controls=C.el('div',undefined,'filters');main.prepend(box);box.append(C.el('h2','技术图表 · 实际成交行情'),controls);
 const period=C.el('select'),basis=C.el('select');period.setAttribute('aria-label','行情周期');basis.setAttribute('aria-label','价格口径');
 for(const [v,t] of [['D','日线'],['W','周线'],['M','月线']]){const o=C.el('option',t);o.value=v;period.append(o);}
 for(const [v,t] of [['QFQ','原生前复权'],['RAW','不复权']]){const o=C.el('option',t);o.value=v;basis.append(o);}
 const plot=C.el('div');controls.append(period,basis);box.append(plot);let generation=0;
 async function load(){const rev=++generation;plot.replaceChildren(C.LoadingState());try{const d=await read('stocks/'+id+'/chart',{period:period.value,price_basis:basis.value,limit:120},signal);if(rev!==generation)return;plot.replaceChildren(C.el('p',`截至 ${d.as_of} · ${d.price_basis==='RAW'?'不复权':'截至该日坐标前复权'} · 展示 ${d.items.length} / ${d.total} 根 · 成交量：股 / 成交额：元`),C.Kline(d.items));const source=C.el('button','行情口径与来源');source.onclick=()=>C.EvidenceDrawer(d);plot.append(source);}catch(e){if(e.name!=='AbortError')plot.replaceChildren(C.ErrorState(e,load));}}
 period.onchange=load;basis.onchange=load;await load();
 const p=await read('stocks/'+id+'/profile',{},signal);main.append(C.el('h2','事实 F / 研究状态 R / 假设 H'));
 for(const [name,fields] of [['事实',p.F],['研究状态',p.R]])main.append(C.el('h3',name),C.DataTable({items:Object.entries(fields).map(([k,v])=>({display_name:labels[k]||'研究字段（见来源）',fields:{value:v}}))},['value'],'fields'));
 main.append(C.EmptyState('假设：当前没有已绑定的 owner 假设产物。等待条件与失效条件仅按实际源展示。'));const b=C.el('button','未入选原因、等待条件与证据');b.onclick=()=>C.EvidenceDrawer(p);main.append(b);
}
export function stockExport(signal){const button=C.el('button','导出当前筛选全量画像 CSV');button.onclick=async()=>{button.disabled=true;try{const params=Object.fromEntries(new URLSearchParams(location.search));delete params.offset;const rows=[];let offset=0;let total;do{const d=await read('stocks',{...params,limit:200,offset},signal);rows.push(...d.items);total=d.total;offset+=200;if(offset>1000000)throw Error('导出超出合同范围');}while(offset<total);const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';const keys=['close','scenario','final_eligibility','primary_industry'];const csv=[['名称','代码','截至日',...keys.map(k=>labels[k])],...rows.map(r=>[r.display_name,r.symbol,r.trade_date,...keys.map(k=>r.fields[k]?.value)])].map(row=>row.map(quote).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=C.link('下载',url);a.download='V4_全量筛选画像.csv';a.click();URL.revokeObjectURL(url);}catch(e){C.EvidenceDrawer({error:e.message});}finally{button.disabled=false;}};return button;}
