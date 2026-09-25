import { expect, test, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("P3-05 browser test requires an owned synthetic fixture.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p304_shipment: string; p305_cargo: string; p305_first: string; p305_second: string; p305_third: string; tenant_b_cargo: string;
};
test.setTimeout(180_000);

async function openShipment(page: Page) {
  await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  await page.locator(`a[href="/operations/shipments/${fixture.p304_shipment}"]`).click();
  await expect(page.getByRole("heading", { name: "خلاصه محموله" })).toBeVisible();
}

async function openTrace(page: Page): Promise<Locator> {
  const details = page.locator("details").filter({ has: page.locator("summary", { hasText: "تخصیص و مسیر هر کالا" }) }).first();
  if (!(await details.getAttribute("open"))) await details.locator("summary").click();
  await expect(details.getByRole("heading", { name: "تخصیص و مسیر هر کالا" })).toBeVisible();
  await expect(details.getByLabel("کالا برای ردگیری")).toHaveValue(fixture.p305_cargo);
  return details;
}

async function save(page: Page, trace: Locator, stage: string, dimension: "PLANNED" | "ACTUAL", quantity: string, reason = "") {
  await trace.getByLabel("اجرای حمل برای تخصیص").selectOption(stage);
  await trace.getByLabel("نوع تخصیص").selectOption(dimension);
  await trace.getByLabel("مقدار تخصیص مرحله").fill(quantity);
  await trace.getByLabel("دلیل اصلاح تخصیص").fill(reason);
  const response = page.waitForResponse(item => item.request().method() === "PUT" && item.url().includes(`/stage-executions/${stage}/allocation`));
  await trace.getByRole("button", { name: "ذخیره تخصیص" }).click();
  expect((await response).status()).toBe(201);
  await expect(trace.getByText(/تخصیص ثبت شد؛ اختلاف‌ها فقط هشدار هستند/)).toBeVisible();
}

test("P3-05 — normal Chrome Cargo plan, actual, correction, transfer and reopen", async ({ page }) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", item => { if (item.type() === "error" && !item.text().includes("favicon")) errors.push(item.text()); });
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill("shared_transport_e2e_restricted");
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await openShipment(page);
  let trace = await openTrace(page);
  await save(page, trace, fixture.p305_first, "PLANNED", "60");
  await save(page, trace, fixture.p305_second, "PLANNED", "40");
  await expect(trace.getByText(/جمع برنامه:.*100/).first()).toBeVisible();
  await openShipment(page);
  trace = await openTrace(page);
  await expect(trace.getByText(/جمع برنامه:.*100/).first()).toBeVisible();

  await save(page, trace, fixture.p305_second, "PLANNED", "30", "برنامه تازه");
  await expect(trace.getByText(/10 کارتن در برنامه این بخش هنوز تخصیص ندارد/)).toBeVisible();
  await save(page, trace, fixture.p305_second, "PLANNED", "50", "بار اضافی برنامه");
  await expect(trace.getByText(/10 کارتن بالاتر از مقدار برنامه‌ریزی‌شده تخصیص داده شده است/)).toBeVisible();
  await save(page, trace, fixture.p305_first, "ACTUAL", "55");
  await save(page, trace, fixture.p305_second, "ACTUAL", "40");
  await expect(trace.getByText(/جمع واقعی:.*95/).first()).toBeVisible();
  await save(page, trace, fixture.p305_first, "ACTUAL", "50", "بازشماری");
  await save(page, trace, fixture.p305_first, "ACTUAL", "48", "مقدار تأییدشده");
  await expect(trace.getByText(/جمع واقعی:.*88/).first()).toBeVisible();
  await trace.locator("summary", { hasText: "تاریخچه تخصیص و انتقال" }).click();
  await expect(trace.getByText("مقدار تأییدشده")).toBeVisible();
  await expect(trace.getByText(/50 ← 48/)).toBeVisible();

  await trace.getByLabel("اجرای مبدأ انتقال").selectOption(fixture.p305_first);
  await trace.getByLabel("اجرای مقصد انتقال").selectOption(fixture.p305_second);
  await trace.getByLabel("مقدار انتقال").fill("20");
  await trace.getByLabel("محل یا زمینه انتقال").fill("خورگوس");
  const transferResponse = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith("/allocation-transfers"));
  await trace.getByRole("button", { name: "ثبت انتقال کالا" }).click();
  expect((await transferResponse).status()).toBe(201);
  await expect(trace.getByText(/جمع واقعی:.*88/).first()).toBeVisible();
  await save(page, trace, fixture.p305_third, "ACTUAL", "95");
  await expect(trace.getByText(/جمع واقعی:.*95/).last()).toBeVisible();
  await expect(trace.getByText(/از بخش قبل هنوز در این بخش ثبت نشده است|بیشتر از بخش قبل در این بخش ثبت شده است/)).toBeVisible();

  const cargoDetails = page.locator("details").filter({ has: page.locator("summary", { hasText: "جزئیات کالا، وسیله حمل و پیگیری" }) }).first();
  await cargoDetails.locator("summary").first().click();
  const cargoArticle = cargoDetails.locator("article").filter({ hasText: "قطعات موتور" }).first();
  await cargoArticle.locator("summary", { hasText: "تکمیل یا اصلاح اطلاعات" }).click();
  await cargoArticle.getByLabel("Edit planned quantity line 1").fill("95");
  await cargoArticle.getByLabel("Edit cargo reason line 1").fill("مشتری مقدار برنامه را کم کرد");
  const planRevision = page.waitForResponse(item => item.request().method() === "PATCH" && item.url().endsWith(`/cargo-items/${fixture.p305_cargo}`));
  await cargoArticle.getByRole("button", { name: "ذخیره اطلاعات کالا" }).click();
  expect((await planRevision).status()).toBe(200);
  await cargoArticle.getByRole("button", { name: "تاریخچه برنامه و مقدار واقعی" }).click();
  await expect(cargoArticle.getByText(/برنامه: 100.*95/)).toBeVisible();
  await expect(cargoArticle.getByText(/مشتری مقدار برنامه را کم کرد/)).toBeVisible();
  await cargoArticle.getByLabel("Edit actual quantity line 1").fill("115");
  await cargoArticle.getByLabel("Edit cargo reason line 1").fill("بازشماری کل کالا");
  const actualCorrection = page.waitForResponse(item => item.request().method() === "PATCH" && item.url().endsWith(`/cargo-items/${fixture.p305_cargo}`));
  await cargoArticle.getByRole("button", { name: "ذخیره اطلاعات کالا" }).click();
  expect((await actualCorrection).status()).toBe(200);
  await cargoArticle.getByRole("button", { name: "تاریخچه برنامه و مقدار واقعی" }).click();
  await expect(cargoArticle.getByText(/مقدار واقعی: 95.*115/)).toBeVisible();
  await expect(cargoArticle.getByText(/بازشماری کل کالا/)).toBeVisible();
  await trace.getByRole("button", { name: "تازه‌سازی" }).click();
  await expect(trace.getByText(/مقدار واقعی شناخته‌شده:.*115/)).toBeVisible();
  await save(page, trace, fixture.p305_third, "ACTUAL", "105", "ثبت واقعی بیش از برنامه");
  await expect(trace.getByText(/جمع واقعی:.*105/).last()).toBeVisible();
  await expect(trace.getByText(/مقدار واقعی این بخش 10 کارتن بیشتر از برنامه است/).last()).toBeVisible();
  const ownerToken = await page.evaluate(() => localStorage.getItem("expert_token"));
  const ownerHeaders = { Authorization: `Bearer ${ownerToken}`, "Content-Type": "application/json" };
  const exceptions = await page.request.get(`/api/operational-shipments/${fixture.p304_shipment}/route-exceptions?status=open`, { headers: ownerHeaders });
  expect(exceptions.status()).toBe(200);
  expect(((await exceptions.json()) as { data: unknown[] }).data).toEqual([]);
  const foreignCargo = await page.request.get(`/api/internal/operational-shipments/${fixture.p304_shipment}/cargo-items/${fixture.tenant_b_cargo}/allocation-trace`, { headers: ownerHeaders });
  expect(foreignCargo.status()).toBe(404);
  for (const persona of ["admin", "foreign"]) {
    const login = await page.request.post("/api/expert/auth/login", { data: { username: `shared_transport_e2e_${persona}`, password } });
    expect(login.status()).toBe(200);
    const token = ((await login.json()) as { tokens: { access_token: string } }).tokens.access_token;
    const denied = await page.request.put(`/api/internal/operational-shipments/${fixture.p304_shipment}/cargo-items/${fixture.p305_cargo}/stage-executions/${fixture.p305_first}/allocation`, { headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": `p305-browser-denied-${persona}` }, data: { dimension: "PLANNED", quantity: "1", expected_version: 1 } });
    expect([403, 404]).toContain(denied.status());
  }
  const guessed = await page.request.put(`/api/internal/operational-shipments/${fixture.p304_shipment}/cargo-items/${fixture.p305_cargo}/stage-executions/00000000-0000-4000-8000-000000000000/allocation`, { headers: { ...ownerHeaders, "Idempotency-Key": "p305-browser-guessed" }, data: { dimension: "PLANNED", quantity: "1", expected_version: 0 } });
  expect(guessed.status()).toBe(404);
  await openShipment(page);
  trace = await openTrace(page);
  await expect(trace.getByText("WAGON-7").first()).toBeVisible();
  await expect(trace.getByText(/جمع واقعی:.*95/).last()).toBeVisible();
  expect(errors).toEqual([]);
});
