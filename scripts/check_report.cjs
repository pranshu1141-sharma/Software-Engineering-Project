const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const {chromium} = require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'reports', 'report_qa');
fs.mkdirSync(out, {recursive:true});
(async()=>{
 const browser = await chromium.launch({channel:'chrome',headless:true});
 const page = await browser.newPage({viewport:{width:1440,height:1050},deviceScaleFactor:1});
 const errors=[];
 page.on('pageerror', e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(root,'reports/dashboard/index.html')).href);
 await page.waitForFunction(()=>document.getElementById('model-table').children.length===4);
 await page.locator('#comparison-img').evaluate(img=>img.decode());
 await page.screenshot({path:path.join(out,'overview-desktop.png'),fullPage:true});
 const body=await page.locator('#model-table').innerText();
 for(const name of ['condition_baseline','specialty_baseline','specialty_distilbert']){
   const m=JSON.parse(fs.readFileSync(path.join(root,`reports/${name}_metrics.json`),'utf8'));
   if(!body.includes((m.test.accuracy*100).toFixed(2)+'%')) throw Error('Displayed results do not match saved metrics: '+name);
 }
 await page.locator('[data-view="training"]').click();
 const latestTransformer=JSON.parse(fs.readFileSync(path.join(root,'reports/specialty_distilbert_metrics.json'),'utf8'));
 if(await page.locator('#epoch-table tr').count()!==latestTransformer.history.length) throw Error('Epoch history missing.');
 if(!(await page.locator('#checkpoint-caption').innerText()).includes('epoch '+latestTransformer.best_epoch+' of '+latestTransformer.config.epochs)) throw Error('Stale checkpoint caption.');
 await page.locator('#training-img').evaluate(img=>img.decode());
 await page.screenshot({path:path.join(out,'training-desktop.png'),fullPage:true});
 await page.locator('[data-view="evaluation"]').click();
 const counts={};
 for(const model of ['specialty_baseline','specialty_distilbert','condition_baseline']){
   await page.locator('#model-select').selectOption(model);
   const rows=await page.locator('#prediction-table tr').count();
   const metrics=JSON.parse(fs.readFileSync(path.join(root,`reports/${model}_metrics.json`),'utf8'));
   const expected=Math.round((1-metrics.test.accuracy)*metrics.test.sample_size);
   if(rows!==expected) throw Error(`Wrong error count ${model}: ${rows}, expected ${expected}`);
   counts[model]=rows;
 }
 await page.locator('#model-select').selectOption('specialty_distilbert');
 await page.locator('#confusion-img').evaluate(img=>img.decode());
 await page.screenshot({path:path.join(out,'evaluation-desktop.png'),fullPage:true});
 await page.locator('#prediction-filter').selectOption('all');
 if(await page.locator('#prediction-table tr').count()!==212) throw Error('All predictions filter failed.');
 const downloadWait=page.waitForEvent('download');
 await page.locator('#download-predictions').click();
 const download=await downloadWait;
 await download.saveAs(path.join(out,'exported_predictions.csv'));
 await page.locator('[data-view="logs"]').click();
 await page.locator('[data-log="gpuLog"]').click();
 if(!(await page.locator('#raw-log').innerText()).includes('14 passed')) throw Error('Final verification missing from process log.');
 await page.locator('.event').first().locator('summary').click();
 await page.screenshot({path:path.join(out,'logs-desktop.png'),fullPage:true});
 await page.locator('[data-view="exports"]').click();
 const links=await page.locator('a[download]').evaluateAll(elements=>elements.map(e=>e.getAttribute('href')).filter(x=>x.startsWith('../')));
 for(const link of links){
   if(!fs.existsSync(path.resolve(root,'reports/dashboard',decodeURIComponent(link)))) throw Error('Missing export: '+link);
 }
 await page.setViewportSize({width:390,height:844});
 await page.locator('[data-view="overview"]').click();
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
 if(overflow) throw Error('Mobile viewport has page overflow.');
 await page.screenshot({path:path.join(out,'overview-mobile.png'),fullPage:true});
 if(errors.length) throw Error(errors.join('\n'));
 await browser.close();
 const result={status:'passed',javascriptErrors:errors,predictionErrorCounts:counts,checkedDownloadLinks:links.length,
   checks:['All 5 sections','Saved numerical metrics','Latest epoch history and checkpoint caption','Model selector','Error/all prediction filter','CSV download','Original GPU log','Export file existence','390px mobile overflow']};
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exit(1)});
