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
    publications:function(){return get('/api/publications');},
    identity:function(publicationId){return get('/api/identity',{publication_id:publicationId});},
    universeSummary:function(publicationId){return get('/api/universe/summary',{publication_id:publicationId});}
  };
}());
