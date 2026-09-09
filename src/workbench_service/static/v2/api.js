(function(){
  'use strict';
  function get(path, params){
    var url=new URL(path,window.location.origin);
    Object.keys(params||{}).forEach(function(key){
      var value=params[key];
      if(value!==undefined&&value!==null&&value!=='') url.searchParams.set(key,String(value));
    });
    return fetch(url.toString(),{headers:{Accept:'application/json'}}).then(function(response){
      return response.json().catch(function(){return {};}).then(function(body){
        if(!response.ok) throw new Error(body.message||body.code||'请求失败');
        return body;
      });
    });
  }
  window.WorkbenchV2Api={
    get:get,
    publications:function(includeAnalysis){return get('/api/publications',{include_analysis:includeAnalysis?'1':undefined});},
    identity:function(publicationId,includeAnalysis){return get('/api/identity',{publication_id:publicationId,include_analysis:includeAnalysis?'1':undefined});},
    universeSummary:function(publicationId){return get('/api/universe/summary',{publication_id:publicationId});},
    sectorCycle:function(params){return get('/api/sectors/cycle',params);},
    sectorTimeline:function(params){
      var sectorId=encodeURIComponent(params.sector_id);var query=Object.assign({},params);delete query.sector_id;
      return get('/api/sectors/'+sectorId+'/timeline',query);
    },
    sectorMembersHistory:function(params){
      var sectorId=encodeURIComponent(params.sector_id);var query=Object.assign({},params);delete query.sector_id;
      return get('/api/sectors/'+sectorId+'/members/history',query);
    },
    sectorLeaderHistory:function(params){
      var sectorId=encodeURIComponent(params.sector_id);var query=Object.assign({},params);delete query.sector_id;
      return get('/api/sectors/'+sectorId+'/leader-history',query);
    },
    technical:function(params){return get('/api/stocks/technical',params);},
    newHighs:function(params){return get('/api/stocks/new-highs',params);},
    technicalHistory:function(params){
      var securityId=encodeURIComponent(params.security_id);
      var query=Object.assign({},params);delete query.security_id;
      return get('/api/stocks/'+securityId+'/technical-history',query);
    },
    structureHistory:function(params){
      var securityId=encodeURIComponent(params.security_id);
      var query=Object.assign({},params);delete query.security_id;
      return get('/api/stocks/'+securityId+'/structure-history',query);
    }
  };
}());
