(function(){
  'use strict';
  var api=window.WorkbenchV2Api,format=window.WorkbenchV2Format,table=window.WorkbenchV2Table,modal=window.WorkbenchV2Modal;
  var select=document.getElementById('publication-select'),notice=document.getElementById('notice'),context=document.getElementById('page-context'),tableTarget=document.getElementById('context-table'),current=null;
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
  function load(publication){
    current=publication;notice.className='notice';notice.textContent='正在读取当前发布版本摘要…';context.textContent='交易日 '+format.text(publication.trade_date)+' · publication_id '+format.text(publication.publication_id);
    setText('publication-value',publication.trade_date);setText('publication-detail',publication.publication_id);
    Promise.all([api.identity(publication.publication_id,true),api.universeSummary(publication.publication_id)]).then(function(values){
      var identity=values[0]||{},universe=values[1]||{};
      setText('identity-value',first(identity,['source_revision_id','source_bundle_id','status'])||'已绑定');setText('identity-detail',first(identity,['api_contract','contract'])||'输入身份可追溯');
      var count=first(universe,['display_count','quote_valid_count','total']);setText('universe-value',count===null?'已加载':format.number(count,0));setText('universe-detail',first(universe,['scope','classification_summary'])||'统一 A 股范围');
      renderContext(publication,identity,universe);notice.textContent='摘要已加载；明细页面按升级步骤逐步接入。';
      document.getElementById('identity-evidence').onclick=function(){modal.open('输入身份证据',JSON.stringify(identity,null,2));};
      document.getElementById('universe-evidence').onclick=function(){modal.open('统一股票范围边界',JSON.stringify(universe,null,2));};
    }).catch(function(error){notice.className='notice error';notice.textContent='摘要读取失败：'+error.message;});
  }
  api.publications(true).then(function(result){
    var items=result.items||[];select.replaceChildren.apply(select,publicationRows(items));
    if(!items.length){notice.className='notice error';notice.textContent='没有可用的成功发布版本';return;}
    var wanted=new URLSearchParams(location.search).get('publication_id');current=items.find(function(item){return item.publication_id===wanted;})||items[0];select.value=current.publication_id;select.addEventListener('change',function(){load(items.find(function(item){return item.publication_id===select.value;}));});load(current);
  }).catch(function(error){notice.className='notice error';notice.textContent='版本列表读取失败：'+error.message;});
  document.querySelectorAll('.nav-item').forEach(function(button){button.addEventListener('click',function(){document.querySelectorAll('.nav-item').forEach(function(item){item.classList.remove('active');});button.classList.add('active');if(button.dataset.page!=='overview'){modal.open('页面预览',button.textContent+' 页面将在后续升级步骤接入。');}});});
}());
