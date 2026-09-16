// Synthetic qualification: real UI/auth/backend, private parent-to-browser pipe.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('C:\\Users\\pc\\AppData\\Local\\npm-cache\\_npx\\e41f203b7505f1fb\\node_modules\\playwright-core');
const lines = readline.createInterface({ input: process.stdin })[Symbol.asyncIterator]();
const receive = async () => JSON.parse((await lines.next()).value);
const input = await receive();
const origin = new URL(input.origin);
if (origin.protocol !== 'http:' || origin.hostname !== '127.0.0.1' || !['UTC','America/New_York'].includes(input.timezone)) process.exit(2);
const executablePath = fs.readdirSync('C:\\Users\\pc\\AppData\\Local\\ms-playwright').filter(x=>/^chromium-\d+$/.test(x))
  .sort((a,b)=>Number(b.split('-')[1])-Number(a.split('-')[1]))
  .map(x=>path.join('C:\\Users\\pc\\AppData\\Local\\ms-playwright',x,'chrome-win64','chrome.exe')).find(x=>fs.existsSync(x));
const checks = [], capabilities = [];
const check = (name, value) => { if (!value) throw new Error('CHECK_FAILED'); checks.push(name); };
const dispatch = async () => {
  console.log(JSON.stringify({command:'DISPATCH_PRIVATE'}));
  const result = await receive();
  const target = new URL(result.link);
  check('private-fake-link-bounded-origin', target.origin === origin.origin && target.pathname === '/quote-response.html');
  capabilities.push(target.hash.slice(1));
  return result.link;
};
let browser, stage='launch';
try {
  browser = await chromium.launch({executablePath,headless:true});
  const staff = await browser.newContext({timezoneId:input.timezone,locale:'fa-IR',viewport:{width:1440,height:900}});
  const expert = await browser.newContext({timezoneId:input.timezone,locale:'fa-IR',viewport:{width:1440,height:900}});
  const customer = await browser.newContext({timezoneId:input.timezone,locale:'fa-IR',viewport:{width:390,height:844}});
  const adminPage = await staff.newPage(), expertPage = await expert.newPage(), customerPage = await customer.newPage();
  let unsafe = 0;
  customerPage.on('request', r=>{
    if (!r.url().startsWith(origin.origin) || capabilities.some(token=>r.url().includes(token) || (r.headers().referer||'').includes(token))) unsafe++;
  });
  for (const page of [adminPage,expertPage,customerPage]) page.on('console',m=>{if(capabilities.some(token=>m.text().includes(token))) unsafe++;});
  const login = async (page, identity) => {
    stage='login-home';
    await page.goto(origin.origin, {waitUntil:'networkidle'});
    stage='login-open-dialog';
    if (!await page.getByRole('button',{name:'ورود به سامانه',exact:true}).count()) {
      if(input.screenshot)await page.screenshot({path:input.screenshot,fullPage:true});
      stage='login-no-rendered-staff-button';
      throw new Error('CHECK_FAILED');
    }
    await page.getByRole('button',{name:'ورود به سامانه',exact:true}).filter({visible:true}).first().click();
    await page.locator('#username').fill(identity.username);
    await page.locator('#password').fill(identity.password);
    stage='login-submit';
    await page.getByRole('dialog').getByRole('button',{name:'ورود',exact:true}).click();
    await page.waitForFunction(()=>Boolean(localStorage.getItem('expert_token')));
  };
  await login(adminPage,input.admin);
  stage='admin-open';
  await adminPage.goto(origin.origin+'/admin',{waitUntil:'networkidle'});
  stage='admin-quotation-tab';
  await adminPage.getByRole('tab',{name:'اعتبار پیشنهادها',exact:true}).click();
  stage='admin-zone-fill';
  await adminPage.locator('#quotation-zone').fill('Europe/Paris');
  stage='admin-zone-save';
  const savedResponse=adminPage.waitForResponse(r=>r.url().endsWith('/quotation-settings') && r.request().method()==='PATCH');
  await adminPage.getByRole('button',{name:'ثبت منطقه زمانی',exact:true}).click();
  const saved=await savedResponse;
  stage='admin-zone-http-'+saved.status();
  check('admin-zone-save-HTTP-success',saved.status()===200);
  stage='admin-zone-confirm';
  await adminPage.getByRole('status').filter({hasText:'تنظیمات ثبت شد.'}).first().waitFor();
  stage='admin-zone-UI-value-check';
  check('real-admin-IANA-setting-UI',await adminPage.locator('#quotation-zone').inputValue()==='Europe/Paris');
  await login(expertPage,input.expert);
  await expertPage.goto(origin.origin+'/expert/requests/'+input.root,{waitUntil:'networkidle'});
  await expertPage.getByRole('button',{name:'انتشار پیشنهاد جایگزین',exact:true}).click();
  await expertPage.locator('#quote-currency').selectOption('EUR');
  await expertPage.locator('#quote-amount').fill('4321.50');
  await expertPage.locator('#quote-valid').fill(input.validUntil);
  await expertPage.locator('#quote-note').fill('<img src="https://example.invalid/leak" onerror="window.quoteXss=true">');
  const publication = expertPage.waitForResponse(r=>r.url().endsWith('/quote') && r.request().method()==='POST');
  await expertPage.getByRole('dialog').getByRole('button',{name:'ارسال پیشنهاد',exact:true}).click();
  const response = await publication, published = await response.json();
  check('real-expert-exact-money-publication-UI', response.status()===200 && published.quote.amount_exact==='4321.50' && published.quote.validity_timezone==='Europe/Paris');
  check('staff-publication-has-no-customer-token', !JSON.stringify(published).includes('#') && !('token' in published));
  let link = await dispatch();
  await customerPage.goto(link,{waitUntil:'networkidle'});
  await customerPage.getByRole('button',{name:'درخواست مذاکره',exact:true}).waitFor();
  check('new-customer-content-from-real-publication',(await customerPage.locator('.amount').innerText()).includes('4,321.50 EUR'));
  check('published-note-is-escaped-text', (await customerPage.locator('.note').innerText()).includes('<img') && !await customerPage.evaluate(()=>Boolean(window.quoteXss)));
  await customerPage.getByRole('button',{name:'درخواست مذاکره',exact:true}).click();
  await customerPage.locator('.receipt').waitFor();
  await expertPage.reload({waitUntil:'networkidle'});
  check('staff-recipient-ready-does-not-claim-real-delivery',(await expertPage.getByLabel('آمادگی گیرنده').innerText()).includes('تحویل واقعی تأیید نشده است'));
  check('expert-read-projects-real-negotiation',(await expertPage.locator('body').innerText()).includes('درخواست مذاکره'));
  const managed = await expertPage.evaluate(async ({root,quote})=>{
    const result=await fetch('/api/expert/requests/'+root+'/quotes/'+quote+'/capability',{
      method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+localStorage.getItem('expert_token')},body:JSON.stringify({operation:'REISSUE'})});
    return {status:result.status,body:await result.json()};
  },{root:input.root,quote:published.quote.public_id});
  check('real-staff-reissue-metadata-only',managed.status===200 && !JSON.stringify(managed.body).includes('#') && !('token' in managed.body));
  const oldLink=link;
  link=await dispatch();
  stage='old-reissued-link-open';
  await customerPage.goto(oldLink,{waitUntil:'networkidle'});
  await customerPage.waitForFunction(()=>!document.querySelector('.choices button'));
  check('reopened-private-fragment-cleared',!customerPage.url().includes('#'));
  check('old-link-no-fresh-decision-controls',await customerPage.locator('.choices button').count()===0);
  stage='new-reissued-link-open';
  await customerPage.goto(link,{waitUntil:'networkidle'});
  stage='reissued-accept-control';
  await customerPage.getByRole('button',{name:'پذیرش پیشنهاد',exact:true}).waitFor();
  await customerPage.getByRole('button',{name:'پذیرش پیشنهاد',exact:true}).click();
  stage='reissued-two-receipts';
  await customerPage.waitForFunction(()=>document.querySelectorAll('.receipt').length===2);
  check('reissued-customer-own-receipts-final',await customerPage.locator('.choices button').count()===0);
  await expertPage.reload({waitUntil:'networkidle'});
  check('accepted-publication-cannot-replace-in-expert-UI',await expertPage.getByRole('button',{name:'انتشار پیشنهاد جایگزین',exact:true}).isDisabled());
  const inbox=await expertPage.evaluate(async()=>{
    const result=await fetch('/api/expert/notifications',{headers:{Authorization:'Bearer '+localStorage.getItem('expert_token')}});
    return {status:result.status,body:await result.json()};
  });
  check('live-expert-inbox-has-two-actual-response-facts',inbox.status===200 && inbox.body.notifications.filter(entry=>entry.type==='customer_quote_response' && entry.fact_id).length===2);
  const isolated=await customerPage.evaluate(()=>({local:localStorage.length,session:sessionStorage.length,cookies:document.cookie,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone}));
  check('customer-context-isolated-from-staff',isolated.local===0 && isolated.session===0 && isolated.cookies==='' && isolated.timezone===input.timezone);
  check('customer-private-link-cleared-and-no-leakage',!customerPage.url().includes('#') && unsafe===0);
  await customerPage.goto(origin.origin+'/customer/track/'+input.tracking,{waitUntil:'networkidle'});
  await customerPage.getByText('پیشنهاد پذیرفته شد',{exact:false}).first().waitFor();
  const trackingText=(await customerPage.locator('body').innerText()).replace(/[۰-۹]/g,value=>String('۰۱۲۳۴۵۶۷۸۹'.indexOf(value)))
    .replace(/٬/g,',').replace(/٫/g,'.');
  check('legacy-tracking-remains-exact-read-only',await customerPage.getByRole('button',{name:'پذیرش پیشنهاد',exact:true}).count()===0
    && await customerPage.getByRole('button',{name:'رد پیشنهاد',exact:true}).count()===0
    && trackingText.includes('4,321.50'));
  console.log(JSON.stringify({command:'INVALIDATE_SYNTHETIC_RECIPIENT'}));
  const invalidated=await receive();
  check('synthetic-recipient-invalidation-ack',invalidated.status==='ACK');
  await expertPage.reload({waitUntil:'networkidle'});
  const readiness=await expertPage.getByLabel('آمادگی گیرنده').innerText();
  check('staff-not-ready-recipient-and-open-follow-up',readiness.includes('پیوند خصوصی آماده نیست') && readiness.includes('مسئول پیگیری') && readiness.includes('باز است'));
  console.log(JSON.stringify({status:'PASS',timezone:input.timezone,checks}));
} catch {
  console.log(JSON.stringify({status:'FAIL',timezone:input.timezone,checks,stage,reason:'BROWSER_CHECK_OR_RUNTIME_FAILED'}));
  process.exitCode=1;
} finally {if(browser)await browser.close();process.stdin.destroy();}
