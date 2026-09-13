(function(){
  'use strict';
  var responseCache=new Map(), CACHE_LIMIT=24, CACHE_TTL_MS=30000;
  var perfStats={requests:0,completed:0,cache_hits:0,cache_misses:0,aborted:0,errors:0,samples:[]};
  function recordSample(path,duration,kind,status){
    perfStats.samples.push({path:path,duration_ms:Math.round(duration*100)/100,kind:kind,status:status});
    if(perfStats.samples.length>120) perfStats.samples.shift();
  }
  function cachePut(key,value){
    if(responseCache.has(key)) responseCache.delete(key);
    responseCache.set(key,{value:value,expires:Date.now()+CACHE_TTL_MS});
    while(responseCache.size>CACHE_LIMIT) responseCache.delete(responseCache.keys().next().value);
  }
  function get(path, params, options){
    var url=new URL(path,window.location.origin);
    Object.keys(params||{}).forEach(function(key){
      var value=params[key];
      if(value!==undefined&&value!==null&&value!=='') url.searchParams.set(key,String(value));
    });
    options=options||{};
    var key=url.toString(), now=Date.now(), cached=options.cache===false?null:responseCache.get(key);
    if(cached&&cached.expires>now){
      responseCache.delete(key);responseCache.set(key,cached);perfStats.cache_hits++;recordSample(path,0,'HIT','CACHE');return Promise.resolve(cached.value);
    }
    if(cached) responseCache.delete(key);
    perfStats.requests++;perfStats.cache_misses++;
    var started=Date.now(), request={headers:{Accept:'application/json'}};
    if(options&&options.signal) request.signal=options.signal;
    return fetch(url.toString(),request).then(function(response){
      return response.json().catch(function(){return {};}).then(function(body){
        if(!response.ok) { perfStats.errors++;recordSample(path,Date.now()-started,'MISS','HTTP_'+response.status); var error=new Error(body.message||body.code||'请求失败'); error.code=body.code||''; throw error; }
        perfStats.completed++;recordSample(path,Date.now()-started,'MISS','OK');if(options.cache!==false) cachePut(key,body);
        return body;
      });
    }).catch(function(error){if(error&&error.name==='AbortError') perfStats.aborted++;throw error;});
  }
  function csrfToken(){
    var node=document.querySelector('meta[name="csrf-token"]');
    return node?node.getAttribute('content'):'';
  }
  window.WorkbenchV2Api={
    get:get,
    publications:function(includeAnalysis){return get('/api/publications',{include_analysis:includeAnalysis?'1':undefined});},
    dashboard:function(params,options){return get('/api/dashboard',params||{},options);},
    candidates:function(params,options){return get('/api/candidates',params||{},options);},
    identity:function(publicationId,includeAnalysis,options){return get('/api/identity',{publication_id:publicationId,include_analysis:includeAnalysis?'1':undefined},options);},
    universeSummary:function(publicationId,options){return get('/api/universe/summary',{publication_id:publicationId},options);},
    researchContext:function(params,options){return get('/api/v3/research/context',params||{},options);},
    sectorLibrary:function(params,options){return get('/api/sector-library',params,options);},
    sectorIntersectionQuery:function(params,options){
      var request={method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json','X-CSRF-Token':csrfToken()},body:JSON.stringify(params)};
      if(options&&options.signal) request.signal=options.signal;
      return fetch('/api/sector-intersection/query',request).then(function(response){
        return response.json().catch(function(){return {};}).then(function(body){if(!response.ok) { var error=new Error(body.message||body.code||'请求失败'); error.code=body.code||''; throw error; }return body;});
      }).catch(function(error){if(error&&error.name==='AbortError') perfStats.aborted++;throw error;});
    },
      stockMemberships:function(params){
        var securityId=encodeURIComponent(params.security_id);var query=Object.assign({},params);delete query.security_id;
        return get('/api/stocks/'+securityId+'/memberships',query);
      },
      linkage:function(params,options){return get('/api/linkage',params||{},options);},
      linkageHistory:function(params,options){return get('/api/linkage/history',params||{},options);},
    sectorAssociations:function(params){
      var securityId=encodeURIComponent(params.security_id);var query=Object.assign({},params);delete query.security_id;
      return get('/api/stocks/'+securityId+'/sector-associations',query);
    },
    stockInsight:function(params,options){
      var securityId=encodeURIComponent(params.security_id);var query=Object.assign({},params);delete query.security_id;
      return get('/api/stocks/'+securityId+'/insight',query,options);
    },
    evidence:function(params,options){return get('/api/evidence',params||{},options);},
    marketCycle:function(params,options){return get('/api/market/cycle',params||{},options);},
    marketDayDetail:function(params,options){return get('/api/market/day-detail',params||{},options);},
    hotRankings:function(params,options){return get('/api/hot-rankings',params||{},Object.assign({cache:false},options||{}));},
    limitLadder:function(params,options){return get('/api/limit-ladder',params||{},options);},
    limitPromotionHistory:function(params,options){return get('/api/limit-ladder/promotion-history',params||{},options);},
    sectorCycle:function(params,options){return get('/api/sectors/cycle',params,options);},
    mainlines:function(params,options){return get('/api/mainlines',params,options);},
    mainlineEvidence:function(params,options){
      var sectorId=encodeURIComponent(params.sector_id);var query=Object.assign({},params);delete query.sector_id;
      return get('/api/mainlines/'+sectorId+'/evidence',query,options);
    },
    sectorTimeline:function(params,options){
      var sectorId=encodeURIComponent(params.sector_id);var query=Object.assign({},params);delete query.sector_id;
      return get('/api/sectors/'+sectorId+'/timeline',query,options);
    },
    sectorMembersHistory:function(params,options){
      var sectorId=encodeURIComponent(params.sector_id);var query=Object.assign({},params);delete query.sector_id;
      return get('/api/sectors/'+sectorId+'/members/history',query,options);
    },
    sectorLeaderHistory:function(params,options){
      var sectorId=encodeURIComponent(params.sector_id);var query=Object.assign({},params);delete query.sector_id;
      return get('/api/sectors/'+sectorId+'/leader-history',query,options);
    },
    technical:function(params,options){return get('/api/stocks/technical',params,options);},
    newHighs:function(params,options){return get('/api/stocks/new-highs',params,options);},
    technicalHistory:function(params,options){
      var securityId=encodeURIComponent(params.security_id);
      var query=Object.assign({},params);delete query.security_id;
      return get('/api/stocks/'+securityId+'/technical-history',query,options);
    },
    structureHistory:function(params,options){
      var securityId=encodeURIComponent(params.security_id);
      var query=Object.assign({},params);delete query.security_id;
      return get('/api/stocks/'+securityId+'/structure-history',query,options);
    },
    perf:function(){return {requests:perfStats.requests,completed:perfStats.completed,cache_hits:perfStats.cache_hits,cache_misses:perfStats.cache_misses,aborted:perfStats.aborted,errors:perfStats.errors,cache_size:responseCache.size,cache_limit:CACHE_LIMIT,cache_ttl_ms:CACHE_TTL_MS,samples:perfStats.samples.slice()};},
    clearCache:function(){responseCache.clear();}
  };
  window.WorkbenchV2Perf=window.WorkbenchV2Api.perf;
}());
