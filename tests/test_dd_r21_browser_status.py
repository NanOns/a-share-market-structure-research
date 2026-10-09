"""Execute actual page JS with a lost HTTP connection; no browser/service claim."""
import json,subprocess,shutil
from pathlib import Path

def test_service_disconnect_does_not_keep_running_label(tmp_path):
    node=shutil.which('node')
    assert node,'NODE_REQUIRED_FOR_ACTUAL_PAGE_JS_REPLAY'
    source=Path(__file__).resolve().parents[1]/'src/workbench_service/static/daily-update/app.js'
    runner=r'''
const fs=require('fs');const elements={};
global.document={getElementById:id=>elements[id]||(elements[id]={textContent:'',replaceChildren(){},append(){}}),createElement:()=>({append(){}})};
global.setInterval=()=>0;
global.fetch=async()=>{throw Error('ISOLATED_SERVICE_DISCONNECT')};
elements.status={textContent:'后台存活'};elements.job={textContent:'后台执行中'};
const code=fs.readFileSync(process.argv[1],'utf8');
const execute=new Function('return (async()=>{'+code+'\nawait refresh();return {status:$("status").textContent,job:$("job").textContent,error:$("error").textContent};})()');
execute().then(result=>{console.log(JSON.stringify(result));if(result.job.includes('后台执行中')||!result.status.includes('无法确认'))process.exit(1)});
'''
    result=subprocess.run([node,'-e',runner,str(source)],capture_output=True,text=True,encoding='utf8',timeout=20)
    assert result.returncode==0,result.stderr
    payload=json.loads(result.stdout)
    assert '无法确认' in payload['job']
