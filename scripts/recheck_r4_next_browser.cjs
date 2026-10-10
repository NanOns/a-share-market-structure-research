// Real 28765 differential checks; all interactions are read-only.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
(async()=>{const out=path.resolve(process.argv[2]);fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});const results=[];
try{for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
 const page=await browser.newPage({viewport});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const origin='http://127.0.0.1:28765';
 for(const [route,title] of [['home','今日总览'],['sectors','板块研究'],['stocks','个股研究'],['focus','关注跟踪'],['market','市场与事件'],['diagnostics','数据与诊断']]){
  await page.goto(origin+'/v4/research/'+route+'?trade_date=2026-10-09');
  await page.getByRole('heading',{name:title,exact:true,level:1}).waitFor();
  await page.getByText('正在读取当前生产快照…',{exact:true}).waitFor({state:'hidden'});
  assert.equal(await page.locator('nav a').count(),6);
  assert.equal(await page.getByRole('combobox',{name:'研究日期'}).inputValue(),'2026-10-09');
  const nav=page.locator('nav a').filter({hasText:route==='home'?'个股研究':'今日总览'});
  await nav.click();await page.getByRole('heading',{name:route==='home'?'个股研究':'今日总览',exact:true,level:1}).waitFor();
  assert(page.url().includes('trade_date=2026-10-09'));
  results.push({viewport,route,six_navigation_links:true,date_retained:true,status:'PASS'});
 }
 await page.goto(origin+'/v4/research/stocks?q=688349&trade_date=2026-09-30');
 await page.getByRole('cell',{name:'13.240',exact:true}).waitFor();
 assert.equal(await page.getByRole('searchbox',{name:'搜索代码或名称'}).inputValue(),'688349');
 await page.screenshot({path:path.join(out,viewport.width+'_historical.png'),fullPage:true});
 await page.goto(origin+'/v4/research/stocks?q=301628&trade_date=2026-10-09');
 await page.locator('main table tbody tr').first().waitFor();
 await page.locator('main table tbody tr a').first().click();
 await page.getByText('失效',{exact:true}).first().waitFor();
 await page.getByText('正在读取当前生产快照…',{exact:true}).waitFor({state:'hidden'});
 await page.screenshot({path:path.join(out,viewport.width+'_invalidated.png'),fullPage:true});
 await page.getByRole('link',{name:'← 返回个股研究',exact:true}).click();
 await page.getByRole('searchbox',{name:'搜索代码或名称'}).waitFor();
 assert(page.url().includes('q=301628'));assert(page.url().includes('trade_date=2026-10-09'));
 await page.goto(origin+'/v4/research/stocks?offset=25&trade_date=2026-10-09');
 await page.locator('main table tbody tr a').first().waitFor();
 await page.locator('main table tbody tr a').first().click();
 await page.getByRole('link',{name:'← 返回个股研究',exact:true}).click();
 await page.locator('main table tbody tr').first().waitFor();
 assert(page.url().includes('offset=25'));assert(page.url().includes('trade_date=2026-10-09'));
 assert.deepEqual(errors,[]);results.push({viewport,historical_close:'13.240 CNY',current_state:'INVALIDATED (失效)',search_return_retained:true,pagination_return_retained:true,page_errors:errors,status:'PASS'});
 await page.close();
}fs.writeFileSync(path.join(out,'E_DIFFERENTIAL_BROWSER_RECEIPT.json'),JSON.stringify({origin:'http://127.0.0.1:28765',external_acceptance:false,results},null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
