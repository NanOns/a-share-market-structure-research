import * as C from './components.js';
import {read,getContext} from './api.js';
export async function replayPage(main,route,signal,render){
 main.append(C.el('p','运营历史使用当前成员重建，PIT_ELIGIBLE=false。严格首次可用证据不足，不作为 T0 当时已知或历史策略效果。','notice'));
 if(route==='replay'){main.append(C.EmptyState('严格历史 PIT 未具备完整 first-available 证明。可用数据请进入明确标记的重建比较。'),C.link('进入重建比较','/v4/research/compare'));return;}
 const params=new URLSearchParams(location.search),context=getContext();
 const form=C.el('form',undefined,'filters'),day=C.el('select'),mode=C.el('select'),left=C.el('input'),right=C.el('input');
 day.setAttribute('aria-label','比较日期');for(const value of context.context.available_trade_dates){const o=C.el('option',value);o.value=value;day.append(o);}day.value=params.get('as_of')||context.context.trade_date;
 mode.setAttribute('aria-label','比较方式');for(const [value,title] of [['stock-stock','股票与股票'],['sector-sector','板块与板块'],['stock-market','股票与市场'],['sector-market','板块与市场']]){const o=C.el('option',title);o.value=value;mode.append(o);}mode.value=params.get('mode')||'stock-stock';
 left.setAttribute('aria-label','左侧研究对象');left.placeholder='股票代码或板块 ID';left.value=params.get('left')||'';right.setAttribute('aria-label','右侧研究对象');right.placeholder='股票代码或板块 ID';right.value=params.get('right')||'';
 const button=C.el('button','读取重建比较');button.type='submit';form.append(day,mode,left,right,button);form.onsubmit=e=>{e.preventDefault();history.pushState({},'','?'+new URLSearchParams({as_of:day.value,mode:mode.value,left:left.value,right:right.value}));render();};main.append(form);
 if(!left.value){main.append(C.EmptyState('选择日期和研究对象；可从股票或板块详情直接进入。'));return;}
 try{const d=await read('compare',Object.fromEntries(params),signal);main.append(C.el('h2','事后重建比较 · 非严格 PIT'),C.el('p','截至 '+d.as_of+' · 不作因果归因。'));for(const [label,row] of [['左侧',d.left],['右侧',d.right]]){main.append(C.el('h3',label));if(row.fields)main.append(C.DataTable({items:[row]},['ret1','ret5','ret20','sector_rs5','sector_rs20'],'fields'));else main.append(C.el('p','市场环境：'+(row.regime?.value||'不可判定')));const b=C.el('button',label+'日期、字段与来源');b.onclick=()=>C.EvidenceDrawer(row);main.append(b);}}catch(e){if(e.name!=='AbortError')main.append(C.ErrorState(e,render));}
}
