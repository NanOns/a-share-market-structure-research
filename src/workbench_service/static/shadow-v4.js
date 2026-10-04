'use strict';
// One token per mounted view. No production routes, writes or simulation switch.
const ShadowUI = (() => {
  const identity = ['namespace','trade_date','publication_id','publication_revision','model_contract_id','parameter_set_id','state_lineage_id','daily_input_digest','source_manifest_digest','evidence_origin'];
  const registry = {
    summary: ['今日变化 / Why Now', {entity_id:'对象',prior_state:'前一接受状态',current_state:'当前状态',reason_codes:'变化原因',observable_evidence:'可观察证据',risk_unknown:'风险 / 未知'}],
    radar: ['研究雷达', {entity_id:'对象',entity_type:'类型',eligibility:'资格',state:'状态',priority_primitives:'优先级原语',quality:'质量',why_now:'Why Now',not_display_reason:'未展示原因'}],
    entity: ['股票 / 板块状态', {entity_id:'对象',entity_type:'类型',trend:'趋势',position:'位置',relative_state:'相对状态',structure:'结构',breakout:'突破',pullback:'回撤',recovery:'恢复',support:'支持',acceptance:'接受',sector_context:'授权板块上下文'}],
    cohort: ['Cohort / Forward', {entity_id:'对象',enrollment_id:'入组身份',T0:'冻结 T0',cohort_namespace:'样本分层',horizon:'期限',due_date:'到期日',outcome_status:'待结算 / 已观察',benchmark_ids:'基准身份',control_assignment_ids:'控制身份'}],
    settlement: ['结算与修订', {enrollment_id:'入组身份',horizon:'期限',outcome_status:'观察状态',outcome:'价格路径结果',outcome_revision:'结果修订',bound_outcome_revision:'精确绑定修订',right_censor:'右删失',revision_reason:'修订原因'}],
    health: ['运行健康 / 来源质量', {slot_status:'观察窗口',source_receipts:'可见性回执',publication_lineage:'发布身份 / 修订',late_missing_unknown:'时钟 / 缺失',capability_scope:'能力范围',blocked_capabilities:'受阻能力',stop_state:'停止新接受',rollback:'保留已接受事实'}]
  };
  const stable = value => JSON.stringify(value, Object.keys(value).sort());
  async function tokenFor(context) {
    if (Object.keys(context).sort().join() !== [...identity].sort().join()) throw Error('CONTEXT_FIELDS_MISMATCH');
    const bytes = new TextEncoder().encode(stable(context));
    const hash = await crypto.subtle.digest('SHA-256', bytes);
    return 'shadow-' + [...new Uint8Array(hash)].map(x => x.toString(16).padStart(2,'0')).join('');
  }
  function cellText(cell) {
    if (cell && !['KNOWN','DEGRADED'].includes(cell.quality) && cell.value != null) throw Error('UNKNOWN_OR_PENDING_VALUE_FORBIDDEN');
    if (!cell || !['KNOWN','DEGRADED'].includes(cell.quality)) return `${cell?.quality || 'UNKNOWN'} · ${cell?.reason || 'SOURCE_FIELD_UNAVAILABLE'}`;
    if (cell.value == null || (typeof cell.value==='string' && cell.value.startsWith('UNKNOWN')) || !cell.source) throw Error('KNOWN_VALUE_REQUIRES_SOURCE');
    return typeof cell.value === 'object' ? JSON.stringify(cell.value,null,2) : String(cell.value);
  }
  async function validate(payload, expected) {
    if (payload.status === 'BLOCKED') throw Error(payload.code || 'SCOPE_BLOCKED');
    if (payload.status === 'NO_REAL_SHADOW_DATA') {
      if (expected || payload.context !== null || payload.real_sample_count !== 0) throw Error('NO_DATA_CONTEXT_MISMATCH');
      return;
    }
    if (!['KNOWN','DEGRADED','UNKNOWN'].includes(payload.source_quality) || payload.context_token !== await tokenFor(payload.context)) throw Error('CONTEXT_TOKEN_MISMATCH');
    if (expected && (payload.context_token !== expected.context_token || stable(payload.context) !== stable(expected.context))) throw Error('COMPONENT_CONTEXT_MISMATCH');
    if (payload.status === 'ACTIVATION_SIMULATION' && (payload.evidence_label !== 'NOT_REAL_EVIDENCE' || payload.context.evidence_origin !== 'ACTIVATION_SIMULATION' || payload.real_sample_count !== 0)) throw Error('SIMULATION_LABEL_REQUIRED');
    if (payload.status === 'READY' && payload.context.evidence_origin !== 'PIT_OBSERVED') throw Error('REAL_ORIGIN_REQUIRED');
    if (!['READY','ACTIVATION_SIMULATION'].includes(payload.status)) throw Error('STATUS_INVALID');
  }
  const el = (tag,text,className) => {const e=document.createElement(tag); if(text!==undefined)e.textContent=text;if(className)e.className=className;return e;};
  function renderFields(parent, fields, labels) {
    const list=el('dl');
    for(const [name,label] of Object.entries(labels)) {
      const row=el('div',undefined,'field');row.append(el('dt',label));
      const cell=fields?.[name];const value=el('dd',cellText(cell));
      if(cell && ['KNOWN','DEGRADED'].includes(cell.quality))value.append(el('span',cell.quality,'quality'));
      row.append(value);
      if(cell?.source){const details=el('details');details.append(el('summary','来源'),el('pre',JSON.stringify(cell.source,null,2)));row.append(details);}
      list.append(row);
    }
    parent.append(list);
  }
  async function mount() {
    const status=document.querySelector('#status'), cards=document.querySelector('#components');
    const deep=new URLSearchParams(location.search);let current=null;let generation=0;
    const fetchRead=async (name,query={}) => {
      const params=new URLSearchParams(query);const response=await fetch('/api/v4/shadow/'+name+(params.size?'?'+params:''),{method:'GET',cache:'no-store'});
      const data=await response.json();if(!response.ok)throw Error(data.code || 'READ_FAILED');return data;
    };
    async function refresh() {
      const round=++generation;cards.replaceChildren();
      try {
        current=await fetchRead('context',Object.fromEntries(deep));await validate(current);if(round!==generation)return;
        if(deep.has('context_token') && deep.get('context_token')!==current.context_token)throw Error('DEEP_LINK_MISMATCH');
        status.className='banner'+(current.status==='ACTIVATION_SIMULATION'?' simulation':'');
        status.textContent=current.status==='NO_REAL_SHADOW_DATA'?'NO_REAL_SHADOW_DATA · 真实样本 0 · 等待独立接受的真实 Shadow 发布。':`${current.status} · ${current.evidence_label} · 真实样本 ${current.real_sample_count}`;
        const identities=document.querySelector('#identity');identities.replaceChildren();
        for(const key of identity){const d=el('dl');d.append(el('dt',key),el('dd',current.context?.[key]===undefined?'UNKNOWN':String(current.context[key])));identities.append(d);}
        identities.append(el('p','来源质量：'+current.source_quality));document.querySelector('#token').textContent='context token：'+(current.context_token || '尚无真实上下文');
        if(current.context_token){deep.set('context_token',current.context_token);history.replaceState(null,'','?'+deep);}
        for(const [name,[title,labels]] of Object.entries(registry)){
          const section=el('section');section.append(el('h2',title));cards.append(section);
          if(!current.context_token){section.append(el('p','无已接受真实数据','muted'));renderFields(section,null,labels);continue;}
          let page=1;const input=el('input');input.placeholder='筛选当前上下文';input.setAttribute('aria-label',title+'筛选');
          const filter=el('button','筛选'),previous=el('button','上一页'),next=el('button','下一页'),tools=el('div',undefined,'tools'),content=el('div');tools.append(input,filter,previous,next);section.append(tools,content);
          const pinned=current;
          async function read(){
            try{const data=await fetchRead(name,{context_token:pinned.context_token,page:String(page),page_size:'20',q:input.value});await validate(data,pinned);if(round!==generation)return;
              content.replaceChildren();content.append(el('p',`共 ${data.total} 条 · 第 ${data.page} 页 · ${data.source_quality}`,'muted'));
              if(!data.items.length)content.append(el('p','当前筛选无记录；不补写资格或样本。','muted'));
              for(const item of data.items){const record=el('article',undefined,'record');renderFields(record,item.fields,labels);content.append(record);}
              previous.disabled=page<=1;next.disabled=!data.has_more;
            }catch(error){if(round===generation){content.replaceChildren(el('p','BLOCKED · '+error.message,'blocked'));previous.disabled=next.disabled=true;}}
          }
          filter.onclick=()=>{page=1;read();};previous.onclick=()=>{if(page>1){page--;read();}};next.onclick=()=>{page++;read();};read();
        }
      }catch(error){if(round===generation){current=null;status.className='banner blocked';status.textContent='BLOCKED · '+error.message;document.querySelector('#identity').replaceChildren();document.querySelector('#token').textContent='上下文校验失败';}}
    }
    document.querySelector('#refresh').onclick=refresh;await refresh();
  }
  return {identity,registry,tokenFor,cellText,validate,mount};
})();
if (typeof module !== 'undefined') module.exports=ShadowUI;
if (typeof document !== 'undefined') ShadowUI.mount();
