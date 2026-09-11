(function(){
  'use strict';
  var active=null,lastFocus=null,closeHandlers=[],titleId=0;
  function close(){if(!active)return;active.hidden=true;active.setAttribute('aria-hidden','true');active.replaceChildren();if(lastFocus&&lastFocus.focus)lastFocus.focus();active=null;closeHandlers.slice().forEach(function(handler){handler();});}
  function open(title,body){
    close();lastFocus=document.activeElement;active=document.getElementById('modal');
    var card=document.createElement('section');card.className='modal-card';card.setAttribute('role','dialog');card.setAttribute('aria-modal','true');
    var head=document.createElement('div');head.className='modal-head';var heading=document.createElement('h2');heading.id='modal-title-'+(++titleId);heading.textContent=title;card.setAttribute('aria-labelledby',heading.id);var button=document.createElement('button');button.type='button';button.className='modal-close';button.setAttribute('aria-label','关闭');button.textContent='×';button.addEventListener('click',close);head.append(heading,button);
    var content=document.createElement('div');content.className='modal-body';
    if(body&&body.nodeType){content.appendChild(body);}else{content.textContent=body===null||body===undefined?'—':String(body);}
    card.append(head,content);active.appendChild(card);active.hidden=false;active.setAttribute('aria-hidden','false');button.focus();
  }
  document.addEventListener('keydown',function(event){
    if(event.key==='Escape'){close();return;}
    if(event.key!=='Tab'||!active)return;
    var focusable=Array.prototype.slice.call(active.querySelectorAll('button,summary,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')).filter(function(node){return !node.disabled&&node.offsetParent!==null;});
    if(!focusable.length){event.preventDefault();return;}
    var first=focusable[0],last=focusable[focusable.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  });
  document.addEventListener('click',function(event){if(active&&event.target===active)close();});
  function onClose(handler){if(typeof handler==='function')closeHandlers.push(handler);}
  window.WorkbenchV2Modal={open:open,close:close,onClose:onClose,isOpen:function(){return !!active;}};
}());
