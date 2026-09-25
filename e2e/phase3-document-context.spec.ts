import { expect, test, type Browser, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const apiBase = process.env.VITE_BACKEND_URL;
const browserBase = process.env.PLAYWRIGHT_BASE_URL;
if (!password || !fixturePath || !apiBase || !browserBase) throw new Error("P3-06 requires an owned synthetic browser runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p304_shipment: string; p304_road_leg: number; p304_foreign_leg: number;
  p305_cargo: string; tenant_b_cargo: string; foreign_unit: string;
  p306_account_a: string; p306_account_b: string;
  p306_email_a: string; p306_email_b: string;
  p306_crm_customer: number;
};
const pdf = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF");
test.setTimeout(180_000);

async function expert(page: Page, username = "shared_transport_e2e_restricted") {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  if (username === "shared_transport_e2e_admin") {
    await page.goto(`/operations/shipments/${fixture.p304_shipment}`);
  } else {
    await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
    await page.locator(`a[href="/operations/shipments/${fixture.p304_shipment}"]`).click();
  }
  await expect(page.getByRole("heading", { name: "خلاصه محموله" })).toBeVisible();
  await page.locator("summary", { hasText: "جزئیات عملیاتی بیشتر" }).click();
  await expect(page.getByRole("heading", { name: "اسناد و مدارک حمل" })).toBeVisible();
}

async function customer(browser: Browser, email: string) {
  const context = await browser.newContext({ baseURL: browserBase, locale: "fa-IR" });
  const page = await context.newPage();
  await page.goto("/customer");
  await page.locator("#customer-email").fill(email);
  await page.locator("#customer-password").fill(password!);
  await page.locator("form button").first().click();
  await expect(page).toHaveURL(/\/customer\/requests/);
  await page.getByRole("link", { name: "اسناد مشترک" }).click();
  await expect(page.getByRole("heading", { name: "اسناد به‌اشتراک‌گذاشته‌شده با شما" })).toBeVisible();
  return { context, page };
}

async function upload(page: Page, title: string, filename: string, content = pdf) {
  await page.getByLabel("نوع یا دسته تجاری سند").fill(title);
  await page.getByLabel("انتخاب فایل سند").setInputFiles({ name: filename, mimeType: "application/pdf", buffer: content });
  const response = page.waitForResponse(item => item.request().method() === "POST" &&
    item.url().endsWith(`/operational-shipments/${fixture.p304_shipment}/documents`));
  await page.getByRole("button", { name: "بارگذاری سند", exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(201);
  return (await result.json()).data as { public_id: string; context: { visibility: string; type: string } };
}

test("P3-06 — contextual upload, explicit audience, exact version, history, privacy and partial retry", async ({ page, browser }) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await expert(page);
  const docs = page.getByRole("heading", { name: "اسناد و مدارک حمل" }).locator("..").locator("..");
  await expect(docs.getByLabel("Document upload context")).toBeVisible();

  const internal = await upload(page, "P306 داخلی", "internal.pdf");
  expect(internal.context.visibility).toBe("INTERNAL");
  await expect(docs.getByText("مربوط به: پرونده حمل").first()).toBeVisible();
  await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  await page.locator(`a[href="/operations/shipments/${fixture.p304_shipment}"]`).click();
  await page.locator("summary", { hasText: "جزئیات عملیاتی بیشتر" }).click();
  await expect(page.getByText("internal.pdf")).toBeVisible();

  await page.getByLabel("Document upload context").selectOption("CARGO");
  await page.getByLabel("Document upload target").selectOption(fixture.p305_cargo);
  await page.getByLabel("Document upload visibility").selectOption("CARGO_OWNER");
  const cargo = await upload(page, "P306 کالا", "cargo-private.pdf");
  expect(cargo.context.type).toBe("CARGO");
  let cargoArticle = page.getByRole("article").filter({ hasText: "cargo-private.pdf" }).first();
  await cargoArticle.locator("summary", { hasText: "اصلاح زمینه یا دسترسی" }).click();
  await cargoArticle.getByLabel(`Document context ${cargo.public_id}`).selectOption("ROUTE_LEG");
  await cargoArticle.getByLabel(`Document target ${cargo.public_id}`).selectOption(String(fixture.p304_road_leg));
  await cargoArticle.getByRole("button", { name: "ثبت اصلاح با تاریخچه" }).click();
  await expect(cargoArticle.getByText("مربوط به: مرحله مسیر")).toBeVisible();
  cargoArticle = page.getByRole("article").filter({ hasText: "cargo-private.pdf" }).first();
  await cargoArticle.locator("summary", { hasText: "اصلاح زمینه یا دسترسی" }).click();
  await cargoArticle.getByLabel(`Document context ${cargo.public_id}`).selectOption("EXECUTION_UNIT");
  const executionChoice = await cargoArticle.getByLabel(`Document target ${cargo.public_id}`).locator("option").first().getAttribute("value");
  expect(executionChoice).toBeTruthy();
  await cargoArticle.getByLabel(`Document target ${cargo.public_id}`).selectOption(executionChoice!);
  await cargoArticle.getByRole("button", { name: "ثبت اصلاح با تاریخچه" }).click();
  await expect(cargoArticle.getByText("مربوط به: اجرای حمل")).toBeVisible();
  await cargoArticle.locator("summary", { hasText: "اصلاح زمینه یا دسترسی" }).click();
  await cargoArticle.getByRole("button", { name: "نمایش تاریخچه زمینه و دسترسی" }).click();
  await expect(cargoArticle.getByText(/CONTEXT_CHANGED/).first()).toBeVisible();

  await page.getByLabel("Document upload context").selectOption("SHIPMENT");
  await page.getByLabel("Document upload visibility").selectOption("EXPLICIT_SHARED");
  await page.getByLabel("Document upload audiences").selectOption([fixture.p306_account_a]);
  const shared = await upload(page, "P306 مشترک", "shared-v1.pdf");
  expect(shared.context.visibility).toBe("EXPLICIT_SHARED");
  const ownerToken = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(ownerToken).toBeTruthy();
  for (const [type, target] of [
    ["CARGO", fixture.tenant_b_cargo], ["ROUTE_LEG", String(fixture.p304_foreign_leg)],
    ["EXECUTION_UNIT", fixture.foreign_unit],
  ]) {
    const denied = await page.request.post(`${apiBase}/api/internal/operational-shipments/${fixture.p304_shipment}/documents`, {
      headers: { Authorization: `Bearer ${ownerToken}`, "Idempotency-Key": `p306-foreign-${type}` },
      multipart: { title: "خارج از محدوده", context_type: type, context_target_public_id: target,
        file: { name: "foreign.pdf", mimeType: "application/pdf", buffer: pdf } },
    });
    expect(denied.status()).toBe(404);
  }

  const a = await customer(browser, fixture.p306_email_a);
  await expect(a.page.getByText("document-v1.pdf")).toBeVisible();
  await expect(a.page.getByText("internal.pdf")).toHaveCount(0);
  await expect(a.page.getByText("cargo-private.pdf")).toHaveCount(0);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/${internal.public_id}/download`)).status()).toBe(404);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/${cargo.public_id}/download`)).status()).toBe(404);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/guessed-file/download`)).status()).toBe(404);
  const b = await customer(browser, fixture.p306_email_b);
  await expect(b.page.getByText("document-v1.pdf")).toHaveCount(0);
  expect((await b.page.request.get(`${apiBase}/api/customer/documents/${shared.public_id}/download`)).status()).toBe(404);

  const sharedArticle = page.getByRole("article").filter({ hasText: "shared-v1.pdf" }).first();
  await sharedArticle.getByRole("button", { name: "جایگزینی این نسخه" }).click();
  const replacement = await upload(page, "P306 مشترک", "shared-v2.pdf");
  expect(replacement.context.visibility).toBe("INTERNAL");
  await a.page.reload();
  await expect(a.page.getByText("document-v1.pdf")).toHaveCount(0);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/${shared.public_id}/download`)).status()).toBe(404);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/${replacement.public_id}/download`)).status()).toBe(404);

  const nextArticle = page.getByRole("article").filter({ hasText: "shared-v2.pdf" }).first();
  await nextArticle.locator("summary", { hasText: "اصلاح زمینه یا دسترسی" }).click();
  await nextArticle.getByLabel(`Document visibility ${replacement.public_id}`).selectOption("EXPLICIT_SHARED");
  await nextArticle.getByLabel(`Document audiences ${replacement.public_id}`).selectOption([fixture.p306_account_a]);
  await nextArticle.getByRole("button", { name: "ثبت اصلاح با تاریخچه" }).click();
  await expect(nextArticle.getByText(/چه کسانی می‌توانند ببینند؟ مشتریان انتخاب‌شده/)).toBeVisible();
  await a.page.reload();
  await expect(a.page.getByText("document-v2.pdf")).toBeVisible();
  await expect(b.page.getByText("document-v2.pdf")).toHaveCount(0);

  await page.getByLabel("Document upload context").selectOption("SHIPMENT");
  await page.getByLabel("Document upload visibility").selectOption("INTERNAL");
  await page.getByLabel("نوع یا دسته تجاری سند").fill("P306 چندفایلی");
  await page.getByLabel("انتخاب فایل سند").setInputFiles([
    { name: "good.pdf", mimeType: "application/pdf", buffer: pdf },
    { name: "bad.pdf", mimeType: "application/pdf", buffer: Buffer.from("not a PDF") },
  ]);
  await page.getByRole("button", { name: "بارگذاری 2 فایل" }).click();
  await expect(page.getByText("good.pdf: ثبت شد")).toBeVisible();
  await expect(page.getByText(/bad.pdf: ناموفق/)).toBeVisible();
  await page.getByLabel("انتخاب فایل سند").setInputFiles({ name: "bad.pdf", mimeType: "application/pdf", buffer: pdf });
  await page.getByRole("button", { name: "بارگذاری سند", exact: true }).click();
  await expect(page.getByText("bad.pdf: ثبت شد")).toBeVisible();

  const adminContext = await browser.newContext({ baseURL: browserBase, locale: "fa-IR" });
  const adminPage = await adminContext.newPage();
  await adminPage.goto("/");
  await adminPage.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await adminPage.getByLabel("نام کاربری").fill("shared_transport_e2e_admin");
  await adminPage.getByLabel("رمز عبور").fill(password!);
  await adminPage.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect.poll(() => adminPage.evaluate(() => Boolean(localStorage.getItem("expert_token")))).toBe(true);
  const adminToken = await adminPage.evaluate(() => localStorage.getItem("expert_token"));
  expect(adminToken).toBeTruthy();
  const adminPath = `${apiBase}/api/internal/operational-shipments/${fixture.p304_shipment}/documents`;
  const adminHeaders = { Authorization: `Bearer ${adminToken}`, "Idempotency-Key": "p306-admin-denied" };
  expect((await adminPage.request.get(adminPath, { headers: adminHeaders })).status()).toBe(200);
  expect((await adminPage.request.post(adminPath, {
    headers: adminHeaders,
    multipart: { title: "ممنوع", file: { name: "admin.pdf", mimeType: "application/pdf", buffer: pdf } },
  })).status()).toBe(404);
  expect(errors).toEqual([]);
  await a.context.close(); await b.context.close(); await adminContext.close();
});

test("DN10 — Admin grant → own-Cargo exact download → revoke → mobile back/reopen denied", async ({ page, browser }, testInfo) => {
  await expert(page);
  await page.getByLabel("Document upload context").selectOption("CARGO");
  await page.getByLabel("Document upload target").selectOption(fixture.p305_cargo);
  await page.getByLabel("Document upload visibility").selectOption("CARGO_OWNER");
  const cargo = await upload(page, "مدرک کالای مشتری", "dn10-cargo.pdf");
  const a = await customer(browser, fixture.p306_email_a);
  await a.page.setViewportSize({ width: 390, height: 844 });
  const cargoCard = a.page.getByRole("article").filter({ hasText: "مربوط به: کالای شما" });
  await expect(cargoCard).toHaveCount(0);
  expect((await a.page.request.get(`${apiBase}/api/customer/documents/${cargo.public_id}/download`)).status()).toBe(404);

  const adminContext = await browser.newContext({ baseURL: browserBase, locale: "fa-IR" });
  const admin = await adminContext.newPage();
  await admin.goto("/");
  await admin.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await admin.getByLabel("نام کاربری").fill("shared_transport_e2e_admin");
  await admin.getByLabel("رمز عبور").fill(password!);
  await admin.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await admin.getByRole("tab", { name: "دسترسی حساب مشتری", exact: true }).click();
  await expect(admin.getByText("هنوز دسترسی‌ای ثبت نشده است.")).toBeVisible();
  await admin.getByLabel("حساب پورتال", { exact: true }).selectOption(fixture.p306_account_a);
  await admin.getByLabel("مشتری / شرکت", { exact: true }).selectOption(String(fixture.p306_crm_customer));
  await admin.getByRole("button", { name: "اعطای دسترسی", exact: true }).click();
  await expect(admin.getByText("دسترسی ثبت شد.")).toBeVisible();
  await admin.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true }).click();
  await admin.getByRole("tab", { name: "دسترسی حساب مشتری", exact: true }).click();
  await expect(admin.getByRole("button", { name: "لغو دسترسی" })).toBeVisible();
  await admin.screenshot({ path: testInfo.outputPath("dn10-admin.png"), fullPage: true });

  await a.page.reload();
  await expect(cargoCard).toBeVisible();
  await a.page.screenshot({ path: testInfo.outputPath("dn10-customer-mobile.png"), fullPage: true });
  const downloaded = a.page.waitForEvent("download");
  await cargoCard.getByRole("button", { name: "دریافت سند" }).click();
  const download = await downloaded;
  expect(download.suggestedFilename()).toBe("document-v1.pdf");
  expect(await download.failure()).toBeNull();
  expect(await (await a.page.request.get(`${apiBase}/api/customer/documents/${cargo.public_id}/download`)).body()).toEqual(pdf);
  const b = await customer(browser, fixture.p306_email_b);
  await expect(b.page.getByText("مربوط به: کالای شما")).toHaveCount(0);
  expect((await b.page.request.get(`${apiBase}/api/customer/documents/${cargo.public_id}/download`)).status()).toBe(404);

  await a.page.getByRole("link", { name: "درخواست‌های من", exact: true }).click();
  await admin.getByRole("button", { name: "لغو دسترسی", exact: true }).click();
  await expect(admin.getByText(/دسترسی لغو شد/)).toBeVisible();
  await a.page.goBack();
  await expect(a.page.getByRole("heading", { name: "اسناد به‌اشتراک‌گذاشته‌شده با شما" })).toBeVisible();
  await expect(cargoCard).toHaveCount(0);
  const denied = await a.page.request.get(`${apiBase}/api/customer/documents/${cargo.public_id}/download`);
  expect(denied.status()).toBe(404);
  expect(denied.headers()["cache-control"]).toContain("no-store");
  await a.page.reload();
  await expect(cargoCard).toHaveCount(0);
  await admin.getByText("تاریخچه دسترسی‌ها", { exact: true }).click();
  await expect(admin.getByText(/لغو شده/)).toBeVisible();
  await a.context.close(); await b.context.close(); await adminContext.close();
});
