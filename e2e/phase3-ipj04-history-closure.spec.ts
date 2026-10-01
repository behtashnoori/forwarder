import fs from "node:fs";
import path from "node:path";
import { expect, test, type Browser, type Page } from "@playwright/test";
import { openShipmentSection } from "./helpers/shipment-workspace";

const databaseUrl = process.env.E2E_DATABASE_URL;
const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const evidencePath = process.env.PHASE3_FINAL_CANDIDATE_EVIDENCE_PATH;
if (!databaseUrl || !password || !fixturePath || !evidencePath) {
  throw new Error("FWD-IPJ-04 requires the owned final-candidate runtime inputs.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_integrated_cert_p3_06_documents_p313_")) {
  throw new Error("FWD-IPJ-04 is restricted to its owned loopback database.");
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  p313_shipment: string;
  p305_cargo: string;
  p308_cargo_b: string;
  p309_documents: Record<string, string>;
  p309_accounts: Record<string, { email: string }>;
  p313_target_label: string;
  p315_ipj04: {
    shipment: string;
    new_owner: string;
    original_report: string;
    corrected_report: string;
    eta_cargo: string;
    selected_route_time_versions: string[];
  };
};

test.setTimeout(300_000);

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page, expectedStatuses: number[] = []): BrowserEvidence {
  const evidence: BrowserEvidence = { consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [] };
  page.on("console", message => {
    const expected = expectedStatuses.some(status => message.text().includes(`status of ${status}`));
    if (message.type() === "error" && !expected) evidence.consoleErrors.push(message.text());
  });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => evidence.failedRequests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400 && !expectedStatuses.includes(response.status())) {
      evidence.unexpectedResponses.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  return evidence;
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.pageErrors, "uncaught browser errors").toEqual([]);
  const actionableFailures = evidence.failedRequests.filter(item =>
    !(item.includes("/closure") && item.endsWith("net::ERR_ABORTED")),
  );
  expect(actionableFailures, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  expect(evidence.consoleErrors.filter(item => !item.includes("favicon")), "browser console errors").toEqual([]);
}

async function loginExpert(page: Page, persona: string, landing: RegExp) {
  await page.context().clearCookies();
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).toHaveURL(landing);
}

async function token(page: Page) {
  const value = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(value).toBeTruthy();
  return value!;
}

async function openCompletedShipment(page: Page) {
  await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).first().click();
  const all = page.getByRole("button", { name: "نمایش همه وضعیت‌ها", exact: true });
  if (await all.isVisible()) await all.click();
  await page.getByRole("link", { name: /^مشاهده محموله عملیاتی / }).and(page.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`)).click();
  await expect(page.locator("#shipment-overview h1")).toBeVisible();
}

async function loginCustomer(browser: Browser, name: "a" | "b") {
  const context = await browser.newContext({ locale: "fa-IR" });
  const page = await context.newPage();
  await page.goto("/customer");
  await page.locator("#customer-email").fill(fixture.p309_accounts[name].email);
  await page.locator("#customer-password").fill(password!);
  await page.locator("form button").first().click();
  await expect(page).toHaveURL(/\/customer\/requests$/);
  await page.getByRole("link", { name: "حمل‌های من", exact: true }).click();
  await page.locator(`a[href="/customer/shipments/${fixture.p313_shipment}"]`).click();
  await expect(page.getByRole("heading", { name: "کالاهای من", exact: true })).toBeVisible();
  return { context, page };
}

test("FWD-IPJ-04 continues one shared Shipment through history, ETA, privacy, closure, and post-close denial", async ({ browser }, testInfo) => {
  const ownerContext = await browser.newContext({ locale: "fa-IR" });
  const adminContext = await browser.newContext({ locale: "fa-IR" });
  const oldContext = await browser.newContext({ locale: "fa-IR" });
  const owner = await ownerContext.newPage();
  const admin = await adminContext.newPage();
  const old = await oldContext.newPage();
  const ownerEvidence = observe(owner, [409]);
  const adminEvidence = observe(admin);
  const oldEvidence = observe(old, [404]);

  await loginExpert(owner, "transfer_target", /\/operations$/);
  await openCompletedShipment(owner);
  await expect(owner.getByText(fixture.p313_target_label, { exact: true }).first()).toBeVisible();
  await openShipmentSection(owner, "cargo", fixture.p313_shipment);
  await expect(owner.locator("#shipment-cargo article strong").filter({ hasText: /^قطعات موتور$/ }).first()).toBeVisible();
  await expect(owner.locator("#shipment-cargo article strong").filter({ hasText: /^کالای مشتری دوم$/ }).first()).toBeVisible();

  const routeReferenceTimes = owner.waitForResponse(response =>
    response.url().includes("/route-plans/") && response.url().endsWith("/reference-times"),
  );
  await openShipmentSection(owner, "route", fixture.p313_shipment);
  await expect(owner.getByRole("heading", { name: "وسیله و شرکت حمل هر بخش مسیر" })).toBeVisible();
  await owner.locator("summary", { hasText: "زمان مرجع و مبنای برنامه" }).click();
  expect((await routeReferenceTimes).status()).toBe(200);
  await openShipmentSection(owner, "cargo", fixture.p313_shipment);
  await expect(owner.getByRole("heading", { name: "تخصیص و مسیر هر کالا" })).toBeVisible();

  const etaResponse = owner.waitForResponse(response =>
    response.url().includes(`/cargo/${fixture.p315_ipj04.eta_cargo}/eta/ensure`) && response.status() === 200,
  );
  await openShipmentSection(owner, "tracking", fixture.p313_shipment);
  await expect(owner.getByText("اصلاح‌شده؛ محفوظ در سابقه", { exact: true })).toBeVisible();
  await expect(owner.getByText("اصلاح موقعیت برای گواه پیوستگی سفر", { exact: false })).toBeVisible();
  const eta = await (await etaResponse).json() as { next: { available: boolean }; final: { available: boolean }; source_fingerprint?: string };
  expect(eta.next.available || eta.final.available).toBe(true);
  await expect(owner.getByRole("region", { name: "زمان تقریبی رسیدن کالا", exact: true }).first()).toContainText("زمان محاسبه:");

  await openShipmentSection(owner, "delivery", fixture.p313_shipment);
  await expect(owner.getByRole("region", { name: "تحویل کالاها" })).toContainText("نسخه اصلاحی جاری");
  await expect(owner.getByRole("region", { name: "تحویل کالاها" })).toContainText("سابقه تحویل‌های اصلاح‌شده");

  await openShipmentSection(owner, "history", fixture.p313_shipment);
  await expect(owner.getByRole("heading", { name: "تاریخچه یکپارچه محموله" })).toBeVisible();
  await expect(owner.getByLabel("تاریخچه عملیات حمل")).not.toContainText("دریافت تاریخچه عملیات ممکن نشد");

  const a = await loginCustomer(browser, "a");
  const b = await loginCustomer(browser, "b");
  await expect(a.page.getByText("قطعات موتور", { exact: true }).first()).toBeVisible();
  await expect(a.page.getByText("کالای مشتری دوم", { exact: true })).toHaveCount(0);
  await expect(a.page.locator("body")).not.toContainText("PRIVATE");
  await expect(b.page.getByText("کالای مشتری دوم", { exact: true }).first()).toBeVisible();
  await expect(b.page.getByText("قطعات موتور", { exact: true })).toHaveCount(0);
  await expect(b.page.locator("body")).not.toContainText("کالای شما از نقطه میانی عبور کرده است");
  await expect(b.page.locator("body")).not.toContainText("اصلاح موقعیت برای گواه پیوستگی سفر");
  expect((await a.page.request.get(`/api/customer/documents/${fixture.p309_documents.b}/download`)).status()).toBe(404);
  expect((await b.page.request.get(`/api/customer/documents/${fixture.p309_documents.a}/download`)).status()).toBe(404);

  await loginExpert(admin, "admin", /\/admin$/);
  await admin.getByRole("tab", { name: "قواعد بستن پرونده", exact: true }).click();
  await expect(admin.getByRole("heading", { name: "قواعد بستن پرونده" })).toBeVisible();
  await admin.getByRole("button", { name: "تعریف نسخه V1 قواعد", exact: true }).click();
  const local = new Date(Date.now() - 86_400_000).toISOString().slice(0, 16);
  await admin.getByLabel("شروع اعتبار (زمان محلی)").fill(local);
  const policy = admin.waitForResponse(response => response.url().endsWith("/closure-policy/versions") && response.request().method() === "POST");
  await admin.getByRole("button", { name: "ثبت نسخه قواعد" }).click();
  expect((await policy).status()).toBe(201);

  await owner.bringToFront();
  await openShipmentSection(owner, "closure", fixture.p313_shipment);
  const closure = owner.getByRole("region", { name: "بررسی بستن پرونده" });
  await closure.getByRole("button", { name: "بررسی دوباره" }).click();
  await expect(closure.getByRole("button", { name: "بستن پرونده", exact: true })).toBeDisabled();
  await expect(closure.locator("li", { hasText: "تحویل نهایی محموله به‌صراحت ثبت شده باشد" })).toBeVisible();
  await expect(closure.locator("li", { hasText: "همه مراحل عملیاتی الزامی محموله کامل شده باشند" })).toBeVisible();
  await expect(closure.getByRole("button", { name: "بستن با استثنای مدیر" })).toHaveCount(0);
  await admin.goto(`/operations/shipments/${fixture.p313_shipment}`);
  await openShipmentSection(admin, "closure", fixture.p313_shipment);
  const adminClosure = admin.getByRole("region", { name: "بررسی بستن پرونده" });
  await adminClosure.getByRole("button", { name: "بستن با استثنای مدیر" }).click();
  await adminClosure.getByRole("button", { name: "تأیید نهایی بستن" }).click();
  await expect(adminClosure.getByRole("alert")).toContainText("دلیل");
  await adminClosure.getByLabel("دلیل بستن با استثنا (الزامی)").fill("PRIVATE-IPJ04-CLOSURE-EXCEPTION");
  const closed = admin.waitForResponse(response => response.url().endsWith("/close") && response.request().method() === "POST");
  await adminClosure.getByRole("button", { name: "تأیید نهایی بستن" }).click();
  expect((await closed).status()).toBe(201);
  await expect(adminClosure.getByText(/پرونده بسته شده است/)).toBeVisible();
  await owner.reload();
  await expect(owner.getByText("بسته‌شده", { exact: true })).toBeVisible();
  await openShipmentSection(owner, "route", fixture.p313_shipment);
  await expect(owner.getByRole("heading", { name: "اصلاح و تکمیل سوابق" })).toBeVisible();

  const denied = await owner.request.post(`/api/operational-shipments/${fixture.p313_shipment}/reported-facts`, {
    headers: { Authorization: `Bearer ${await token(owner)}`, "Idempotency-Key": crypto.randomUUID() },
    data: {
      scope: "CARGO", target_public_id: fixture.p305_cargo, kind: "LOCATION", source: "CARRIER_REPORT",
      occurred_at: new Date().toISOString(), location: { location_text: "ثبت تازه پس از بستن" },
      impacted_cargo_public_ids: [fixture.p305_cargo],
    },
  });
  expect(denied.status()).toBe(409);

  await loginExpert(old, "restricted", /\/operations$/);
  await old.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).first().click();
  const all = old.getByRole("button", { name: "نمایش همه وضعیت‌ها", exact: true });
  if (await all.isVisible()) await all.click();
  await expect(old.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`)).toHaveCount(0);
  expect((await old.request.get(`/api/operational-shipments/${fixture.p313_shipment}`, {
    headers: { Authorization: `Bearer ${await token(old)}` },
  })).status()).toBe(404);

  await a.page.reload();
  await b.page.reload();
  await expect(a.page.getByText("بسته‌شده", { exact: true })).toBeVisible();
  await expect(b.page.getByText("بسته‌شده", { exact: true })).toBeVisible();
  await expect(a.page.locator("body")).not.toContainText("PRIVATE");
  await expect(b.page.locator("body")).not.toContainText("کالای شما از نقطه میانی عبور کرده است");
  await expect(b.page.locator("body")).not.toContainText("اصلاح موقعیت برای گواه پیوستگی سفر");
  await owner.setViewportSize({ width: 390, height: 844 });
  expect(await owner.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await owner.screenshot({ path: testInfo.outputPath("ipj04-closed-history-mobile.png"), fullPage: true });

  fs.writeFileSync(path.join(evidencePath!, "fwd-ipj04-contract.json"), JSON.stringify({
    owner_transfer: "PASS",
    shared_cargo_route_execution_allocation: "PASS",
    report_correction_history: "PASS",
    contextual_documents: "PASS",
    partial_delivery_history: "PASS",
    eta: "PASS",
    closure: "PASS",
    old_owner_denial: "PASS",
    customer_a_b_privacy_after_transfer_and_closure: "PASS",
    production_accessed: false,
  }, null, 2));

  expectClean(ownerEvidence);
  expectClean(adminEvidence);
  expectClean(oldEvidence);
  await a.context.close();
  await b.context.close();
  await ownerContext.close();
  await adminContext.close();
  await oldContext.close();
});
