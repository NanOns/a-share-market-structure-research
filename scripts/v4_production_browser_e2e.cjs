// Real running service only; no intercepted responses or mock fixtures.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
async function main(){
  const root=path.resolve(__dirname,'..');const output=path.join(root,'reports/v4_production_cutover_20261007');
  const base=process.env.V4_E2E_URL||'http://127.0.0.1:28766';
  const browser=await chromium.launch({headless:true,channel:'msedge'});
  const page=await browser.newPage({viewport:{width:1400,height:1000}});const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(base+'/v4');await page.waitForFunction(()=>window.V4Context);
  await page.locator('#health article').first().waitFor();
  const context=await page.evaluate(()=>window.V4Context);
  if(context.context.accepted_trade_date!=='2026-09-30'||context.status!=='READY_CURRENT_ACCEPTED')throw Error('Incorrect accepted context');
  if((await page.locator('.content .error').count())!==0)throw Error('Module source error');
  const files=[];
  async function capture(name,locator){await locator.screenshot({path:path.join(output,name)});files.push(name);}
  await page.screenshot({path:path.join(output,'01_HOME_CURRENT_ACCEPTED.png')});files.push('01_HOME_CURRENT_ACCEPTED.png');
  for(const [name,selector] of [['02_WHY_NOW.png','#summary'],['03_RADAR.png','#radar'],['04_ENTITY_AND_SECTOR.png','#entity'],['04_SECTOR.png','#sector'],['05_FORWARD_STATE.png','#cohort'],['05_SETTLEMENT.png','#settlement'],['06_HEALTH_AND_FRESHNESS.png','#health']])await capture(name,page.locator(selector));
  await page.getByRole('textbox',{name:'股票搜索',exact:true}).fill('688349');
  await page.waitForFunction(()=>document.querySelector('#entity .content').textContent.includes('1 条'));
  if(await page.locator('#entity article').count()!==1)throw Error('Search failed');
  await page.getByRole('button',{name:'刷新当前已接受状态'}).click();
  await page.waitForFunction(token=>window.V4Context.context_token===token,context.context_token);
  await page.goto(base+'/v4?q=688349');await page.waitForFunction(()=>window.V4Context);await page.locator('#entity article').first().waitFor();
  if((await page.evaluate(()=>window.V4Context.context_token))!==context.context_token)throw Error('Deep link changed context');
  await page.goto(base+'/v4/shadow');await page.getByRole('status').filter({hasText:'NO_REAL_SHADOW_DATA'}).waitFor();
  await page.screenshot({path:path.join(output,'07_SHADOW_NO_REAL_DATA.png')});files.push('07_SHADOW_NO_REAL_DATA.png');
  if(errors.length)throw Error(errors.join('\n'));
  const receipt={status:'PASS_REAL_SERVICE_E2E',base,context,search:true,refresh_stability:true,deep_link_stability:true,shadow_separation:true,browser_errors:errors,screenshots:files,fixture:false};
  for(const name of ['UI_E2E_RECEIPT.json','SCREENSHOT_MANIFEST.json']){const file=path.join(output,name);fs.writeFileSync(file+'.tmp',JSON.stringify(receipt,null,2)+'\n');fs.renameSync(file+'.tmp',file);}
  await browser.close();console.log(JSON.stringify({status:receipt.status,screenshots:files}));
}
main().catch(error=>{console.error(error);process.exit(1);});
