import { expect, test, type Browser, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const apiBase = process.env.VITE_BACKEND_URL;
const browserBase = process.env.PLAYWRIGHT_BASE_URL;
if (!password || !fixturePath || !apiBase || !browserBase) throw new Error("Owned P3-09 qualification runner required");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p304_shipment: string; p305_cargo: string; p308_cargo_b: string;
  p309_accounts: Record<string, { public_id: string; email: string }>;
  p309_documents: Record<string, string>; p309_customer_a: number; p309_customer_b: number;
  p309_customer_a_label: string;
};
const pdf = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n%a\n");
test.setTimeout(180_000);

async function customer(browser: Browser, name: string) {
  const context = await browser.newContext({ baseURL: browserBase, locale: "fa-IR" });
  const page = await context.newPage();
  await page.goto("/customer");
  await page.locator("#customer-email").fill(fixture.p309_accounts[name].email);
  await page.locator("#customer-password").fill(password!);
  await page.locator("form button").first().click();
  await expect(page).toHaveURL(/\/customer\/requests/);
  await page.getByRole("link", { name: "حمل‌های من", exact: true }).click();
  await expect(page.getByRole("heading", { name: "حمل‌های من", exact: true })).toBeVisible();
  return { context, page };
}

async function openShipment(page: Page) {
  await page.locator(`a[href="/customer/shipments/${fixture.p304_shipment}"]`).click();
  await expect(page.getByRole("heading", { name: "کالاهای من", exact: true })).toBeVisible();
}

async function adminLogin(browser: Browser) {
  const context = await browser.newContext({ baseURL: browserBase, locale: "fa-IR" });
  const page = await context.newPage();
  await page.goto("/"); await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill("shared_transport_e2e_admin"); await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await page.getByRole("tab", { name: "دسترسی حساب مشتری", exact: true }).click();
  return { context, page };
}

test("P3-09 Customer A/B/C, union, exact bytes, Admin revoke and mobile browser return", async ({ browser }, testInfo) => {
  const a = await customer(browser, "a"); const errors: string[] = [];
  a.page.on("pageerror", error => errors.push(error.message));
  await openShipment(a.page);
  await expect(a.page.getByText("این حمل به‌صورت مشترک انجام می‌شود.")).toBeVisible();
  await expect(a.page.getByText("قطعات موتور", { exact: true }).first()).toBeVisible();
  await expect(a.page.locator("body")).not.toContainText("PRIVATE");
  await expect(a.page.locator("body")).not.toContainText("مقصد اختصاصی مشتری دوم");
  await expect(a.page.getByText(/خورگوس آزمایشی ← آکتائو آزمایشی/)).toBeVisible();
  await expect(a.page.getByText("گزارش شرکت حمل", { exact: false }).first()).toBeVisible();
  const detail = await a.page.request.get(`${apiBase}/api/customer/shipments/${fixture.p304_shipment}`);
  expect(detail.status()).toBe(200); expect(detail.headers()["cache-control"]).toContain("no-store");
  const payload = await detail.json();
  expect(payload.cargo.map((item: { public_id: string }) => item.public_id)).toEqual([fixture.p305_cargo]);
  expect(Number(payload.cargo[0].delivered)).toBe(93); expect(Number(payload.cargo[0].remaining)).toBe(7);
  expect(JSON.stringify(payload)).not.toContain("PRIVATE");
  await a.page.screenshot({ path: testInfo.outputPath("customer-shipment-desktop.png"), fullPage: true });
  await a.page.setViewportSize({ width: 390, height: 844 });
  expect(await a.page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await a.page.screenshot({ path: testInfo.outputPath("customer-shipment-mobile.png"), fullPage: true });
  const ownDocument = a.page.getByRole("article").filter({ has: a.page.getByText("کالای شما · نسخه 1", { exact: true }) });
  const downloadPromise = a.page.waitForEvent("download");
  await ownDocument.getByRole("button", { name: "دریافت سند" }).click();
  const downloaded = await downloadPromise;
  expect(downloaded.suggestedFilename()).toBe("document-v1.pdf"); expect(await downloaded.failure()).toBeNull();
  expect(await (await a.page.request.get(`${apiBase}/api/customer/documents/${fixture.p309_documents.a}/download`)).body()).toEqual(pdf);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/${fixture.p309_documents.b}/download`)).status()).toBe(404);
  const b = await customer(browser, "b"); await openShipment(b.page);
  await expect(b.page.getByText("کالای مشتری دوم", { exact: true }).first()).toBeVisible();
  await expect(b.page.getByText("قطعات موتور", { exact: true })).toHaveCount(0);
  await expect(b.page.getByText(/خورگوس آزمایشی ← مقصد اختصاصی مشتری دوم/)).toBeVisible();
  await expect(b.page.locator("body")).not.toContainText("آکتائو آزمایشی");
  await expect(b.page.getByText("هنوز تحویلی برای این کالا ثبت نشده است.")).toBeVisible();
  expect((await b.page.request.get(`${apiBase}/api/customer/documents/${fixture.p309_documents.a}/download`)).status()).toBe(404);
  const c = await customer(browser, "c");
  await expect(c.page.getByText("حملی در این فهرست برای شما در دسترس نیست.")).toBeVisible();
  await c.page.goto(`/customer/shipments/${fixture.p304_shipment}`); await expect(c.page.getByRole("alert")).toContainText("در دسترس نیست");
  const ab = await customer(browser, "ab"); await openShipment(ab.page);
  await expect(ab.page.getByText("کالای مشتری دوم", { exact: true }).first()).toBeVisible();
  await expect(ab.page.getByText("قطعات موتور", { exact: true }).first()).toBeVisible();
  const admin = await adminLogin(browser);
  // An authenticated Admin command changes only the chosen explicit grant.
  const grantRow = admin.page.locator("div.flex.flex-wrap.items-center.justify-between").filter({ has: admin.page.locator("bdi", { hasText: fixture.p309_accounts.a.email }) });
  await a.page.getByRole("link", { name: "درخواست‌های من", exact: true }).click();
  await grantRow.getByRole("button", { name: "لغو دسترسی", exact: true }).click();
  await expect(admin.page.getByText(/دسترسی لغو شد/)).toBeVisible();
  await a.page.goBack(); await expect(a.page.getByRole("alert")).toContainText("در دسترس نیست");
  await expect(a.page.getByRole("heading", { name: "کالاهای من" })).toHaveCount(0);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/${fixture.p309_documents.a}/download`)).status()).toBe(404);
  await a.page.getByRole("link", { name: "حمل‌های من", exact: true }).click();
  await expect(a.page.getByText("حملی در این فهرست برای شما در دسترس نیست.")).toBeVisible();
  await b.page.reload(); await expect(b.page.getByText("کالای مشتری دوم", { exact: true }).first()).toBeVisible();
  await ab.page.reload(); await expect(ab.page.getByText("قطعات موتور", { exact: true }).first()).toBeVisible();
  // Delay a real authorized body; revoke A while it is in flight. No focus or
  // pageshow event is synthesized. Acceptance must fetch current authorization.
  let releaseBody: () => void = () => undefined;
  let bodyReady: () => void = () => undefined;
  const release = new Promise<void>(resolve => { releaseBody = resolve; });
  const ready = new Promise<void>(resolve => { bodyReady = resolve; });
  let held = false;
  await ab.page.route(`**/api/customer/shipments/${fixture.p304_shipment}?*`, async route => {
    if (held) { await route.continue(); return; }
    held = true;
    const response = await route.fetch();
    expect((await response.json()).cargo).toHaveLength(2);
    bodyReady(); await release; await route.fulfill({ response });
  });
  await ab.page.getByRole("button", { name: "تازه‌سازی", exact: true }).click();
  await ready;
  const abGrant = admin.page.locator("div.flex.flex-wrap.items-center.justify-between")
    .filter({ has: admin.page.locator("bdi", { hasText: fixture.p309_accounts.ab.email }) })
    .filter({ hasText: fixture.p309_customer_a_label });
  await abGrant.getByRole("button", { name: "لغو دسترسی", exact: true }).click();
  await expect(abGrant).toHaveCount(0);
  releaseBody();
  await expect(ab.page.getByText("کالای مشتری دوم", { exact: true }).first()).toBeVisible();
  await expect(ab.page.getByText("قطعات موتور", { exact: true })).toHaveCount(0);
  expect((await ab.page.request.get(`${apiBase}/api/customer/documents/${fixture.p309_documents.a}/download`)).status()).toBe(404);
  expect((await ab.page.request.get(`${apiBase}/api/customer/documents/${fixture.p309_documents.b}/download`)).status()).toBe(200);
  await ab.page.screenshot({ path: testInfo.outputPath("customer-shipment-partial-revoke.png"), fullPage: true });
  await a.page.screenshot({ path: testInfo.outputPath("customer-shipment-revoked-mobile.png"), fullPage: true });
  expect(errors).toEqual([]);
  for (const item of [a, b, c, ab, admin]) await item.context.close();
});

test("P3-09 existing password change revokes an already open Shipment session; recovery stays opaque", async ({ browser }) => {
  const first = await customer(browser, "b"); await openShipment(first.page);
  const second = await customer(browser, "b");
  await second.page.getByRole("link", { name: "تغییر گذرواژه", exact: true }).click();
  await second.page.locator("#current-password").fill(password!);
  await second.page.locator("#new-password").fill(`${password!}Changed`);
  await second.page.locator("#confirm-password").fill(`${password!}Changed`);
  await second.page.locator("form button").click();
  await expect(second.page).toHaveURL(/\/customer$/);
  await first.page.getByRole("button", { name: "تازه‌سازی", exact: true }).click();
  await expect(first.page).toHaveURL(/\/customer$/);
  await expect(first.page.getByText("کالای مشتری دوم", { exact: true })).toHaveCount(0);
  await first.page.getByRole("link", { name: /فراموش/ }).click();
  await first.page.locator("#recovery-email").fill(fixture.p309_accounts.b.email);
  await first.page.locator("form button").first().click();
  const known = await first.page.getByRole("status").textContent();
  await first.page.locator("#recovery-email").fill("unknown-p309@example.test");
  await first.page.locator("form button").first().click();
  await expect(first.page.getByRole("status")).toHaveText(known!);
  await first.context.close(); await second.context.close();
});
