import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const {chromium}=createRequire(import.meta.url)('C:\\Users\\pc\\AppData\\Local\\npm-cache\\_npx\\e41f203b7505f1fb\\node_modules\\playwright-core');
const cache=path.join(process.env.LOCALAPPDATA,'ms-playwright');
const executablePath=fs.readdirSync(cache).filter(n=>/^chromium-\d+$/.test(n)).sort().reverse().map(n=>path.join(cache,n,'chrome-win64','chrome.exe')).find(fs.existsSync);
const base=process.env.FWD07_UAT_BASE_URL,evidence=process.env.FWD07_UAT_EVIDENCE_DIR;
assert(executablePath&&base&&evidence&&process.env.FWD_TEST_MANIFEST,'Missing owned prerequisites');fs.mkdirSync(evidence,{recursive:true});
const started=Date.now(),checks=[],steps=[],errors=[],api=[];let browser,context,page,current='S1',last=null;
const record=(name,detail={})=>{checks.push({name,...detail});console.log(name);};
const step=async(name,action)=>{current=name;const begin=Date.now();await action();last=name;steps.push({name,elapsedMs:Date.now()-begin});console.log(name);};
const pdf=s=>Buffer.from(`%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n${s}`);
const file=(name,buffer,mimeType='application/pdf')=>({name,buffer,mimeType});
try{
 browser=await chromium.launch({executablePath,headless:true});
 for(const width of (process.env.FWD07_UAT_VIEWPORT ? [Number(process.env.FWD07_UAT_VIEWPORT)] : [1280,390])){
 context=await browser.newContext({viewport:{width,height:width===390?844:800},acceptDownloads:true});if(process.env.FWD07_UAT_ZERO!=='1')await context.tracing.start({screenshots:true,snapshots:true,sources:false});{
 const manifest=JSON.parse(fs.readFileSync(process.env.FWD_TEST_MANIFEST,'utf8'));
 assert.equal(path.resolve(evidence),path.resolve(manifest.root));
 const origins=manifest.local_endpoints.map(([host,port])=>`http://${host}:${port}`);
 assert(origins.includes(base));assert(origins.includes(process.env.VITE_BACKEND_URL));
 await context.route('**/*',async route=>{const u=new URL(route.request().url());if(!origins.includes(u.origin)){record('external-resource-blocked',{origin:u.origin});await route.abort();return;}await route.continue();});
 await context.routeWebSocket(/.*/,ws=>{const u=new URL(ws.url());if(origins.includes(u.origin.replace('ws:','http:')))ws.connectToServer();else{record('external-websocket-blocked');ws.close();}});
 }page=await context.newPage();page.setDefaultTimeout(10000);page.setDefaultNavigationTimeout(15000);
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.url().includes('/api/'))api.push({path:new URL(r.url()).pathname,status:r.status(),method:r.request().method()});});
 await step('S1',async()=>{await page.goto(base,{waitUntil:process.env.FWD07_UAT_ZERO==='1'?'domcontentloaded':'networkidle'});});
 await step('S2',async()=>{if(width===390)await page.getByRole('button',{name:'منوی سامانه',exact:true}).click();await page.getByRole('button',{name:'ورود به سامانه'}).click();await page.getByLabel('نام کاربری').fill('fwd07-expert');await page.getByLabel('رمز عبور').fill(process.env.FWD07_UAT_PASSWORD);await page.getByRole('button',{name:'ورود',exact:true}).click();await page.waitForURL(/\/expert/);});
 const tracking=`SR-FWD07-BROWSER-${width}`;
 const open=async()=>{await page.getByText(tracking,{exact:true}).waitFor();await page.getByText(tracking,{exact:true}).locator("xpath=ancestor::*[.//button[contains(.,'مشاهده جزئیات')]][1]").getByRole('button',{name:'مشاهده جزئیات'}).click();await page.waitForURL(/\/expert\/requests\//);};
 await step('S3',open);
 const tab=page.getByRole('tab',{name:process.env.FWD07_UAT_DIAGNOSE_OLD_SELECTOR?/مدارک|اسناد/:'مستندات پرونده',exact:!process.env.FWD07_UAT_DIAGNOSE_OLD_SELECTOR});
 await step('S4',async()=>{await tab.waitFor({state:'visible'});assert(await tab.isEnabled());});
 if(process.env.FWD07_UAT_ZERO==='1'){
 const pending=page.waitForResponse(r=>/\/documents$/.test(new URL(r.url()).pathname)&&r.request().method()==='GET');
 await tab.click();const result=await pending;assert.equal(result.status(),200);const payload=await result.json();assert.deepEqual(payload.requirements,[]);assert.equal(payload.summary.total_requirements,0);assert.equal(payload.miscellaneous.length,0);
 await page.getByText('برای این پرونده نیازمندی مدرکی تعریف نشده است.',{exact:true}).waitFor();
 const input=page.getByLabel('افزودن سایر مستندات',{exact:true});assert.equal(await input.isDisabled(),true);
 await page.getByPlaceholder('عنوان الزامی',{exact:true}).fill('سند مصنوعی مجاز');assert.equal(await input.isEnabled(),true);
 const buffer=pdf('zero-requirement-synthetic');const sent=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().includes('/documents'));
 await input.setInputFiles(file('zero-proof.pdf',buffer));assert.equal((await sent).status(),201);await page.getByText('zero-proof.pdf: ثبت شد',{exact:true}).waitFor();
 await page.goto(base+'/expert');await page.getByRole('button',{name:'خروج',exact:true}).click();await page.waitForURL(base+'/');if(width===390)await page.getByRole('button',{name:'منوی سامانه',exact:true}).click();await page.getByRole('button',{name:'ورود به سامانه'}).click();await page.getByLabel('نام کاربری').fill('fwd07-expert');await page.getByLabel('رمز عبور').fill(process.env.FWD07_UAT_PASSWORD);await page.getByRole('button',{name:'ورود',exact:true}).click();await page.waitForURL(/\/expert/);await open();const listed=page.waitForResponse(r=>/\/documents$/.test(new URL(r.url()).pathname)&&r.request().method()==='GET');await page.getByRole('tab',{name:'مستندات پرونده',exact:true}).click();const reopened=await (await listed).json();assert.deepEqual(reopened.requirements,[]);assert.equal(reopened.miscellaneous.length,1);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'دریافت',exact:true}).click();const d=await download;const target=path.join(evidence,'zero-download-'+width);await d.saveAs(target);assert.deepEqual(fs.readFileSync(target),buffer);
 const layout=await page.evaluate(()=>({dir:document.documentElement.dir,scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));assert.equal(layout.dir,'rtl');assert(layout.scrollWidth<=layout.clientWidth+1);record('zero-requirement-'+width,{requirements:0,miscellaneous:1,reopened:true,downloadBytes:true,...layout});await page.getByText('ورود موفق',{exact:true}).waitFor({state:'hidden'});await page.screenshot({path:path.join(evidence,'zero-'+width+'.png'),fullPage:true});await context.close();context=null;continue;
 }
 let release;const delivery=new Promise(resolve=>{release=resolve;});await page.route('**/documents',async route=>{const real=await route.fetch();await delivery;await route.fulfill({response:real});},{times:1});const response=page.waitForResponse(r=>/\/documents$/.test(new URL(r.url()).pathname)&&r.request().method()==='GET').then(r=>({r}),error=>({error}));
 await step('S5',async()=>{await tab.click();await page.getByText('در حال بارگذاری...',{exact:true}).waitFor();record('loading-state-'+width);release();assert.equal(await tab.getAttribute('data-state'),'active');});let payload;
 await step('S6',async()=>{const received=await response;if(received.error)throw received.error;assert.equal(received.r.status(),200);payload=await received.r.json();});
 const input=page.getByLabel('افزودن فایل به مدرک فارسی با نام بلند',{exact:true});
 await step('S7',async()=>{await input.waitFor({state:'attached'});assert(await input.isEnabled());assert.equal(payload.requirements.length,1);assert.equal(payload.requirements[0].active_files.length,0);});
 await page.screenshot({path:path.join(evidence,'empty-files-'+width+'.png'),fullPage:true});record('empty-file-state-'+width);current='MULTI_FILE_JOURNEY';const selected=[file('مدرک-هم‌نام.pdf',pdf('first')),file('مدرک-هم‌نام.pdf',pdf('second')),file('تصویر-فارسی.png',Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=','base64'),'image/png')];
 await input.setInputFiles(selected);await page.getByText('تصویر-فارسی.png: ثبت شد',{exact:true}).waitFor();assert.equal(await page.getByText('مدرک-هم‌نام.pdf: ثبت شد',{exact:true}).count(),2);record(`independent-results-${width}`);
 const reopen=async()=>{await page.goto(`${base}/expert`);await open();await page.getByRole('tab',{name:'مستندات پرونده',exact:true}).click();await page.getByRole('button',{name:'دریافت',exact:true}).first().waitFor();};
 const verify=async()=>{const buttons=page.getByRole('button',{name:'دریافت',exact:true});assert.equal(await buttons.count(),selected.length);for(let i=0;i<selected.length;i++){const row=await buttons.nth(i).locator('xpath=../..').innerText();const version=Number(row.match(/نسخه (\d+)/)[1]);const expected=selected[version-1];const pending=page.waitForEvent('download');await buttons.nth(i).click();const d=await pending,target=path.join(evidence,`download-${width}-${i}`);await d.saveAs(target);assert.deepEqual(fs.readFileSync(target),expected.buffer);assert.equal(d.suggestedFilename(),expected.name.replaceAll("‌","_"));}record(`ui-download-bytes-${width}-${selected.length}`);};
 const upload=async f=>{await input.setInputFiles([f]);await page.getByText(`${f.name}: ثبت شد`,{exact:true}).waitFor();selected.push(f);await reopen();await verify();};
 await reopen();await verify();await upload(file('مکمل.pdf',pdf('append')));record(`append-preserves-originals-${width}`);
 await input.setInputFiles([file('موفق.pdf',pdf('good')),file('نامعتبر.pdf',Buffer.from('bad'))]);await page.getByText(/نامعتبر.pdf: ثبت نشد/).waitFor();assert.equal(await page.getByText('موفق.pdf: ثبت شد',{exact:true}).count(),1);selected.push(file('موفق.pdf',pdf('good')));await reopen();await verify();await upload(file('نامعتبر.pdf',pdf('corrected')));record(`partial-failure-retry-only-failed-${width}`);
 await page.screenshot({path:path.join(evidence,'fwd07-'+width+'.png'),fullPage:true});const layout=await page.evaluate(()=>({dir:document.documentElement.dir,scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));assert.equal(layout.dir,'rtl');assert(layout.scrollWidth<=layout.clientWidth+1);record('rtl-layout-'+width,layout);
 // Fault only the delivery of a real committed upload; upload API is not mocked.
 current='LOST_RESPONSE';let committedStatus;await page.route('**/document-requirements/*/files',async route=>{const real=await route.fetch();committedStatus=real.status();await route.abort('connectionreset');},{times:1});
 const lost=file('پاسخ-ازدست‌رفته.pdf',pdf('lost'));await input.setInputFiles([lost]);await page.getByText(/پاسخ-ازدست‌رفته.pdf: ثبت نشد/).waitFor();assert.equal(committedStatus,201);selected.push(lost);await reopen();await verify();await upload(lost);record(`lost-response-unsafe-retry-reproduced-${width}`,{serverStatus:committedStatus,duplicateSameOperation:true,attachmentsAfterRetry:selected.length});
 current='LIST_ERROR_RECOVERY';await page.route('**/documents',async route=>{await route.fetch();await route.abort('connectionreset');},{times:1});await page.goto(base+'/expert');await open();await page.getByRole('tab',{name:'مستندات پرونده',exact:true}).click();await page.getByText('Failed to fetch',{exact:true}).waitFor();record('list-error-state-'+width);await reopen();await verify();record('list-error-ui-recovery-'+width); await context.tracing.stop({path:path.join(evidence,`private-trace-${width}.zip`)});await context.close();context=null;
 }
 if(process.env.FWD07_UAT_ZERO==='1'){assert.equal(checks.filter(c=>c.name.startsWith('zero-requirement-')).length,2);assert.deepEqual(errors,[]);}
}catch(e){if(page){await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(evidence,'failure-dom.txt'),await page.locator('body').innerText());}record('failure',{lastSuccessfulStep:last,firstFailingStep:current,timeoutLayer:'action/assertion',elapsedMs:Date.now()-started,error:e.message});process.exitCode=1;
}finally{if(context){if(process.env.FWD07_UAT_ZERO!=='1')await context.tracing.stop({path:path.join(evidence,'private-failure-trace.zip')}).catch(()=>{});await context.close();}if(browser)await browser.close();fs.writeFileSync(path.join(evidence,'result.json'),JSON.stringify({missionResult:process.env.FWD07_UAT_ZERO==='1'&&checks.filter(c=>c.name.startsWith('zero-requirement-')).length===2&&errors.length===0?'ZERO_REQUIREMENT_PASS':checks.some(c=>c.duplicateSameOperation)?'BLOCKED_RECOVERY_CONTRACT':'DIAGNOSTIC',steps,checks,errors,api,elapsedMs:Date.now()-started},null,2));}
