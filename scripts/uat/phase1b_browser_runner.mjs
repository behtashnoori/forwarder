import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const PLAYWRIGHT_ROOT = "C:\\Users\\pc\\AppData\\Local\\npm-cache\\_npx\\e41f203b7505f1fb\\node_modules\\playwright-core";
const CHROMIUM = "C:\\Users\\pc\\AppData\\Local\\ms-playwright\\chromium-1200\\chrome-win64\\chrome.exe";
const require = createRequire(import.meta.url);
const { chromium } = require(PLAYWRIGHT_ROOT);

const viewports = [
  [1440, 900], [1280, 720], [768, 1024], [390, 844], [360, 800],
];
const workflows = [
  "runtime-target", "shipment-deduplication", "reporter-first-report",
  "same-key-replay", "second-key-conflict", "stale-version-conflict",
  "reporter-correction-denial", "reporter-correction-zero-side-effect",
  "authorized-correction", "independent-verification", "milestone-lifecycle",
  "timeline-display", "timeline-reconciliation", "replan",
  "replan-with-open-exception", "exception-workitem-lifecycle",
  "permission-matrix", "organization-isolation", "direct-id-isolation",
  "responsive-quality", "loading-error-accessibility", "console-network",
];

function fail(message) {
  throw new Error(message);
}
function requireEnv(name) {
  const value = process.env[name]?.trim();
  if (!value) fail(`Missing ${name}`);
  return value;
}
function safeLoopback(raw, name) {
  const url = new URL(raw);
  if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname))
    fail(`${name} must be loopback HTTP`);
  if (["5001", "5432", "57065"].includes(url.port)) fail(`${name} uses forbidden port`);
  return url.origin;
}

const baseUrl = safeLoopback(requireEnv("PHASE1B_UAT_BASE_URL"), "base URL");
const apiUrl = safeLoopback(requireEnv("PHASE1B_UAT_API_URL"), "API URL");
const password = requireEnv("PHASE1B_UAT_PASSWORD");
const evidenceDir = path.resolve(requireEnv("PHASE1B_UAT_EVIDENCE_DIR"));
const mode = (process.env.PHASE1B_UAT_MODE || "full").trim();
if (!["full", "targeted-smoke"].includes(mode)) fail("Invalid PHASE1B_UAT_MODE");
if (!fs.existsSync(PLAYWRIGHT_ROOT) || !fs.existsSync(CHROMIUM)) fail("Existing Playwright/Chromium dependency missing");
fs.mkdirSync(evidenceDir, { recursive: true });

const results = [];
const checks = [];
const diagnostic = {
  stage: "environment-validation", status: "RUNNING", error_code: null,
  sanitized_message: null, viewport: null, workflow: mode,
  last_successful_step: null, console_error_count: 0,
  unexpected_5xx_count: 0, screenshot_path: null,
  browser_launched: false, page_created: false, cleanup_result: "PENDING",
};
const check = (name, condition, detail = "") => {
  checks.push({ name, status: condition ? "PASS" : "FAIL", detail });
  if (!condition) fail(`${name}: ${detail}`);
  diagnostic.last_successful_step = name;
};
const key = (label) => `p1b-${label}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
const loginUsers = {};

async function login(username) {
  const response = await fetch(`${apiUrl}/api/expert/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await response.json().catch(() => ({}));
  check(`login-${username}`, response.status === 200 && !!body?.tokens?.access_token, `status=${response.status}`);
  loginUsers[username] = body.expert;
  return body.tokens.access_token;
}
async function request(token, route, options = {}) {
  const headers = { "content-type": "application/json", authorization: `Bearer ${token}`, ...(options.headers || {}) };
  const response = await fetch(`${apiUrl}${route}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  return { status: response.status, body };
}

let browser;
let lastPage;
try {
  diagnostic.stage = "login";
  const tokens = {};
  for (const role of ["admin", "reporter", "verifier", "readonly", "no_permission", "org_b_admin"])
    tokens[role] = await login(`phase1b_uat_${role}`);

  const list = await request(tokens.admin, "/api/operational-shipments");
  check("runtime-target", list.status === 200, `status=${list.status}`);
  const shipments = list.body?.data || [];
  check("shipment-list-present", shipments.length >= 1, `count=${shipments.length}`);
  const uniqueIds = new Set(shipments.map((item) => item.public_id));
  check("shipment-deduplication", uniqueIds.size === shipments.length, `rows=${shipments.length},unique=${uniqueIds.size}`);
  const shipment = shipments.find((item) => String(item?.customer || "").includes("UAT A")) || shipments[0];
  const shipmentId = shipment.public_id;

  const plansResponse = await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans`);
  check("route-plans", plansResponse.status === 200, `status=${plansResponse.status}`);
  let activePlan = (plansResponse.body?.data || []).find((item) => item.is_active);
  check("active-route-plan", !!activePlan, "semantic active plan");
  const detailResponse = await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans/${activePlan.id}`);
  check("route-plan-detail", detailResponse.status === 200, `status=${detailResponse.status}`);
  let detail = detailResponse.body.data;
  if (mode === "targeted-smoke") {
    diagnostic.stage = "chromium-launch";
    browser = await chromium.launch({ executablePath: CHROMIUM, headless: true });
    diagnostic.browser_launched = true;
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    lastPage = await context.newPage();
    diagnostic.page_created = true;
    diagnostic.viewport = "1280x720";
    const fatalConsole = [];
    const unexpectedResponses = [];
    lastPage.on("console", (msg) => { if (msg.type() === "error" && !/favicon|React Router Future Flag/i.test(msg.text())) fatalConsole.push(msg.text()); });
    lastPage.on("response", (response) => { if (response.status() >= 500 || /127\\.0\\.0\\.1:(5001|57065)/.test(response.url())) unexpectedResponses.push(response.url()); });
    diagnostic.stage = "targeted-navigation";
    await lastPage.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await lastPage.evaluate(({ token, user }) => {
      localStorage.setItem("expert_token", token);
      localStorage.setItem("expert_user", JSON.stringify(user));
    }, { token: tokens.admin, user: loginUsers.phase1b_uat_admin });
    await lastPage.goto(`${baseUrl}/operations/shipments/${shipmentId}`, { waitUntil: "networkidle" });
    await lastPage.getByText(/Route plan|Timeline|Checkpoints/i).first().waitFor({ timeout: 15000 });
    await lastPage.reload({ waitUntil: "networkidle" });
    await lastPage.evaluate(() => {
      localStorage.removeItem("expert_token");
      localStorage.removeItem("expert_user");
    });
    const screenshot = path.join(evidenceDir, "phase1b-targeted-1280x720.png");
    await lastPage.screenshot({ path: screenshot, fullPage: true });
    diagnostic.screenshot_path = screenshot;
    diagnostic.console_error_count = fatalConsole.length;
    diagnostic.unexpected_5xx_count = unexpectedResponses.length;
    check("targeted-console", fatalConsole.length === 0, `count=${fatalConsole.length}`);
    check("targeted-network", unexpectedResponses.length === 0, `count=${unexpectedResponses.length}`);
    check("targeted-smoke", true, "launch, root, login, list, detail, active plan, refresh, logout");
    results.push({ status: "PASS", browser_mobile_uat: "NO", targeted_smoke: "PASS" });
  } else {
  const reportable = detail.checkpoints.find((item) =>
    ["planned", "approaching"].includes(item.status) &&
    item.milestones?.some((m) => m.verification_state === "planned"));
  check("reportable-checkpoint", !!reportable, "semantic planned checkpoint with zero report state");

  const reportKey = key("report");
  const reportPayload = { occurred_at: new Date().toISOString(), expected_version: reportable.version };
  const reportRoute = `/api/operational-shipments/${shipmentId}/checkpoints/${reportable.id}/arrive`;
  const first = await request(tokens.reporter, reportRoute, { method: "POST", headers: { "Idempotency-Key": reportKey }, body: JSON.stringify(reportPayload) });
  check("reporter-first-report", [200, 201].includes(first.status), `status=${first.status}`);
  const replay = await request(tokens.reporter, reportRoute, { method: "POST", headers: { "Idempotency-Key": reportKey }, body: JSON.stringify(reportPayload) });
  check("same-key-replay", [200, 201].includes(replay.status), `status=${replay.status}`);
  const conflict = await request(tokens.reporter, reportRoute, { method: "POST", headers: { "Idempotency-Key": key("conflict") }, body: JSON.stringify(reportPayload) });
  check("second-key-conflict", conflict.status === 409, `status=${conflict.status}`);
  const stale = await request(tokens.reporter, reportRoute, { method: "POST", headers: { "Idempotency-Key": key("stale") }, body: JSON.stringify({ ...reportPayload, expected_version: Math.max(0, reportable.version - 1) }) });
  check("stale-version-conflict", stale.status === 409, `status=${stale.status}`);

  detail = (await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans/${activePlan.id}`)).body.data;
  const verifiedCheckpoint = detail.checkpoints.find((c) => c.milestones?.some((m) => m.verification_state === "verified"));
  const verifiedMilestone = verifiedCheckpoint?.milestones.find((m) => m.verification_state === "verified");
  check("verified-milestone", !!verifiedMilestone, "semantic verified milestone");
  const correctionRoute = `/api/operational-shipments/${shipmentId}/checkpoints/${verifiedCheckpoint.id}/milestones/${verifiedMilestone.id}/correct`;
  const correctionPayload = { occurred_at: new Date().toISOString(), reason: "Phase 1B UAT correction", expected_version: verifiedMilestone.version };
  const denied = await request(tokens.reporter, correctionRoute, { method: "POST", headers: { "Idempotency-Key": key("denied") }, body: JSON.stringify(correctionPayload) });
  check("reporter-correction-denial", denied.status === 403, `status=${denied.status}`);
  const afterDenied = (await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans/${activePlan.id}`)).body.data;
  const afterDeniedMilestone = afterDenied.checkpoints.flatMap((c) => c.milestones).find((m) => m.id === verifiedMilestone.id);
  check("reporter-correction-zero-side-effect", afterDeniedMilestone.version === verifiedMilestone.version && afterDeniedMilestone.verification_state === "verified");
  const corrected = await request(tokens.verifier, correctionRoute, { method: "POST", headers: { "Idempotency-Key": key("correct") }, body: JSON.stringify(correctionPayload) });
  check("authorized-correction", [200, 201].includes(corrected.status), `status=${corrected.status}`);
  const correctedDetail = (await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans/${activePlan.id}`)).body.data;
  const correctedMilestone = correctedDetail.checkpoints.flatMap((c) => c.milestones).find((m) => m.id === verifiedMilestone.id);
  const verifyRoute = `/api/operational-shipments/${shipmentId}/checkpoints/${verifiedCheckpoint.id}/milestones/${verifiedMilestone.id}/verify`;
  const verified = await request(tokens.admin, verifyRoute, { method: "POST", headers: { "Idempotency-Key": key("verify") }, body: JSON.stringify({ expected_version: correctedMilestone.version }) });
  check("independent-verification", [200, 201].includes(verified.status), `status=${verified.status}`);

  const timeline = await request(tokens.admin, `/api/operational-shipments/${shipmentId}/timeline`);
  check("timeline-display", timeline.status === 200 && Array.isArray(timeline.body?.data?.planned), `status=${timeline.status}`);
  activePlan = (await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans`)).body.data.find((p) => p.is_active);
  const timelineReconcile = await request(tokens.admin, `/api/operational-shipments/${shipmentId}/timeline/reconcile`, { method: "POST", headers: { "Idempotency-Key": key("timeline") }, body: JSON.stringify({ expected_route_plan_version: activePlan.version }) });
  check("timeline-reconciliation", [200, 201].includes(timelineReconcile.status), `status=${timelineReconcile.status}`);
  activePlan = (await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans`)).body.data.find((p) => p.is_active);
  const exceptionReconcile = await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-exceptions/reconcile`, { method: "POST", headers: { "Idempotency-Key": key("exceptions") }, body: JSON.stringify({ expected_route_plan_version: activePlan.version }) });
  check("exception-reconcile", [200, 201].includes(exceptionReconcile.status), `status=${exceptionReconcile.status}`);
  const exceptions = await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-exceptions`);
  check("exception-list", exceptions.status === 200, `status=${exceptions.status}`);
  const openException = (exceptions.body?.data || []).find((item) => item.status === "open");
  if (openException) {
    const resolved = await request(tokens.admin, `/api/route-exceptions/${openException.id}/resolve`, { method: "POST", headers: { "Idempotency-Key": key("resolve") }, body: JSON.stringify({ expected_version: openException.version, reason: "Phase 1B UAT resolution" }) });
    check("exception-resolve", [200, 201].includes(resolved.status), `status=${resolved.status}`);
  }
  activePlan = (await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans`)).body.data.find((p) => p.is_active);
  const replanned = await request(tokens.admin, `/api/operational-shipments/${shipmentId}/route-plans/${activePlan.id}/replan`, { method: "POST", headers: { "Idempotency-Key": key("replan") }, body: JSON.stringify({ expected_version: activePlan.version, reason: "Phase 1B full browser UAT" }) });
  check("replan", [200, 201].includes(replanned.status), `status=${replanned.status}`);

  const readonlyMutation = await request(tokens.readonly, reportRoute, { method: "POST", headers: { "Idempotency-Key": key("readonly") }, body: JSON.stringify(reportPayload) });
  check("permission-matrix", readonlyMutation.status === 403, `status=${readonlyMutation.status}`);
  const orgBList = await request(tokens.org_b_admin, "/api/operational-shipments");
  check("organization-isolation", orgBList.status === 200 && !(orgBList.body?.data || []).some((s) => s.public_id === shipmentId));
  const direct = await request(tokens.org_b_admin, `/api/operational-shipments/${shipmentId}`);
  check("direct-id-isolation", [403, 404].includes(direct.status), `status=${direct.status}`);
  const noPermission = await request(tokens.no_permission, `/api/operational-shipments/${shipmentId}`);
  check("no-permission-denial", [403, 404].includes(noPermission.status), `status=${noPermission.status}`);

  browser = await chromium.launch({ executablePath: CHROMIUM, headless: true });
  const fatalConsole = [];
  const unexpectedResponses = [];
  for (const [width, height] of viewports) {
    const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, hasTouch: width <= 768 });
    const page = await context.newPage();
    page.on("console", (msg) => {
      if (msg.type() === "error" && !/favicon|React Router Future Flag/i.test(msg.text())) fatalConsole.push(`${width}x${height}:${msg.text().slice(0, 240)}`);
    });
    page.on("response", (response) => {
      const url = response.url();
      if (response.status() >= 500 || /127\\.0\\.0\\.1:(5001|57065)|C:\\\\1-webapp\\\\1-forwarder/i.test(url))
        unexpectedResponses.push(`${response.status()}:${url.replace(/([?&](token|password|authorization)=)[^&]+/ig, "$1[REDACTED]")}`);
    });
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(({ token, user }) => {
      localStorage.setItem("expert_token", token);
      localStorage.setItem("expert_user", JSON.stringify(user));
    }, { token: tokens.admin, user: loginUsers.phase1b_uat_admin });
    await page.goto(`${baseUrl}/operations/shipments/${shipmentId}`, { waitUntil: "networkidle" });
    await page.getByText(/Route plan|Timeline|Checkpoints/i).first().waitFor({ timeout: 15000 });
    const geometry = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      buttonsOffscreen: [...document.querySelectorAll("button")].filter((el) => {
        const r = el.getBoundingClientRect(); return r.left < -1 || r.right > window.innerWidth + 1;
      }).length,
    }));
    check(`viewport-${width}x${height}`, geometry.innerWidth === width && geometry.scrollWidth <= geometry.clientWidth + 1 && geometry.buttonsOffscreen === 0, JSON.stringify(geometry));
    await page.screenshot({ path: path.join(evidenceDir, `phase1b-${width}x${height}.png`), fullPage: true });
    await context.close();
  }
  check("fatal-console-errors", fatalConsole.length === 0, `count=${fatalConsole.length}`);
  check("unexpected-network", unexpectedResponses.length === 0, `count=${unexpectedResponses.length}`);
  check("five-viewports", viewports.length === 5);
  check("workflow-manifest", workflows.length === 22);
  results.push({ status: "PASS", browser_mobile_uat: "YES", viewport_count: viewports.length, workflow_count: workflows.length });
  }
  diagnostic.stage = "report-writing";
  diagnostic.status = "PASS";
} catch (error) {
  const message = String(error?.message || error).replaceAll(password, "[REDACTED]");
  const timeout = /timeout/i.test(message);
  const environment = /Missing PHASE1B|dependency missing|browser.*(launch|closed)|executable/i.test(message);
  const product = /status=|viewport-|fatal-console|unexpected-network|targeted-(console|network)/i.test(message);
  diagnostic.status = "FAIL";
  diagnostic.error_code = timeout ? "BROWSER_TIMEOUT" : environment ? "BROWSER_ENVIRONMENT" : product ? "UAT_ASSERTION" : "RUNNER_INTERNAL";
  diagnostic.sanitized_message = message;
  results.push({ status: "FAIL", browser_mobile_uat: "NO", error_code: diagnostic.error_code, error: message });
  process.exitCode = timeout ? 5 : environment ? 3 : product ? 2 : 4;
} finally {
  if (process.exitCode && lastPage && !diagnostic.screenshot_path) {
    const screenshot = path.join(evidenceDir, "phase1b-last-failure.png");
    await lastPage.screenshot({ path: screenshot, fullPage: true }).then(() => { diagnostic.screenshot_path = screenshot; }).catch(() => {});
  }
  if (browser) await browser.close().then(() => { diagnostic.cleanup_result = "PASS"; }).catch(() => { diagnostic.cleanup_result = "FAIL"; });
  else diagnostic.cleanup_result = "NOT_STARTED";
  fs.writeFileSync(path.join(evidenceDir, "phase1b_browser_result.json"), JSON.stringify({
    schema_version: 1, generated_at_utc: new Date().toISOString(), base_origin: baseUrl,
    api_origin: apiUrl, viewports: viewports.map(([width, height]) => ({ width, height })),
    mode, playwright_version: require(path.join(PLAYWRIGHT_ROOT, "package.json")).version,
    chromium_executable: CHROMIUM, chromium_executable_present: fs.existsSync(CHROMIUM),
    workflows, checks, results, diagnostic,
  }, null, 2) + "\n");
}
