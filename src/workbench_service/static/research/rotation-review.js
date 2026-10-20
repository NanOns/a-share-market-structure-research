import {read,submitRotationReview} from './api.js';
import * as C from './components.js';

export async function rotationReviewPanel(signal){
 const d=await read('rotation-review',{},signal),box=C.el('section',undefined,'card');
 box.append(C.el('h2','轮动域独立验收'));
 if(d.status==='INDEPENDENT_ACCEPTANCE_PASSED_FOR_CANDIDATE'||d.status==='CANDIDATE_REVIEW_ACCEPTED_WITH_LIMITATIONS'){
  box.append(C.el('p',d.status==='INDEPENDENT_ACCEPTANCE_PASSED_FOR_CANDIDATE'?'该候选已由页面验收者签署独立验收。':'验收者已接受本次候选展示，并保留已列明的数据限制。'),
   C.el('p','验收人：'+d.review.reviewer_attestation+' · 时间：'+d.review.reviewed_at),
   C.el('p','状态未知 '+(d.review.unknown_count??0)+' · 已接受轮动迁移仍为 0；该记录不会更改域发布状态。'),
   C.el('p','范围：'+d.trade_date+' 候选展示；不切正式 Head，不更改已接受轮动事件。'));
  return box;
 }
 if(d.review_write_enabled!==true){box.append(C.el('p','当前服务以只读方式运行；验收操作仅在已授权的本地候选预览中开放。','notice'));return box;}
 const reasons=Object.entries(d.unknown_reasons||{}).map(([key,count])=>key+' '+count).join('、')||'无';
 box.append(C.el('p',d.status==='READY_FOR_INDEPENDENT_REVIEW'?'系统核验通过，等待验收者在本页确认。':d.readback?.sector_rows===400&&d.readback?.sector_ids_unique?'系统已核对完整覆盖，但存在质量限制；你可以接受候选展示并保留这些限制。':'系统核验未通过，当前不能验收。'),
  C.el('p','覆盖板块 '+(d.readback?.sector_rows??0)+' / '+(d.readback?.expected_sector_rows??'未知')+' · 状态未知 '+(d.unknown_count??'未知')+' · 已接受迁移 '+(d.accepted_transition_count??0)),
  C.el('p','阻断：'+reasons),
  C.el('p','来源观测 '+(d.limitations?.membership_observed_at||'未知')+' · AS_RECORDED='+(d.limitations?.AS_RECORDED)+' · PIT_ELIGIBLE='+(d.limitations?.PIT_ELIGIBLE)),
  C.el('p','通过只表示验收者接受该日期候选的轮动质量与展示范围；不改变 Head、轮动事件数或正式发布状态。'));
 if(d.readback?.sector_rows!==400||d.readback?.expected_sector_rows!==400||d.readback?.sector_ids_unique!==true){
  box.append(C.el('p','覆盖或唯一性核验未通过，当前不能记录接受决定。','notice'));
  return box;
 }
 const limited=d.status!=='READY_FOR_INDEPENDENT_REVIEW',decision=limited?'ACCEPT_WITH_LIMITATIONS':'ACCEPT_COMPLETE_CANDIDATE',form=C.el('form',undefined,'rotation-review-form'),reviewer=C.el('input'),evidence=C.el('input'),scope=C.el('input'),submit=C.el('button',limited?'确认接受本次候选展示（保留限制）':'确认轮动域独立验收'),status=C.el('p');
 reviewer.required=true;reviewer.maxLength=80;reviewer.placeholder='验收人姓名或标识';reviewer.setAttribute('aria-label','验收人姓名或标识');
 for(const input of [evidence,scope]){input.type='checkbox';input.required=true;}
 const evidenceLabel=C.el('label',undefined,'rotation-review-check'),scopeLabel=C.el('label',undefined,'rotation-review-check');
 evidenceLabel.append(evidence,' 我已检查 Owner、完整覆盖、质量和读取证据。');
 scopeLabel.append(scope,limited?' 我接受已列明的未知项和 PIT 限制；只接受候选展示，不接受轮动迁移或正式发布。':' 我理解验收仅适用于此候选日期，不改变正式 Head 或已接受事件。');
 submit.type='submit';form.append(reviewer,evidenceLabel,scopeLabel,submit,status);
 form.onsubmit=async event=>{event.preventDefault();submit.disabled=true;status.textContent='正在重新核验并保存验收记录…';try{await submitRotationReview({reviewer:reviewer.value,acknowledge_evidence:evidence.checked,acknowledge_scope:scope.checked,decision});box.replaceWith(await rotationReviewPanel(signal));}catch(error){status.textContent=error.message;submit.disabled=false;}};
 box.append(form);return box;
}
