(function(){
  'use strict';
  var active=null,lastFocus=null;
  function close(){if(!active)return;active.hidden=true;active.setAttribute('aria-hidden','true');active.replaceChildren();if(lastFocus&&lastFocus.focus)lastFocus.focus();active=null;}
  function open(title,body){
    close();lastFocus=document.activeElement;active=document.getElementById('modal');
    var card=document.createElement('section');card.className='modal-card';card.setAttribute('role','dialog');card.setAttribute('aria-modal','true');
    var head=document.createElement('div');head.className='modal-head';var heading=document.createElement('h2');heading.textContent=title;var button=document.createElement('button');button.type='button';button.className='modal-close';button.setAttribute('aria-label','关闭');button.textContent='×';button.addEventListener('click',close);head.append(heading,button);
    var content=document.createElement('div');content.className='modal-body';content.textContent=body===null||body===undefined?'—':String(body);card.append(head,content);active.appendChild(card);active.hidden=false;active.setAttribute('aria-hidden','false');button.focus();
  }
  document.addEventListener('keydown',function(event){if(event.key==='Escape')close();});
  document.addEventListener('click',function(event){if(active&&event.target===active)close();});
  window.WorkbenchV2Modal={open:open,close:close};
}());
