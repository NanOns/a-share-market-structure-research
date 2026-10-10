// Controlled browser response fault against real production; never changes server data.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(process.argv[2]);fs.mkdirSync(root,{recursive:true});
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
const results=[];
for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
const page=await browser.newPage({viewport});const requests=[];let inject=true;
page.on('request',r=>{if(r.url().includes('/api/'))requests.push(r.url());});
await page.route('**/market/breadth*',async route=>{if(inject){inject=false;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({status:'SOURCE_INCOMPLETE',message:'Controlled breadth 503 regression fault'})});}else await route.continue();});
await page.goto('http://127.0.0.1:28765/v4/research/market?trade_date=2026-10-09');
const section=page.locator('main > section').filter({has:page.getByRole('heading',{name:'市场宽度与成交额',exact:true})});
await section.getByRole('button',{name:'重试',exact:true}).waitFor();
await page.getByRole('heading',{name:'正式研究结构事件',exact:true}).waitFor();
await page.locator('main table').first().waitFor();
await page.getByText('正在读取当前生产快照…',{exact:true}).waitFor({state:'hidden'});
const unaffected=await page.locator('main > section').evaluateAll(nodes=>nodes.filter(n=>n.querySelector('h2')?.textContent!=='市场宽度与成交额').map(n=>n.outerHTML));
fs.writeFileSync(path.join(root,`${viewport.width}_fault.html`),await page.content());await page.screenshot({path:path.join(root,`${viewport.width}_fault.png`),fullPage:true});
const before=requests.length;await section.getByRole('button',{name:'重试',exact:true}).click();
await section.getByText(/分母 .*实际行情/).waitFor();
const after=await page.locator('main > section').evaluateAll(nodes=>nodes.filter(n=>n.querySelector('h2')?.textContent!=='市场宽度与成交额').map(n=>n.outerHTML));
assert.deepStrictEqual(after,unaffected);const retry=requests.slice(before);assert(retry.length===1&&retry[0].includes('/market/breadth'));assert(page.url().includes('trade_date=2026-10-09'));
fs.writeFileSync(path.join(root,`${viewport.width}_recovered.html`),await page.content());await page.screenshot({path:path.join(root,`${viewport.width}_recovered.png`),fullPage:true});
results.push({viewport,origin:'http://127.0.0.1:28765',fault:'browser_intercepted_503_one_response',server_fault:false,retry_requests:retry,unaffected_sections_identical:true,date_retained:true,status:'PASS'});await page.close();}
fs.writeFileSync(path.join(root,'E_BREADTH_503_BROWSER_RECEIPT.json'),JSON.stringify({contract:'R4_BREADTH_FAULT_REPLAY_R1',results},null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
