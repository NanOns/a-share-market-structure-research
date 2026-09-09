const operationKeyCN={revision:'配置版本',valid:'校验通过',config:'配置',validation:'校验报告',resolved_managed_write_roots:'受管写入目录',resolved_backup_root:'备份目录',resolved_database_path:'数据库路径',cleanup_job_id:'清理计划编号',state:'状态',eligible:'可处理对象',protected:'受保护对象',reason:'保护原因',backup_id:'备份编号',path:'路径',sha256:'文件摘要',created_at_utc:'创建时间',source_database:'源数据库',verification:'抽检结果',publication_heads:'发布头',queue_memberships:'队列记录',membership_entries:'成员记录',outcomes:'Forward记录',restore_drill_path:'恢复演练路径',status:'结果',target_database:'目标数据库',operation:'操作',completed_at_utc:'完成时间',result:'执行结果',message:'说明',pid:'进程号'};
function operationChinese(value){if(Array.isArray(value))return value.map(operationChinese);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,item])=>[operationKeyCN[key]||key,operationChinese(item)]));return value}
result=function(id,title,value,good=true){const element=document.getElementById(id);element.className='notice '+(good?'ok':'warn');element.textContent=title+'\n'+JSON.stringify(operationChinese(value),null,2)};
const _operationFetch=window.fetch.bind(window);
window.fetch=async function(input,init={}){
 if(typeof input==='string'&&input.includes('/api/operations/storage/')&&init.method==='POST'){
  const payload=JSON.parse(init.body||'{}');payload.confirmation=document.querySelector('.confirmation')?.value||'';
  init={...init,body:JSON.stringify(payload)};
 }
 return _operationFetch(input,init);
};
