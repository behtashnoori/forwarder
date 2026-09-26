import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Use the owned P3-13 runner");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p313_shipment: string; p313_target_id: number; p313_target_label: string;
  p309_documents: Record<string, string>; p309_accounts: Record<string, {email: string}>;
};
test.setTimeout(180_000);
async function login(page: Page, persona: string) {
  await page.goto("/"); await page.getByRole("button", {name: "ورود به سامانه"}).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", {name: "ورود", exact: true}).click();
  await expect(page).not.toHaveURL(/\/$/);
}
async function openShipment(page: Page) {
  await page.goto("/operations/shipments");
  await page.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`).click();
  await expect(page.getByRole("heading", {name: "خلاصه محموله", exact: true})).toBeVisible();
}
async function ownership(page: Page) {
  await page.locator("summary", {hasText: "مسئول و سابقه انتقال"}).click();
  return page.getByRole("region", {name: "مسئول و سابقه انتقال"});
}
async function request(page: Page, path: string, method = "GET", body?: unknown, key?: string) {
  return page.evaluate(async ({path, method, body, key}) => {
    const token = localStorage.getItem("expert_token");
    const response = await fetch(path, {method, headers: {
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
      ...(body ? {"Content-Type": "application/json"} : {}), ...(key ? {"Idempotency-Key": key} : {}),
    }, ...(body ? {body: JSON.stringify(body)} : {})});
    return {status: response.status, text: await response.text()};
  }, {path, method, body, key});
}

test("P3-13 Admin transfer changes live Expert access and preserves Customer document scope", async ({browser}, testInfo) => {
  const contexts = await Promise.all(Array.from({length: 4}, () => browser.newContext()));
  const [admin, old, next, customer] = await Promise.all(contexts.map(context => context.newPage()));
  const errors: string[] = [];
  for (const page of [admin, old, next, customer]) {
    page.on("pageerror", error => errors.push(error.message));
    await page.route("https://fonts.googleapis.com/**", route => route.fulfill({status: 200, contentType: "text/css", body: ""}));
    await page.route("https://fonts.gstatic.com/**", route => route.fulfill({status: 204, body: ""}));
  }
  await login(old, "restricted"); await openShipment(old);
  const root = `/api/operational-shipments/${fixture.p313_shipment}`;
  const documents = `/api/internal/operational-shipments/${fixture.p313_shipment}/documents`;
  const download = `${documents}/${fixture.p309_documents.a}/download`;
  const originalFile = await request(old, download); expect(originalFile.status).toBe(200);
  const originalDocuments = await request(old, documents); expect(originalDocuments.status).toBe(200);
  await login(next, "transfer_target"); await next.goto("/operations/shipments");
  await expect(next.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`)).toHaveCount(0);
  await customer.goto("/customer");
  await customer.locator("#customer-email").fill(fixture.p309_accounts.a.email);
  await customer.locator("#customer-password").fill(password!);
  await customer.locator("form button").first().click(); await expect(customer).toHaveURL(/\/customer\/requests/);
  await customer.getByRole("link", {name: "حمل‌های من", exact: true}).click();
  await customer.locator(`a[href="/customer/shipments/${fixture.p313_shipment}"]`).click();
  const customerFile = await request(customer, `/api/customer/documents/${fixture.p309_documents.a}/download`);
  expect(customerFile.status).toBe(200);

  await login(admin, "admin"); await openShipment(admin);
  let region = await ownership(admin);
  await expect(region.getByText(/کارهای بازِ مسئول فعلی/)).toContainText("1");
  await expect(region.getByRole("button", {name: "بررسی انتقال مسئول"})).toBeDisabled();
  await region.getByLabel("کارشناس مسئول جدید").selectOption(String(fixture.p313_target_id));
  await region.getByLabel("دلیل انتقال (الزامی)").fill("PRIVATE-OWNER-TRANSFER-REASON");
  await region.getByRole("button", {name: "بررسی انتقال مسئول"}).click();
  await expect(region.getByRole("group", {name: "تأیید انتقال مسئول"})).toContainText(fixture.p313_target_label);
  await admin.screenshot({path: testInfo.outputPath("owner-transfer-admin-confirm.png"), fullPage: true});
  const submitted = admin.waitForRequest(value => value.url().endsWith("/owner-transfers") && value.method() === "POST");
  const transferred = admin.waitForResponse(value => value.url().endsWith("/owner-transfers") && value.request().method() === "POST");
  await region.getByRole("button", {name: "تأیید نهایی انتقال"}).click();
  expect((await transferred).status()).toBe(201);
  const command = await submitted;
  const payload = command.postDataJSON(); const key = command.headers()["idempotency-key"];
  await expect(admin.getByText(fixture.p313_target_label, {exact: true}).first()).toBeVisible();
  const replay = await request(admin, `${root}/owner-transfers`, "POST", payload, key);
  expect(replay.status).toBe(200); expect(JSON.parse(replay.text).data.created).toBe(false);
  expect((await request(admin, `${root}/owner-transfers`, "POST", {...payload, actor_user_id: 999}, "forged-actor")).status).toBe(422);
  expect((await request(next, `${root}/owner-transfers`, "POST", payload, "ordinary-expert")).status).toBe(403);

  await old.bringToFront(); await old.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(old.getByRole("heading", {name: "خلاصه محموله", exact: true})).toHaveCount(0);
  await expect(old.getByRole("alert").first()).toContainText("دسترس نیست");
  expect((await request(old, download)).status).toBe(404);
  expect((await request(old, `${root}/owner-transfers`)).status).toBe(404);
  await old.goto("/operations/shipments");
  await expect(old.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`)).toHaveCount(0);
  for (const [url, api] of [["/operations", "/api/operational-workspace"], ["/operations/control-tower", "/api/control-tower/shipments"]]) {
    const loaded = old.waitForResponse(response => new URL(response.url()).pathname === api && response.request().method() === "GET");
    await old.goto(url); const response = await loaded; expect(response.status()).toBe(200);
    expect(JSON.stringify(await response.json())).not.toContain(fixture.p313_shipment);
    await expect(old.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`)).toHaveCount(0);
  }

  await next.bringToFront(); await next.evaluate(() => window.dispatchEvent(new Event("focus")));
  await next.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`).click();
  const currentFile = await request(next, download); expect(currentFile).toEqual(originalFile);
  const currentDocuments = await request(next, documents);
  expect(JSON.parse(currentDocuments.text).data).toEqual(JSON.parse(originalDocuments.text).data);
  expect(JSON.parse(currentDocuments.text).can_manage_documents).toBe(true);
  expect(JSON.parse((await request(admin, documents)).text).can_manage_documents).toBe(false);
  region = await ownership(next);
  await expect(region.getByText("PRIVATE-OWNER-TRANSFER-REASON", {exact: false})).toBeVisible();
  await expect(region.getByLabel("کارشناس مسئول جدید")).toHaveCount(0);
  await next.setViewportSize({width: 390, height: 844}); await region.scrollIntoViewIfNeeded();
  expect(await next.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await next.screenshot({path: testInfo.outputPath("owner-transfer-new-owner-mobile.png"), fullPage: true});
  await next.reload(); region = await ownership(next);
  await expect(region.getByText("PRIVATE-OWNER-TRANSFER-REASON", {exact: false})).toBeVisible();
  const history = JSON.parse((await request(admin, `${root}/owner-transfers`)).text).data;
  expect(history.transfers).toHaveLength(1); expect(history.transfers[0].new_owner.id).toBe(fixture.p313_target_id);
  expect(history.initial_owner.occurred_at).toBeNull();
  for (const [url, api] of [["/operations", "/api/operational-workspace"], ["/operations/control-tower", "/api/control-tower/shipments"]]) {
    const loaded = next.waitForResponse(response => new URL(response.url()).pathname === api && response.request().method() === "GET");
    await next.goto(url); const response = await loaded; expect(response.status()).toBe(200);
    expect(JSON.stringify(await response.json())).toContain(fixture.p313_shipment);
    await expect(next.locator(`a[href="/operations/shipments/${fixture.p313_shipment}"]`).first()).toBeVisible();
  }
  await openShipment(next);
  await next.locator("summary", {hasText: "جزئیات عملیاتی بیشتر"}).click();
  await next.getByLabel("نوع یا دسته تجاری سند", {exact: true}).fill("PRIVATE-NEW-OWNER-DOCUMENT");
  await next.getByLabel("انتخاب فایل سند").setInputFiles({name: "new-owner.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF")});
  const uploaded = next.waitForResponse(response => new URL(response.url()).pathname === documents && response.request().method() === "POST");
  await next.getByRole("button", {name: "بارگذاری سند", exact: true}).click();
  expect((await uploaded).status()).toBe(201);
  await expect(next.getByText("new-owner.pdf: ثبت شد", {exact: true})).toBeVisible();
  expect(await request(next, download)).toEqual(originalFile);
  await customer.reload();
  await expect(customer.getByRole("heading", {name: "کالاهای من", exact: true})).toBeVisible();
  await expect(customer.getByText("قطعات موتور", {exact: true}).first()).toBeVisible();
  await expect(customer.locator("body")).not.toContainText("PRIVATE");
  await expect(customer.getByText("PRIVATE-OWNER-TRANSFER-REASON", {exact: false})).toHaveCount(0);
  expect(await request(customer, `/api/customer/documents/${fixture.p309_documents.a}/download`)).toEqual(customerFile);
  expect((await request(customer, `/api/customer/documents/${fixture.p309_documents.b}/download`)).status).toBe(404);
  expect((await request(customer, `${root}/owner-transfers`)).status).toBe(401);
  await customer.screenshot({path: testInfo.outputPath("owner-transfer-customer-unchanged.png"), fullPage: true});
  expect(errors).toEqual([]);
  for (const context of contexts) await context.close();
});
