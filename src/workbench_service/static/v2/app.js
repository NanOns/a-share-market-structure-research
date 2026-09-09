(function(){
  'use strict';
  var api=window.WorkbenchV2Api,format=window.WorkbenchV2Format,table=window.WorkbenchV2Table,modal=window.WorkbenchV2Modal;
  var select=document.getElementById('publication-select'),notice=document.getElementById('notice'),context=document.getElementById('page-context'),tableTarget=document.getElementById('context-table'),overview=document.getElementById('overview-page'),technicalPage=document.getElementById('technical-page'),sectorsPage=document.getElementById('sectors-page'),current=null,currentPage='overview';
  var technicalState={mode:'highs',page:1,pageSize:50,window:20,rpsMin:'',streakMin:'',maState:'',amountClass:''};
  var sectorState={days:10,type:''};
  function setText(id,value){document.getElementById(id).textContent=value===undefined||value===null||value===''?'—':String(value);}
  function first(obj,keys){for(var i=0;i<keys.length;i++)if(obj&&obj[keys[i]]!==undefined&&obj[keys[i]]!==null)return obj[keys[i]];return null;}
  function publicationRows(items){return items.map(function(item){var option=document.createElement('option');option.value=item.publication_id;option.textContent=item.trade_date+' · '+item.publication_id;return option;});}
  function renderContext(publication,identity,universe){
    var rows=[
      {label:'交易日期',value:publication.trade_date,contract:'publication_heads'},
      {label:'发布身份',value:publication.publication_id,contract:first(identity,['api_contract','contract'])||'m7a-identity-v1'},
      {label:'股票范围',value:first(universe,['contract','universe_contract'])||'workbench-universe-v2.1',contract:'A_SHARE_SQL'},
      {label:'语义注册表',value:'workbench-semantic-v2.1',contract:'sector_semantics.yaml'}
    ];
    table.render(tableTarget,[{label:'上下文',key:'label'},{label:'当前值',key:'value'},{label:'契约/来源',key:'contract'}],rows);
  }
  function setNotice(message,error){notice.className=error?'notice error':'notice';notice.textContent=message;}
  function valueOrDash(value){return value===null||value===undefined?'—':String(value);}
  function quality(item){var codes=(item.quality_codes||[]).concat(item.strength_quality_codes||[]);return codes.length?codes.join(', '):'VALID';}
  function basisText(result){return 'snapshot_id '+format.text(result.snapshot_id)+' · basis '+format.text(result.basis)+' · 数据质量由接口返回，NULL 保持 NULL。';}
  function technicalParams(){
    var params={publication_id:current.publication_id,page:technicalState.page,page_size:technicalState.pageSize,basis:'AUTO'};
    if(technicalState.mode==='highs'){params.window=technicalState.window;params.rps_min=technicalState.rpsMin;params.streak_min=technicalState.streakMin;}
    else{params.ma_state=technicalState.maState;params.amount_class=technicalState.amountClass;}
    return params;
  }
  function showHistory(row){
    modal.open('技术历史 · '+row.security_id,'正在读取…');
    api.technicalHistory({publication_id:current.publication_id,security_id:row.security_id,days:20,price_basis:'ADJUSTED',fields:'ohlc,ma,amount,rps'}).then(function(result){
      var points=result.points||[];var last=points.length?points[points.length-1]:null;
      modal.open('技术历史 · '+row.security_id,JSON.stringify({contract:result.contract||'TECHNICAL_CHART_V2_1_PREVIEW',security_id:result.security_id,snapshot_id:result.snapshot_id,price_basis:result.price_basis,rps_capability:result.rps_capability,latest:last},null,2));
    }).catch(function(error){modal.open('技术历史 · '+row.security_id,'读取失败：'+error.message);});
  }
  function renderTechnical(result){
    var items=result.items||[];var pages=Math.max(1,Math.ceil((result.total||0)/result.page_size));
    document.getElementById('technical-heading').textContent=technicalState.mode==='highs'?'创新高-RPS':'技术状态';
    document.getElementById('technical-description').textContent=technicalState.mode==='highs'?'严格使用前序窗口；并列前高、左删失和缺失值不被伪装成有效信号。':'均线、收益、量额状态来自同一分析快照；不可用字段显示为 NULL。';
    document.getElementById('technical-basis').textContent=basisText(result);document.getElementById('technical-page-label').textContent='第 '+result.page+' 页 / 共 '+pages+' 页 · '+(result.total||0)+' 条';
    document.getElementById('technical-prev').disabled=result.page<=1;document.getElementById('technical-next').disabled=result.page>=pages;
    if(technicalState.mode==='highs'){
      table.render(document.getElementById('technical-table'),[
        {label:'股票',key:'security_id'},{label:'日期',key:'trade_date'},{label:'窗口',value:function(row){return row.window+'日'}},{label:'创新高',value:function(row){return row.new_high===null?'—':row.new_high?'是':'否'}},{label:'前高距离',value:function(row){return row.dist_prior_high===null?'—':format.percent(row.dist_prior_high*100)}},{label:'连续',key:'streak'},{label:'RPS20',value:function(row){return row.rps20===null?'—':format.number(row.rps20,4)}},{label:'有效样本',key:'rps_valid_universe_count20'},{label:'质量',value:quality},{label:'历史',action:{label:'查看',onClick:showHistory}}
      ],items);
    }else{
      table.render(document.getElementById('technical-table'),[
        {label:'股票',key:'security_id'},{label:'日期',key:'trade_date'},{label:'收盘',value:function(row){return row.adj_close===null?'—':format.number(row.adj_close,2)}},{label:'RET20',value:function(row){return row.ret20===null?'—':format.percent(row.ret20*100)}},{label:'MA5 / MA20 / MA60',value:function(row){return [row.ma5,row.ma20,row.ma60].map(valueOrDash).join(' / ')}},{label:'均线',key:'ma_alignment'},{label:'额比20',value:function(row){return row.amount_ratio20===null?'—':format.number(row.amount_ratio20,2)}},{label:'量比前20',value:function(row){return row.volume_vs_prior20===null?'—':format.number(row.volume_vs_prior20,2)}},{label:'量额状态',key:'amount_class'},{label:'质量',value:quality},{label:'历史',action:{label:'查看',onClick:showHistory}}
      ],items);
    }
  }
  function loadTechnical(){
    if(!current)return;setNotice('正在读取个股技术数据…');var request=technicalState.mode==='highs'?api.newHighs(technicalParams()):api.technical(technicalParams());
    request.then(function(result){renderTechnical(result);setNotice('已加载 '+(result.total||0)+' 条；当前页 '+(result.items||[]).length+' 条。');}).catch(function(error){
      document.getElementById('technical-table').replaceChildren();var empty=document.createElement('p');empty.className='empty';empty.textContent=error.message.indexOf('RPS_NOT_BUILT')>=0?'RPS 尚未构建，当前筛选不会降级为伪造结果。':'暂无可用数据：'+error.message;document.getElementById('technical-table').appendChild(empty);document.getElementById('technical-basis').textContent='当前发布版本未提供可用分析快照或该字段能力。';setNotice(error.message.indexOf('RPS_NOT_BUILT')>=0?'RPS 尚未构建。':'技术数据读取失败：'+error.message,true);
    });
  }
  function showSectorTimeline(row){
    modal.open('板块时间线 · '+row.sector_name,'正在读取…');
    Promise.all([api.sectorTimeline({publication_id:current.publication_id,sector_id:row.sector_id,days:30}),api.sectorMembersHistory({publication_id:current.publication_id,sector_id:row.sector_id,days:10,state:'ALL'}),api.sectorLeaderHistory({publication_id:current.publication_id,sector_id:row.sector_id,days:30})]).then(function(values){modal.open('板块时间线 · '+row.sector_name,JSON.stringify({timeline:values[0],member_history:values[1],leader_history:values[2]},null,2));}).catch(function(error){modal.open('板块时间线 · '+row.sector_name,'读取失败：'+error.message);});
  }
  function loadSectors(){
    if(!current)return;setNotice('正在读取板块周期…');
    api.sectorCycle({publication_id:current.publication_id,page:1,page_size:100,days:sectorState.days,type:sectorState.type}).then(function(result){
      document.getElementById('sector-basis').textContent='snapshot_id '+format.text(result.snapshot_id)+' · '+result.dates.length+' 个交易日 · 当前结果只读。';
      table.render(document.getElementById('sector-cycle-table'),[
        {label:'板块',key:'sector_name'},{label:'类型',key:'sector_type'},{label:'最新名次',value:function(row){var c=row.cells[row.cells.length-1];return c&&c.rank!==null?c.rank:'—';}},{label:'最新RPS20百分位',value:function(row){var c=row.cells[row.cells.length-1];return c&&c.sector_rs20_pct!==null?format.number(c.sector_rs20_pct,3):'—';}},{label:'周期单元格',value:function(row){return row.cells.map(function(c){return c.trade_date+': '+(c.rank===null?'—':'#'+c.rank);}).join(' · '); }},{label:'时间线',action:{label:'查看',onClick:showSectorTimeline}}
      ],result.items||[]);setNotice('已加载 '+(result.total||0)+' 个板块。');
    }).catch(function(error){document.getElementById('sector-cycle-table').replaceChildren();var empty=document.createElement('p');empty.className='empty';empty.textContent='暂无周期数据：'+error.message;document.getElementById('sector-cycle-table').appendChild(empty);setNotice('板块周期读取失败：'+error.message,true);});
  }
  function showPage(page){
    currentPage=page;document.querySelectorAll('.nav-item').forEach(function(item){item.classList.toggle('active',item.dataset.page===page);});
    overview.hidden=page!=='overview';technicalPage.hidden=page!=='stocks';sectorsPage.hidden=page!=='sectors';
    if(page==='overview'){document.getElementById('page-title').textContent='研究总览';document.getElementById('page-description').textContent='公共 UI 层：版本、输入身份与统一股票范围。';return;}
    if(page==='stocks'){document.getElementById('page-title').textContent='个股技术';document.getElementById('page-description').textContent='新高窗口、RPS、均线与量额状态；每个结果带有可追溯的分析口径。';loadTechnical();return;}
    if(page==='sectors'){document.getElementById('page-title').textContent='板块周期';document.getElementById('page-description').textContent='历史板块矩阵、成员统计与可追溯时间线。';loadSectors();return;}
    document.querySelector('[data-page="overview"]').click();modal.open('页面预览',document.querySelector('[data-page="'+page+'"]').textContent+' 页面将在后续升级步骤接入。');
  }
  function load(publication){
    current=publication;setNotice('正在读取当前发布版本摘要…');context.textContent='交易日 '+format.text(publication.trade_date)+' · publication_id '+format.text(publication.publication_id);setText('publication-value',publication.trade_date);setText('publication-detail',publication.publication_id);
    Promise.all([api.identity(publication.publication_id,true),api.universeSummary(publication.publication_id)]).then(function(values){
      var identity=values[0]||{},universe=values[1]||{};setText('identity-value',first(identity,['source_revision_id','source_bundle_id','status'])||'已绑定');setText('identity-detail',first(identity,['api_contract','contract'])||'输入身份可追溯');var count=first(universe,['display_count','quote_valid_count','total']);setText('universe-value',count===null?'已加载':format.number(count,0));setText('universe-detail',first(universe,['scope','classification_summary'])||'统一 A 股范围');renderContext(publication,identity,universe);setNotice('摘要已加载；明细页面按升级步骤逐步接入。');document.getElementById('identity-evidence').onclick=function(){modal.open('输入身份证据',JSON.stringify(identity,null,2));};document.getElementById('universe-evidence').onclick=function(){modal.open('统一股票范围边界',JSON.stringify(universe,null,2));};if(currentPage==='stocks')loadTechnical();
    }).catch(function(error){setNotice('摘要读取失败：'+error.message,true);});
  }
  function bindTechnicalControls(){
    var controls=['technical-mode','technical-window','technical-rps-min','technical-streak-min','technical-ma-state','technical-amount-class'];
    controls.forEach(function(id){document.getElementById(id).addEventListener('change',function(){technicalState.mode=document.getElementById('technical-mode').value;technicalState.window=Number(document.getElementById('technical-window').value);technicalState.rpsMin=document.getElementById('technical-rps-min').value;technicalState.streakMin=document.getElementById('technical-streak-min').value;technicalState.maState=document.getElementById('technical-ma-state').value;technicalState.amountClass=document.getElementById('technical-amount-class').value;technicalState.page=1;loadTechnical();});});
    document.getElementById('technical-refresh').addEventListener('click',function(){loadTechnical();});document.getElementById('technical-prev').addEventListener('click',function(){if(technicalState.page>1){technicalState.page--;loadTechnical();}});document.getElementById('technical-next').addEventListener('click',function(){technicalState.page++;loadTechnical();});
    document.getElementById('sector-type').addEventListener('change',function(){sectorState.type=this.value;loadSectors();});document.getElementById('sector-days').addEventListener('change',function(){sectorState.days=Number(this.value);loadSectors();});document.getElementById('sector-refresh').addEventListener('click',function(){loadSectors();});
  }
  bindTechnicalControls();
  api.publications(true).then(function(result){var items=result.items||[];select.replaceChildren.apply(select,publicationRows(items));if(!items.length){setNotice('没有可用的成功发布版本',true);return;}var wanted=new URLSearchParams(location.search).get('publication_id');current=items.find(function(item){return item.publication_id===wanted;})||items[0];select.value=current.publication_id;select.addEventListener('change',function(){load(items.find(function(item){return item.publication_id===select.value;}));});load(current);}).catch(function(error){setNotice('版本列表读取失败：'+error.message,true);});
  document.querySelectorAll('.nav-item').forEach(function(button){button.addEventListener('click',function(){showPage(button.dataset.page);});});
}());
