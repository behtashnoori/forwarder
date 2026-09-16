// Local synthetic UAT. Tokens/passwords stay in process memory and never enter evidence.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('C:\\Users\\pc\\AppData\\Local\\npm-cache\\_npx\\e41f203b7505f1fb\\node_modules\\playwright-core');
const browserRoot = 'C:\\Users\\pc\\AppData\\Local\\ms-playwright';
const executablePath = fs.readdirSync(browserRoot).filter(x => /^chromium-\d+$/.test(x)).sort((a,b) => Number(b.split('-')[1])-Number(a.split('-')[1]))
  .map(x => path.join(browserRoot,x,'chrome-win64','chrome.exe')).find(x => fs.existsSync(x));
const base = process.env.FWD06_UAT_BASE_URL;
const api = process.env.FWD06_UAT_API_URL;
const password = process.env.FWD04_UAT_PASSWORD;
const evidence = process.env.FWD06_UAT_EVIDENCE_DIR;
for (const value of [base,api]) { const parsed = new URL(value); if (parsed.protocol !== 'http:' || parsed.hostname !== '127.0.0.1') throw Error('loopback only'); }
if (!password || !evidence || !executablePath) throw Error('missing synthetic UAT dependency');
fs.mkdirSync(evidence,{recursive:true});
const checks=[];
function check(name, condition, detail='') { checks.push({name,status:condition?'PASS':'FAIL',detail}); if (!condition) throw Error(`${name}: ${detail}`); }
async function call(route, token, method='GET', body) {
  const response=await fetch(api+route,{method,headers:{'content-type':'application/json',...(token?{authorization:`Bearer ${token}`}:{})},body:body?JSON.stringify(body):undefined});
  return {status:response.status,body:await response.json().catch(()=>({}))};
}
const admin=await call('/api/expert/auth/login',null,'POST',{username:'fwd04-assigner',password});
const expert=await call('/api/expert/auth/login',null,'POST',{username:'fwd04-expert',password});
check('real-login',admin.status===200&&expert.status===200);
const adminToken=admin.body.tokens.access_token, expertToken=expert.body.tokens.access_token;
const publicRoot=await call('/api/public/track/SR-FWD04-ASSIGNED');
check('synthetic-request',publicRoot.status===200&&Number.isInteger(publicRoot.body.id));
const requestId=publicRoot.body.id;
const experts=await call('/api/expert/experts',adminToken);
const rows=Array.isArray(experts.body)?experts.body:experts.body.experts;
const expertId=rows.find(row=>row.username==='fwd04-expert')?.id;
check('expert-selector',Number.isInteger(expertId));
const assignment=await call(`/api/expert/requests/${requestId}/assign`,adminToken,'POST',{expert_id:expertId});
check('real-assignment',assignment.status===200);
const transition=await call(`/api/expert/requests/${requestId}/status`,expertToken,'POST',{status:'won',note:'Synthetic local FWD-06 UAT transition'});
check('real-eligible-transition',transition.status===200&&transition.body.status==='won');

const browser=await chromium.launch({executablePath,headless:true});
try {
  let unitId;
  for (const timezoneId of ['UTC','America/New_York']) {
    const context=await browser.newContext({timezoneId,locale:'fa-IR',viewport:{width:1440,height:900}});
    await context.addInitScript(session=>{localStorage.setItem('expert_token',session.token);localStorage.setItem('expert_user',JSON.stringify(session.user));}, {token:expertToken,user:expert.body.expert});
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror', error=>errors.push(error.message));
    await page.goto(`${base}/expert/requests/${requestId}`,{waitUntil:'networkidle'});
    await page.getByRole('tab',{name:'مدیریت رهگیری محموله'}).click();
    check(`browser-zone-${timezoneId}`,await page.evaluate(()=>Intl.DateTimeFormat().resolvedOptions().timeZone)===timezoneId);
    if (timezoneId==='UTC') {
      await page.getByRole('button',{name:'فعال‌سازی رهگیری مشتری'}).click();
      await page.getByPlaceholder('کد بخش').fill('M1-BROWSER-TRUCK');
      await page.getByRole('button',{name:'افزودن بخش قابل رهگیری'}).click();
      await page.getByText('M1-BROWSER-TRUCK').first().waitFor();
      const management=await call(`/api/expert/requests/${requestId}/tracking`,expertToken);
      unitId=management.body.unit_tracking.units[0].id;
      check('browser-subject-created',management.status===200&&management.body.unit_tracking.units.length===1);
      await page.getByPlaceholder('کد بخش').fill('M1-BROWSER-TRUCK');
      await page.getByRole('button',{name:'افزودن بخش قابل رهگیری'}).click();
      await page.getByText('این کد بخش قبلاً در همین رهگیری ثبت شده است. کد دیگری وارد کنید.').waitFor();
      check('duplicate-input-retained',await page.getByPlaceholder('کد بخش').inputValue()==='M1-BROWSER-TRUCK');
    }
    const updateCard=page.locator('div.rounded-3xl').filter({has:page.getByRole('heading',{name:'ثبت به‌روزرسانی'})}).first();
    await updateCard.getByRole('combobox').first().click();
    await page.getByRole('option',{name:'M1-BROWSER-TRUCK'}).click();
    await page.getByRole('combobox',{name:'شیوه ورود تاریخ'}).click();
    await page.getByRole('option',{name:'میلادی'}).click();
    await page.getByLabel('تاریخ میلادی وقوع').fill('2026-07-15');
    await page.getByLabel('ساعت وقوع به وقت تهران').fill('12:00');
    await page.getByRole('combobox',{name:'شیوه ورود تاریخ'}).click();
    await page.getByRole('option',{name:'شمسی'}).click();
    await page.locator('#tracking-occurrence-date').click();
    await page.getByRole('button',{name:'24',exact:true}).click();
    await page.getByRole('combobox',{name:'شیوه ورود تاریخ'}).click();
    await page.getByRole('option',{name:'میلادی'}).click();
    check(`calendar-switch-${timezoneId}`,await page.getByLabel('تاریخ میلادی وقوع').inputValue()==='2026-07-15');
    await updateCard.getByRole('button',{name:'ثبت به‌روزرسانی'}).click();
    let timeline=[];
    for (let attempt=0;attempt<20;attempt++) {
      const management=await call(`/api/expert/requests/${requestId}/tracking`,expertToken);
      timeline=management.body.unit_tracking.units[0].timeline;
      if (timeline.length===(timezoneId==='UTC'?1:2)) break;
      await page.waitForTimeout(250);
    }
    check(`browser-tehran-instant-${timezoneId}`,timeline.length===(timezoneId==='UTC'?1:2)&&timeline.every(row=>row.event_at==='2026-07-15T08:30:00Z'),JSON.stringify(timeline.map(row=>row.event_at)));
    await page.reload({waitUntil:'networkidle'});
    await page.getByRole('tab',{name:'مدیریت رهگیری محموله'}).click();
    await page.getByText('M1-BROWSER-TRUCK').first().waitFor();
    check(`reopen-timeline-${timezoneId}`,(await page.locator('body').innerText()).includes('M1-BROWSER-TRUCK'));
    check(`browser-errors-${timezoneId}`,errors.length===0,errors.join(' | '));
    await page.screenshot({path:path.join(evidence,`fwd06-expert-${timezoneId.replace('/','-')}.png`),fullPage:true});
    await context.close();
  }
  const customer=await browser.newContext({timezoneId:'America/New_York',locale:'fa-IR',viewport:{width:390,height:844}});
  const page=await customer.newPage();
  await page.goto(`${base}/customer/track/SR-FWD04-ASSIGNED`,{waitUntil:'networkidle'});
  const body=await page.locator('body').innerText();
  check('mobile-customer-visible',body.includes('M1-BROWSER-TRUCK')&&body.includes('ثبت:'));
  check('no-private-note',!body.includes('Synthetic local FWD-06 UAT transition'));
  await page.screenshot({path:path.join(evidence,'fwd06-customer-mobile.png'),fullPage:true});
  await customer.close();
  const mobileExpert=await browser.newContext({timezoneId:'UTC',locale:'fa-IR',viewport:{width:390,height:844}});
  await mobileExpert.addInitScript(session=>{localStorage.setItem('expert_token',session.token);localStorage.setItem('expert_user',JSON.stringify(session.user));},{token:expertToken,user:expert.body.expert});
  const expertPage=await mobileExpert.newPage();
  await expertPage.goto(`${base}/expert/requests/${requestId}`,{waitUntil:'networkidle'});
  await expertPage.getByRole('tab',{name:'مدیریت رهگیری محموله'}).click();
  await expertPage.getByText('M1-BROWSER-TRUCK').first().waitFor();
  check('mobile-expert-timeline',(await expertPage.locator('body').innerText()).includes('M1-BROWSER-TRUCK'));
  await expertPage.screenshot({path:path.join(evidence,'fwd06-expert-mobile.png'),fullPage:true});
  await mobileExpert.close();
  const desktopCustomer=await browser.newContext({timezoneId:'UTC',locale:'fa-IR',viewport:{width:1440,height:900}});
  const customerPage=await desktopCustomer.newPage();
  await customerPage.goto(`${base}/customer/track/SR-FWD04-ASSIGNED`,{waitUntil:'networkidle'});
  check('desktop-customer-timeline',(await customerPage.locator('body').innerText()).includes('M1-BROWSER-TRUCK'));
  await customerPage.screenshot({path:path.join(evidence,'fwd06-customer-desktop.png'),fullPage:true});
  await desktopCustomer.close();
  const result={candidate:process.env.FWD06_UAT_CANDIDATE,checks,unit_id:unitId,expected_instant:'2026-07-15T08:30:00Z'};
  fs.writeFileSync(path.join(evidence,'fwd06-browser-result.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({checks:checks.length,result:'PASS',evidence}));
} finally {await browser.close();}
