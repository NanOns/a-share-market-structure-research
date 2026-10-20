import * as C from './components.js';

export function rotationAutoAcceptanceComplete(summary,pages,contextToken){
 const expected=Number(summary?.expected_total);
 const rows=pages.flatMap(page=>page.items||[]),ids=rows.map(row=>row.entity_id);
 const unique=ids.length===new Set(ids).size&&ids.every(Boolean);
 return Number.isInteger(expected)&&expected>0&&
  summary?.automatic_acceptance_contract==='V4_ROTATION_PIPELINE_AUTO_ACCEPTANCE_R1'&&
  summary.automatic_acceptance_state==='AUTO_ACCEPTED_WITH_LIMITATIONS'&&
  summary.automatic_acceptance_scope==='OWNER_DATA_COMPLETE_FOR_DISPLAY_ONLY'&&
  summary.owner_bound===true&&summary.formal_publication===false&&
  summary.numeric_acceptance==='NOT_INDEPENDENTLY_VALIDATED'&&
  summary.total===expected&&summary.covered_total===expected&&
  pages.length===Math.ceil(expected/200)&&
  pages.every((page,index)=>page.offset===index*200&&page.total===expected&&
   page.context_token===contextToken&&page.limit===200)&&
  rows.length===expected&&unique;
}

export function rotationAutoAcceptance(summary,pages,tradeDate,contextToken,acceptedTransitions){
 const complete=rotationAutoAcceptanceComplete(summary,pages,contextToken);
 const box=C.el('section',undefined,'card');
 box.append(C.el('h2','轮动域自动验收'));
 box.append(C.el('p',complete?
  tradeDate+' 轮动 Owner 数据完整，可用于本日候选展示（'+summary.covered_total+'/'+summary.expected_total+' 个板块，身份唯一）。':
  '自动验收暂未通过：Owner 绑定、页面完整性或板块身份唯一性检查未满足。',complete?'':'notice'));
 if(complete){
  const unknown=summary.current_states?.UNKNOWN??0,none=summary.current_states?.NONE??0;
  box.append(C.el('p','本日 Owner 状态：未知 '+unknown+' · 无轮动 '+none+' · Owner 状态变化 '+(acceptedTransitions??0)));
  box.append(C.el('p','此检查只确认 Owner 数据完整且可展示，不代表轮动数值已独立验收，也不授予正式域发布。UNKNOWN、NONE 与缺失质量继续按 Owner 原值呈现。'));
  box.append(C.el('p','来源时间：'+(pages[0]?.context?.membership_observed_at||'按 Owner 记录')+' · PIT_ELIGIBLE='+(pages[0]?.context?.PIT_ELIGIBLE??'未知')));
 }
 return box;
}
