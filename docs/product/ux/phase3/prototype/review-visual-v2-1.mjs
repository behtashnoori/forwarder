const {chromium}=await import(process.env.PHASE3_PLAYWRIGHT_MODULE||'file:///D:/1-webapp/15-forwarder-golden-20260921/node_modules/@playwright/test/index.mjs');
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const base=process.env.PHASE3_PROTOTYPE_URL||'http://127.0.0.1:4183/';
const out=path.resolve('docs/product/ux/phase3/evidence/browser-v2-1');
await mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
await page.emulateMedia({reducedMotion:'reduce'});
const errors=[],external=[],failed=[],measurements=[],checks=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))external.push(r.url());});
page.on('requestfailed',r=>failed.push(r.url()));
page.on('response',r=>{if(r.status()>=400)failed.push(r.url()+' '+r.status());});
const assert=(v,m)=>{if(!v)throw Error(m);};
async function shot(name,fullPage=true){await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));await page.screenshot({path:path.join(out,name+'.png'),fullPage});}
async function visit(role,key){await page.locator(`[data-role="${role}"]`).click();await page.locator(`[data-${role}-section="${key}"]`).first().click();}
async function measure(name){const m=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,font:getComputedStyle(document.body).fontFamily,fontLoaded:document.fonts.check('500 14px Vazirmatn'),hiddenControls:[...document.querySelectorAll('main button')].filter(x=>{const r=x.getBoundingClientRect();return r.width<=0||r.height<=0;}).length}));assert(m.scrollWidth<=m.width,name+' page overflow');assert(m.fontLoaded,name+' font not loaded');measurements.push({name,...m});}
try{
 await page.goto(base+'reference-current.html');await page.evaluate(()=>document.fonts.ready);await shot('reference-current-desktop');
 const referenceStyles=await page.evaluate(()=>{const input=getComputedStyle(document.querySelector('#reference-form input'));const button=getComputedStyle(document.querySelector('#reference-form button:not([role="switch"])'));return {inputRadius:input.borderRadius,inputHeight:input.height,inputBackground:input.backgroundColor,buttonRadius:button.borderRadius,buttonBackground:button.backgroundColor};});
 for(const [id,name] of [['reference-form','reference-current-form'],['reference-panel','reference-current-panel'],['reference-navigation','reference-current-tabs']])await page.locator('#'+id).screenshot({path:path.join(out,name+'.png')});
 await page.setViewportSize({width:390,height:844});await shot('reference-current-390');
 await page.setViewportSize({width:1440,height:1000});await page.goto(base);await page.evaluate(()=>document.fonts.ready);
 const contrast=await page.evaluate(()=>{
   const pairs=[['body','var(--ink)','var(--canvas)'],['metadata','var(--ink-muted)','var(--canvas)'],['primary','white','var(--blue)'],['current','var(--blue)','var(--blue-soft)'],['incomplete','var(--amber)','var(--amber-soft)'],['complete','var(--green)','var(--green-soft)'],['problem','var(--red)','var(--red-soft)'],['stale','var(--violet)','var(--violet-soft)']];
   const el=document.createElement('span');document.body.append(el);
   const rgb=s=>{el.style.color=s;return getComputedStyle(el).color.match(/[\d.]+/g).slice(0,3).map(Number);};
   const lum=s=>rgb(s).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((a,x,i)=>a+x*[.2126,.7152,.0722][i],0);
   const results=pairs.map(([name,fg,bg])=>{const a=lum(fg),b=lum(bg);return {name,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};});el.remove();return results;
 });assert(contrast.every(x=>x.ratio>=4.5),'text contrast palette');checks.push({name:'text palette contrast >= 4.5 (scoped, not full WCAG certification)',result:'PASS',contrast});
 const journeys={expert:['overview','relations','cargo','route','transport','allocation','documents','timeline','issues','deliveries','closure'],customer:['summary','timeline','cargo','documents','delivery'],admin:['catalog','route-times','closure-rules','closure-exceptions']};
 for(const [role,sections] of Object.entries(journeys))for(const key of sections){await visit(role,key);await measure(role+'/'+key);await shot(role+'-'+key);}
 await visit('expert','allocation');await page.locator('[data-dialog="allocation"]').click();await shot('aligned-allocation-form',false);
 const alignedStyles=await page.evaluate(()=>{const input=getComputedStyle(document.querySelector('#allocation-quantity'));const button=getComputedStyle(document.querySelector('.dialog .button.primary'));return {inputRadius:input.borderRadius,inputHeight:input.height,inputBackground:input.backgroundColor,buttonRadius:button.borderRadius,buttonBackground:button.backgroundColor};});
 assert(referenceStyles.inputRadius===alignedStyles.inputRadius&&referenceStyles.inputBackground===alignedStyles.inputBackground&&referenceStyles.buttonRadius===alignedStyles.buttonRadius&&referenceStyles.buttonBackground===alignedStyles.buttonBackground,'canonical control styles differ');checks.push({name:'source-rendered canonical input/button style alignment',result:'PASS',referenceStyles,alignedStyles});
 await page.locator('#allocation-quantity').focus();const focus=await page.locator('#allocation-quantity').evaluate(x=>({outline:getComputedStyle(x).outlineWidth,height:x.getBoundingClientRect().height,radius:getComputedStyle(x).borderRadius}));assert(parseFloat(focus.outline)>=2,'visible input focus');await shot('aligned-form-focus',false);
 await page.keyboard.press('Tab');for(let i=0;i<10;i++){await page.keyboard.press('Tab');assert(await page.evaluate(()=>!!document.activeElement.closest('[role="dialog"]')),'focus escaped dialog');}
 await page.keyboard.press('Escape');assert(await page.locator('.dialog-layer').isHidden(),'dialog escape');checks.push({name:'keyboard dialog focus cycle, visible ring, Escape',result:'PASS',focus});
 await visit('expert','route');await page.locator('[data-route-view="actual"]').click();await shot('expert-route-actual');
 await visit('expert','timeline');await page.locator('summary').first().click();await shot('expert-timeline-correction-history');
 await visit('expert','allocation');await page.locator('[data-allocation-view="unit"]').click();await shot('expert-allocation-unit');
 await page.setViewportSize({width:390,height:844});
 for(const key of journeys.customer){await visit('customer',key);await measure('customer/'+key+'/390');await shot('customer-'+key+'-390');await shot('customer-'+key+'-390-viewport',false);const targets=await page.locator('.customer-nav button').evaluateAll(xs=>xs.map(x=>({text:x.textContent,w:x.getBoundingClientRect().width,h:x.getBoundingClientRect().height})));assert(targets.every(x=>x.w>=44&&x.h>=44),'mobile nav touch targets');await page.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));const bottom=await page.locator('main').evaluate(x=>x.getBoundingClientRect().bottom);const navTop=await page.locator('.customer-nav').evaluate(x=>x.getBoundingClientRect().top);assert(bottom<=navTop,'end content blocked by bottom nav');measurements.push({name:'customer/'+key+'/390-bottom',bottom,navTop,targets});}
 await visit('customer','summary');const eta=await page.getByText('۲۳ تا ۲۸ روز',{exact:true}).boundingBox();assert(eta&&eta.y+eta.height<770,'ETA below initial mobile navigation');checks.push({name:'mobile initial ETA visible',result:'PASS',eta});
 await page.setViewportSize({width:1440,height:1000});await visit('admin','catalog');await page.locator('[data-action="open-scenarios"]').click();await shot('state-switcher',false);await page.keyboard.press('Escape');
 for(const role of ['expert','customer','admin'])for(const state of ['loading','empty','error','denied','stale','degraded']){await page.locator(`[data-role="${role}"]`).click();await page.locator('[data-action="open-scenarios"]').click();await page.locator(`[data-scenario="${state}"]`).click();await shot('state-'+role+'-'+state);await page.locator('[data-action="reset-scenario"]').click();}
 assert(!errors.length,'console: '+errors.join(';'));assert(!failed.length,'resources: '+failed.join(';'));assert(!external.length,'external: '+external.join(';'));
 checks.push({name:'Chrome visual evidence complete; no errors, failures or external requests',result:'PASS'});
}finally{
 const files=['app.js','index.html','styles.css','visual-v2-1.css','assets/Vazirmatn.ttf','review-visual-v2-1.mjs','reference-current.html','reference-current.css'];const hashes={};for(const f of files)hashes[f]=createHash('sha256').update(await readFile(new URL(f,import.meta.url))).digest('hex');
 await writeFile(path.join(out,'visual-review.json'),JSON.stringify({testedAt:new Date().toISOString(),sourceHead:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),browser:await browser.version(),url:base,hashes,measurements,checks,errors,failed,external,result:checks.at(-1)?.name.startsWith('Chrome visual')?'PASS':'FAIL'},null,2)+'\n');await browser.close();
}
