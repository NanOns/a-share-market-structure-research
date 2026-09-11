(function(){
  'use strict';
  function escape(value){var node=document.createElement('span');node.textContent=value===null||value===undefined?'':String(value);return node.innerHTML;}
  function number(value,digits){var n=Number(value);return Number.isFinite(n)?n.toLocaleString('zh-CN',{minimumFractionDigits:digits,maximumFractionDigits:digits}):'—';}
  function amount(value){
    if(value===null||value===undefined||value==='')return '—';
    var n=Number(value),abs=Math.abs(n);
    if(!Number.isFinite(n))return '—';
    if(abs>=1e12)return number(n/1e12,2)+'万亿';
    if(abs>=1e8)return number(n/1e8,2)+'亿';
    if(abs>=1e4)return number(n/1e4,2)+'万';
    return number(n,2);
  }
  function percent(value){return value===null||value===undefined||value===''?'—':number(value,2)+'%';}
  function text(value){return value===null||value===undefined||value===''?'—':String(value);}
  window.WorkbenchV2Format={escape:escape,amount:amount,percent:percent,text:text,number:number};
}());
