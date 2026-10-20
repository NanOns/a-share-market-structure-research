import * as C from './components.js';

export function rotationAutoAcceptance(summary,pages,tradeDate,contextToken,acceptedTransitions){
 const rows=pages.flatMap(page=>page.items||[]),ids=rows.map(row=>row.entity_id);
 const unique=ids.length===new Set(ids).size&&ids.every(Boolean);
 const complete=summary?.automatic_acceptance_contract==='V4_ROTATION_PIPELINE_AUTO_ACCEPTANCE_R1'&&
  summary.automatic_acceptance_state==='AUTO_ACCEPTED_WITH_LIMITATIONS'&&summary.owner_bound===true&&summary.total===400&&
  pages.length===2&&pages[0]?.offset===0&&pages[1]?.offset===200&&
  pages.every(page=>page.context_token===contextToken&&page.total===400)&&
  rows.length===400&&unique;
 const box=C.el('section',undefined,'card');
 box.append(C.el('h2','轮动域自动验收'));
 box.append(C.el('p',complete?
  tradeDate+' 候选已按正常数据流程自动接受：轮动 Owner 已绑定并校验，400 个板块完整读回且身份唯一。':
  '自动验收暂未通过：Owner 绑定、页面完整性或板块身份唯一性检查未满足。',complete?'':'notice'));
 if(complete){
  const unknown=summary.current_states?.UNKNOWN??0,none=summary.current_states?.NONE??0;
  box.append(C.el('p','当前状态：未知 '+unknown+' · 无轮动 '+none+' · 已生成状态迁移 '+(acceptedTransitions??0)));
  box.append(C.el('p','自动接受范围：该交易日 Owner 生成的候选数据与页面展示。UNKNOWN 保持未知；只有 Owner 明确给出的有效状态迁移才计入轮动变化。'));
  box.append(C.el('p','来源时间：'+(pages[0]?.context?.membership_observed_at||'按 Owner 记录')+' · PIT_ELIGIBLE='+(pages[0]?.context?.PIT_ELIGIBLE??'未知')));
 }
 return box;
}
