import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const PLAYWRIGHT_ROOT = "C:\\Users\\pc\\AppData\\Local\\npm-cache\\_npx\\e41f203b7505f1fb\\node_modules\\playwright-core";
const PLAYWRIGHT_BROWSERS = "C:\\Users\\pc\\AppData\\Local\\ms-playwright";
const CHROMIUM = process.env.FWD04_UAT_CHROMIUM || fs.readdirSync(PLAYWRIGHT_BROWSERS, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && /^chromium-\d+$/.test(entry.name))
  .sort((left, right) => Number(right.name.split("-")[1]) - Number(left.name.split("-")[1]))
  .map((entry) => path.join(PLAYWRIGHT_BROWSERS, entry.name, "chrome-win64", "chrome.exe"))
  .find((candidate) => fs.existsSync(candidate));
const { chromium } = require(PLAYWRIGHT_ROOT);
const required = (name) => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing ${name}`);
  return value;
};
const loopback = (raw, name) => {
  const url = new URL(raw);
  if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname)) throw new Error(`${name} must be loopback HTTP`);
  return url.origin;
};
const base = loopback(required("FWD04_UAT_BASE_URL"), "FWD04_UAT_BASE_URL");
const api = loopback(required("FWD04_UAT_API_URL"), "FWD04_UAT_API_URL");
const password = required("FWD04_UAT_PASSWORD");
const evidence = path.resolve(required("FWD04_UAT_EVIDENCE_DIR"));
if (!fs.existsSync(PLAYWRIGHT_ROOT) || !CHROMIUM || !fs.existsSync(CHROMIUM)) throw new Error("Existing Playwright/Chromium dependency missing");
fs.mkdirSync(evidence, { recursive: true });

const checks = [];
const check = (name, ok, detail = "") => { checks.push({ name, status: ok ? "PASS" : "FAIL", detail }); if (!ok) throw new Error(`${name}: ${detail}`); };
const request = async (route, options = {}) => {
  const response = await fetch(`${api}${route}`, options);
  return { status: response.status, body: await response.json().catch(() => ({})) };
};
const login = async (username) => {
  const response = await request("/api/expert/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ username, password }) });
  check(`login-${username}`, response.status === 200 && !!response.body?.tokens?.access_token, `status=${response.status}`);
  return response.body;
};
const authorized = (token, route, options = {}) => request(route, { ...options, headers: { "content-type": "application/json", authorization: `Bearer ${token}`, ...(options.headers || {}) } });
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const displayOracle = (instant) => new Intl.DateTimeFormat("en-GB-u-ca-gregory", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tehran" }).format(new Date(instant));
let browser;
try {
  const admin = await login("fwd04-assigner");
  const expert = await login("fwd04-expert");
  const experts = await authorized(admin.tokens.access_token, "/api/expert/experts");
  const expertRows = Array.isArray(experts.body) ? experts.body : experts.body.experts;
  const expertId = expertRows?.find((item) => item.username === "fwd04-expert")?.id;
  check("tenant-expert-selector", Number.isInteger(expertId), `expert_id=${expertId}`);
  const preAssigned = await request("/api/public/track/SR-FWD04-ASSIGNED");
  check("fixture-assignment-target", preAssigned.status === 200 && Number.isInteger(preAssigned.body.id), `status=${preAssigned.status}`);

  // The delay makes the independently-created request and the API-created fact
  // observably distinct without overwriting either business timestamp.
  await sleep(1100);
  const assignment = await authorized(admin.tokens.access_token, `/api/expert/requests/${preAssigned.body.id}/assign`, { method: "POST", body: JSON.stringify({ expert_id: expertId }) });
  check("real-admin-assignment-api", assignment.status === 200 && assignment.body?.assigned_to?.id === expertId, `status=${assignment.status}`);
  const assigned = await request("/api/public/track/SR-FWD04-ASSIGNED");
  const noFact = await request("/api/public/track/SR-FWD04-NOFACT");
  check("public-assignment-fact", assigned.status === 200 && !!assigned.body.assigned_at, JSON.stringify(assigned.body));
  check("assignment-after-request-create", new Date(assigned.body.assigned_at) > new Date(assigned.body.created_at), `${assigned.body.created_at} -> ${assigned.body.assigned_at}`);
  check("public-no-fabricated-assignment", noFact.status === 200 && noFact.body.assigned_at === null, JSON.stringify(noFact.body));

  browser = await chromium.launch({ executablePath: CHROMIUM, headless: true });
  const timezoneRuns = [];
  for (const timezoneId of ["UTC", "America/New_York"]) {
    const context = await browser.newContext({ timezoneId, viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    const consoleErrors = [];
    page.on("console", (message) => { if (message.type() === "error" && !/favicon|React Router Future Flag/i.test(message.text())) consoleErrors.push(message.text()); });
    await page.goto(`${base}/customer/track/SR-FWD04-ASSIGNED`, { waitUntil: "networkidle" });
    const observedTimezone = await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone);
    const body = await page.locator("body").innerText();
    // This is a browser-native Intl oracle, not the product formatter under test.
    const expectedGregorian = await page.evaluate((instant) => new Intl.DateTimeFormat("en-GB-u-ca-gregory", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tehran" }).format(new Date(instant)), assigned.body.assigned_at);
    check(`browser-timezone-${timezoneId}`, observedTimezone === timezoneId, `observed=${observedTimezone}`);
    check(`assignment-visible-${timezoneId}`, body.includes("Asia/Tehran") && body.includes(expectedGregorian), `expected Gregorian=${expectedGregorian}; body=${body.slice(0, 1000)}`);
    const createdGregorian = await page.evaluate((instant) => new Intl.DateTimeFormat("en-GB-u-ca-gregory", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tehran" }).format(new Date(instant)), assigned.body.created_at);
    check(`assigned-not-created-${timezoneId}`, !body.includes(createdGregorian) || createdGregorian === expectedGregorian, "assignment card uses assignment fact");
    await page.goto(`${base}/customer/track/SR-FWD04-NOFACT`, { waitUntil: "networkidle" });
    const noFactBody = await page.locator("body").innerText();
    check(`no-fabrication-ui-${timezoneId}`, noFactBody.includes("تاریخ اختصاص کارشناس") && !noFactBody.includes("Asia/Tehran"), "missing fact remains unresolved");
    timezoneRuns.push({ timezoneId, observedTimezone, assignmentDisplay: expectedGregorian, noFactUnresolved: true });
    check(`console-${timezoneId}`, consoleErrors.length === 0, `count=${consoleErrors.length}`);
    await context.close();
  }

  // The role journey uses the normal rendered login and navigation, not a
  // storage-state fixture or route interception.
  const expertContext = await browser.newContext({ timezoneId: "UTC", viewport: { width: 1280, height: 800 } });
  const expertPage = await expertContext.newPage();
  await expertPage.goto(base, { waitUntil: "networkidle" });
  await expertPage.getByRole("button", { name: "ورود به سامانه" }).click();
  await expertPage.getByLabel("نام کاربری").fill("fwd04-expert");
  await expertPage.getByLabel("رمز عبور").fill(password);
  await expertPage.getByRole("button", { name: "ورود", exact: true }).click();
  await expertPage.waitForURL(`${base}/expert`);
  await expertPage.getByRole("tab", { name: "همه" }).click();
  await expertPage.getByText("SR-FWD04-ASSIGNED", { exact: true }).waitFor();
  await expertPage.getByRole("button", { name: "مشاهده جزئیات" }).click();
  await expertPage.getByRole("heading", { name: "پیشنهاد قیمت" }).waitFor();
  check("expert-assigned-natural-navigation", expertPage.url().includes("/expert/requests/"));
  await expertPage.getByRole("button", { name: "ثبت قیمت" }).click();
  await expertPage.locator("#quote-amount").fill("۱۲٬۳۴۵");
  await expertPage.locator("#quote-valid").fill("2030-01-15");
  await expertPage.getByRole("button", { name: "ارسال پیشنهاد" }).click();
  await expertPage.getByText("۱۲٬۳۴۵ IRR", { exact: false }).waitFor();
  check("expert-local-date-save-reopen", await expertPage.locator("body").innerText().then((text) => text.includes("۲۶ دی ۱۴۰۸")));
  await expertContext.close();

  for (const timezoneId of ["UTC", "America/New_York"]) {
    const context = await browser.newContext({ timezoneId, viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await page.goto(`${base}/customer/track/SR-FWD04-ASSIGNED`, { waitUntil: "networkidle" });
    const observedTimezone = await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone);
    const expectedLocalDate = await page.evaluate(() => new Intl.DateTimeFormat("fa-IR-u-ca-persian", { dateStyle: "medium", timeZone: "UTC" }).format(new Date("2030-01-15T00:00:00Z")));
    const body = await page.locator("body").innerText();
    check(`local-date-${timezoneId}`, observedTimezone === timezoneId && body.includes(expectedLocalDate) && body.includes("۱۲٬۳۴۵ IRR"), `expected=${expectedLocalDate}`);
    await context.close();
  }

  for (const [width, height] of [[1280, 800], [390, 844]]) {
    const context = await browser.newContext({ timezoneId: "UTC", viewport: { width, height }, deviceScaleFactor: 1, hasTouch: width < 600 });
    const page = await context.newPage();
    await page.goto(`${base}/customer/track/SR-FWD04-ASSIGNED`, { waitUntil: "networkidle" });
    const geometry = await page.evaluate(() => ({ direction: document.documentElement.dir, clientWidth: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
    check(`rtl-${width}`, geometry.direction === "rtl" && geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify(geometry));
    await context.close();
  }
  fs.writeFileSync(path.join(evidence, "fwd04-browser-result.json"), JSON.stringify({ candidate: process.env.FWD04_UAT_CANDIDATE || null, application_display_timezone: "Asia/Tehran", assignment: { tracking: "SR-FWD04-ASSIGNED", assigned_at: assigned.body.assigned_at, created_at: assigned.body.created_at }, no_assignment_fact: { tracking: "SR-FWD04-NOFACT", assigned_at: noFact.body.assigned_at }, timezoneRuns, checks }, null, 2) + "\n");
} finally {
  if (browser) await browser.close();
}
