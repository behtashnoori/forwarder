// Actual installed Chromium, private input pipe, no capability-bearing logs.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('C:\\Users\\pc\\AppData\\Local\\npm-cache\\_npx\\e41f203b7505f1fb\\node_modules\\playwright-core');
const browsers = 'C:\\Users\\pc\\AppData\\Local\\ms-playwright';
const executablePath = fs.readdirSync(browsers).filter(x => /^chromium-\d+$/.test(x))
  .sort((a,b) => Number(b.split('-')[1])-Number(a.split('-')[1]))
  .map(x => path.join(browsers,x,'chrome-win64','chrome.exe')).find(x => fs.existsSync(x));
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const target = new URL(input.link);
if (target.protocol !== 'http:' || target.hostname !== '127.0.0.1' || !['UTC','America/New_York'].includes(input.timezone)) process.exit(2);
let browser;
const checks = [];
const check = (name, value) => { if (!value) throw new Error('CHECK_FAILED'); checks.push(name); };
try {
  browser = await chromium.launch({ executablePath, headless: true });
  const context = await browser.newContext({ timezoneId: input.timezone, viewport: {width:390,height:844}, locale:'fa-IR' });
  const page = await context.newPage();
  let posts = 0, unsafeRequests = 0, unsafeConsole = 0;
  page.on('request', r => {
    if (r.method() === 'POST') posts++;
    if (r.url().includes(target.hash.slice(1)) || (r.headers()['referer'] || '').includes('#')) unsafeRequests++;
    if (!r.url().startsWith(target.origin)) unsafeRequests++;
  });
  page.on('console', message => { if (message.text().includes(target.hash.slice(1))) unsafeConsole++; });
  const shell = await page.goto(input.link, {waitUntil:'networkidle'});
  check('strict-shell-CSP-cache-referrer', shell.headers()['cache-control'] === 'no-store'
    && shell.headers()['referrer-policy'] === 'no-referrer'
    && !shell.headers()['content-security-policy'].includes('unsafe-'));
  await page.getByRole('button', {name:'درخواست مذاکره',exact:true}).waitFor();
  check('fragment-cleared-before-interaction', page.url() === target.origin + target.pathname);
  check('GET-open-does-not-write', posts === 0);
  check('exact-EUR-display', (await page.locator('.amount').innerText()).includes('1,234.50 EUR'));
  check('actual-browser-timezone', await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone) === input.timezone);
  await page.getByRole('button', {name:'درخواست مذاکره',exact:true}).click();
  await page.locator('.receipt').first().waitFor();
  await page.getByRole('button', {name:'پذیرش پیشنهاد',exact:true}).click();
  await page.waitForFunction(() => document.querySelectorAll('.receipt').length === 2);
  check('two-real-response-receipts', await page.locator('.receipt').count() === 2);
  check('terminal-no-fresh-controls', await page.locator('.choices button').count() === 0);
  await page.goto(input.link, {waitUntil:'networkidle'});
  await page.locator('.receipt').first().waitFor();
  check('reopen-own-receipts', await page.locator('.receipt').count() === 2);
  check('reopen-does-not-post', posts === 2);
  const storage = await page.evaluate(() => ({ local:localStorage.length, session:sessionStorage.length, cookies:document.cookie,
    rtl:document.documentElement.dir, overflow:document.documentElement.scrollWidth > innerWidth }));
  check('no-browser-persistence', storage.local === 0 && storage.session === 0 && storage.cookies === '');
  check('mobile-RTL-without-overflow', storage.rtl === 'rtl' && !storage.overflow);
  check('no-token-URL-referrer-console-third-party', unsafeRequests === 0 && unsafeConsole === 0);
  if (input.screenshot) await page.screenshot({path:input.screenshot,fullPage:true});
  await page.setViewportSize({width:1440,height:900});
  check('desktop-without-overflow', !await page.evaluate(() => document.documentElement.scrollWidth > innerWidth));
  console.log(JSON.stringify({status:'PASS',timezone:input.timezone,checks}));
} catch {
  console.log(JSON.stringify({status:'FAIL',timezone:input.timezone,checks,reason:'BROWSER_CHECK_OR_RUNTIME_FAILED'}));
  process.exitCode = 1;
} finally { if (browser) await browser.close(); }
