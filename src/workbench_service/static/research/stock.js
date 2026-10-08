import * as C from './components.js';
import {read} from './api.js';
export async function stockDetail(main,id,signal){
 const box=C.el('section'),controls=C.el('div',undefined,'filters');main.prepend(box);box.append(C.el('h2','技术图表 · 实际成交行情'),controls);
 const period=C.el('select'),basis=C.el('select');period.setAttribute('aria-label','行情周期');basis.setAttribute('aria-label','价格口径');
 for(const [v,t] of [['D','日线'],['W','周线'],['M','月线']]){const o=C.el('option',t);o.value=v;period.append(o);}
 for(const [v,t] of [['QFQ','原生前复权'],['RAW','不复权']]){const o=C.el('option',t);o.value=v;basis.append(o);}
 const plot=C.el('div');controls.append(period,basis);box.append(plot);let generation=0;
 async function load(){const rev=++generation;plot.replaceChildren(C.LoadingState());try{const d=await read('stocks/'+id+'/chart',{period:period.value,price_basis:basis.value,limit:120},signal);if(rev!==generation)return;plot.replaceChildren(C.el('p',`截至 ${d.as_of} · ${d.price_basis==='RAW'?'不复权':'截至该日坐标前复权'} · 展示 ${d.items.length} / ${d.total} 根 · 成交量：股 / 成交额：元`),C.Kline(d.items));const source=C.el('button','行情口径与来源');source.onclick=()=>C.EvidenceDrawer(d);plot.append(source);}catch(e){if(e.name!=='AbortError')plot.replaceChildren(C.ErrorState(e,load));}}
 period.onchange=load;basis.onchange=load;await load();
 const p=await read('stocks/'+id+'/profile',{},signal);main.append(C.el('h2','事实 F / 研究状态 R / 假设 H'));
 for(const [name,fields] of [['事实',p.F],['研究状态',p.R]])main.append(C.el('h3',name),C.DataTable({items:Object.entries(fields).map(([k,v])=>({display_name:k,fields:{value:v}}))},['value'],'fields'));
 main.append(C.EmptyState('假设：当前没有已绑定的 owner 假设产物。等待条件与失效条件仅按实际源展示。'));const b=C.el('button','未入选原因、等待条件与证据');b.onclick=()=>C.EvidenceDrawer(p);main.append(b);
}
