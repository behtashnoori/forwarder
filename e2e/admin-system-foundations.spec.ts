import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Use the owned Admin foundations qualification runner");

const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  admin_foundations: {
    catalog_first_created: number;
    catalog_second_created: number;
    profile_first_created: number;
    profile_second_created: number;
    profile_unchanged: number;
  };
};

test.setTimeout(240_000);

async function login(page: Page, persona: "platform" | "dual") {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).toHaveURL(/\/admin/);
}

async function token(page: Page) {
  const value = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(value).toBeTruthy();
  return value!;
}

test("System Admin remains system-only and sees the portable Reference Catalog V1", async ({ browser }, info) => {
  expect(fixture.admin_foundations.catalog_first_created).toBeGreaterThan(0);
  expect(fixture.admin_foundations.catalog_second_created).toBe(0);
  expect(fixture.admin_foundations.profile_first_created).toBeGreaterThan(0);
  expect(fixture.admin_foundations.profile_second_created).toBe(0);
  expect(fixture.admin_foundations.profile_unchanged).toBe(60);

  const context = await browser.newContext({ locale: "fa-IR", viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await login(page, "platform");
  await expect(page.getByText("مدیریت سیستم", { exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "تعاریف استاندارد سیستم", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "دلایل عملیاتی", exact: true })).toHaveCount(0);

  const privateTenantResponse = await page.request.get("/api/admin/logistics-points", {
    headers: { Authorization: `Bearer ${await token(page)}` },
  });
  expect(privateTenantResponse.status()).toBe(403);

  await page.getByRole("tab", { name: "تعاریف استاندارد سیستم", exact: true }).click();
  await page.getByRole("tab", { name: "واحدهای اندازه‌گیری", exact: true }).last().click();
  await expect(page.getByText("میلی‌متر", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "انواع بسته‌بندی", exact: true }).last().click();
  await expect(page.getByText("پالت", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "انواع وسیله حمل", exact: true }).last().click();
  await expect(page.getByText("کامیون / کشنده جاده‌ای", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "تجهیزات و واحدهای بار", exact: true }).last().click();
  await expect(page.getByText("کانتینر ۴۰ فوت High Cube", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("system-admin-reference-catalog-mobile.png"), fullPage: true });
  await context.close();
});

test("explicit dual Admin manages system and own-organization foundations without impersonation", async ({ browser }, info) => {
  const context = await browser.newContext({ locale: "fa-IR" });
  const page = await context.newPage();
  await login(page, "dual");
  await expect(page.getByRole("tab", { name: "تعاریف استاندارد سیستم", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true })).toBeVisible();

  await page.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true }).click();
  await page.getByRole("tab", { name: "انواع بسته‌بندی", exact: true }).last().click();
  const pallet = page.locator("article, [data-slot=card]").filter({ hasText: "پالت" }).first();
  await expect(pallet.getByText("فعال", { exact: true })).toBeVisible();
  await expect(pallet.getByText(/برای حمل و جابه‌جایی/)).toBeVisible();

  await page.getByRole("tab", { name: "کاتالوگ کالا", exact: true }).click();
  await page.getByLabel("کد ثابت کالا").fill("ADMIN_E2E_ENGINE");
  await page.getByLabel("نام فارسی").fill("مجموعه موتور آزمون");
  await page.getByLabel("نام انگلیسی").fill("Qualification engine assembly");
  await page.getByLabel("نوع کالا").selectOption({ index: 1 });
  await page.getByLabel("واحد اندازه‌گیری پیش‌فرض").selectOption({ index: 1 });
  const cargoCreate = page.waitForResponse(response => response.request().method() === "POST" && response.url().includes("/api/admin/cargo-catalog"));
  await page.getByRole("button", { name: "ایجاد کالای استاندارد", exact: true }).click();
  expect((await cargoCreate).status()).toBe(201);
  await expect(page.getByText("مجموعه موتور آزمون", { exact: false })).toBeVisible();

  await page.getByRole("tab", { name: "دلایل عملیاتی", exact: true }).click();
  await page.getByLabel("عنوان دلیل").fill("تأخیر بارگیری آزمون");
  await page.getByLabel("توضیح دلیل").fill("دلیل مصنوعی برای احراز مسیر مدیر سازمان");
  const reasonCreate = page.waitForResponse(response => response.request().method() === "POST" && response.url().includes("/delay-reasons"));
  await page.getByRole("button", { name: "افزودن دلیل", exact: true }).click();
  expect((await reasonCreate).status()).toBe(201);
  const reason = page.locator("article").filter({ hasText: "تأخیر بارگیری آزمون" });
  await expect(reason).toBeVisible();
  await reason.locator("summary", { hasText: "جزئیات فنی" }).click();
  await expect(reason.locator("code")).toHaveText(/^DLR_[0-9A-F]{32}$/);
  await reason.getByRole("button", { name: "غیرفعال کردن", exact: true }).click();
  await expect(reason.getByText("غیرفعال", { exact: true })).toBeVisible();

  await page.getByRole("tab", { name: "SLA سازمان", exact: true }).click();
  await expect(page.getByLabel("فرآیند یا مرحله مورد سنجش")).toHaveValue("EXCEPTION_RESPONSE");
  await expect(page.getByText("ثبت وقوع مشکل", { exact: true })).toBeVisible();
  await expect(page.getByText("رفع مشکل", { exact: true })).toBeVisible();
  await page.getByLabel("مدت رسیدگی به مشکل عملیاتی").fill("120");
  await page.getByLabel("هشدار رسیدگی به مشکل عملیاتی").fill("30");
  const slaCreate = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/organization-sla-rules"));
  await page.getByRole("button", { name: "ثبت تنظیم", exact: true }).click();
  expect((await slaCreate).status()).toBe(201);
  await expect(page.getByText(/فعال · نسخه 1/)).toBeVisible();
  await page.getByLabel("مدت رسیدگی به مشکل عملیاتی").fill("150");
  const slaUpdate = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().includes("/api/organization-sla-rules/"));
  await page.getByRole("button", { name: "ذخیره نسخهٔ جدید", exact: true }).click();
  expect((await slaUpdate).status()).toBe(200);
  await expect(page.getByText(/فعال · نسخه 2/)).toBeVisible();
  await page.getByRole("button", { name: "نمایش تاریخچه", exact: true }).click();
  await expect(page.getByText(/ایجاد/).first()).toBeVisible();

  await page.getByRole("tab", { name: "شبکه لجستیکی سازمان", exact: true }).click();
  await page.getByText("انبار استاندارد آزمون", { exact: true }).click();
  const adoption = page.waitForResponse(response => response.request().method() === "POST" && response.url().includes("/api/admin/global-logistics-points/") && response.url().endsWith("/adopt"));
  await page.getByRole("button", { name: "افزودن به شبکهٔ سازمان", exact: true }).click();
  expect((await adoption).status()).toBe(201);
  await expect(page.getByText("مکان عملیاتی آماده است", { exact: true })).toBeVisible();

  await page.getByLabel("کد ثابت مکان").fill("ADMIN-E2E-PRIVATE-WAREHOUSE");
  await page.getByLabel("نام فارسی مکان").fill("انبار خصوصی آزمون");
  await page.getByLabel("نام انگلیسی مکان").fill("Private Qualification Warehouse");
  await page.getByLabel("نوع مکان سراسری").selectOption({ index: 1 });
  const privateCreate = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/admin/logistics-points"));
  await page.getByRole("button", { name: "ایجاد مکان لجستیکی", exact: true }).click();
  expect((await privateCreate).status()).toBe(201);
  await expect(page.getByText("انبار خصوصی آزمون", { exact: true })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("tab", { name: "تعاریف استاندارد سیستم", exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "کاتالوگ کالا", exact: true }).click();
  await expect(page.getByText("مجموعه موتور آزمون", { exact: false })).toBeVisible();
  await page.screenshot({ path: info.outputPath("dual-admin-foundations.png"), fullPage: true });
  await context.close();
});
