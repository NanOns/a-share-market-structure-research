(function(){
  'use strict';
  function render(target,columns,rows){
    target.replaceChildren();
    if(!rows||!rows.length){var empty=document.createElement('p');empty.className='empty';empty.textContent='暂无数据';target.appendChild(empty);return;}
    var table=document.createElement('table');table.className='context-table';
    var head=document.createElement('thead'),headRow=document.createElement('tr');
    columns.forEach(function(column){var th=document.createElement('th');th.textContent=column.label;headRow.appendChild(th);});
    head.appendChild(headRow);table.appendChild(head);
    var body=document.createElement('tbody');
    rows.forEach(function(row){
      var tr=document.createElement('tr');
      columns.forEach(function(column){
        var td=document.createElement('td');
        if(column.action){td.className='table-action';var button=document.createElement('button');button.type='button';button.textContent=column.action.label;button.addEventListener('click',function(){column.action.onClick(row);});td.appendChild(button);}
        else{var value=column.value?column.value(row):row[column.key];td.textContent=value===null||value===undefined?'—':String(value);}
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    table.appendChild(body);target.appendChild(table);
  }
  window.WorkbenchV2Table={render:render};
}());
