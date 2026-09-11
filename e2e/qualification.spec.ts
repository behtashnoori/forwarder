import { expect, test, type Page } from "@playwright/test";

const password = process.env.FORWARDER_E2E_PASSWORD;

if (!password) {
  throw new Error("FORWARDER_E2E_PASSWORD must be supplied by the local qualification environment.");
}

type BrowserEvidence = { consoleErrors: string[]; pageErrors: string[]; failedRequests: string[]; unexpectedResponses: string[] };

function observe(page: Page, expectedStatuses: number[] = []): BrowserEvidence {
  const evidence: BrowserEvidence = { consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [] };
  page.on("console", message => { if (message.type() === "error") evidence.consoleErrors.push(message.text()); });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => evidence.failedRequests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400 && !expectedStatuses.includes(response.status()))
      evidence.unexpectedResponses.push(`${response.status()} ${response.request().method()} ${response.url()}`);
  });
  return evidence;
}

async function login(page: Page, username: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`personal_analytics_uat_${username}`);
  await page.getByLabel("رمز عبور").fill(password);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.pageErrors, "uncaught browser page errors").toEqual([]);
  expect(evidence.failedRequests, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  expect(evidence.consoleErrors.filter(item => !item.includes("favicon")), "browser console errors").toEqual([]);
}

test.describe.serial("FORWARDER PRODUCT INTEGRATION CORRECTION v1", () => {
  test("A — personal dashboard create, edit, save, navigation and persistence", async ({ page }) => {
    const evidence = observe(page);
    await login(page, "expert_a");
    await page.goto("/operations/shipments");
    await expect(page.getByRole("link", { name: "داشبوردهای من" })).toBeVisible();
    await page.getByRole("link", { name: "داشبوردهای من" }).click();
    await page.getByRole("button", { name: "ایجاد داشبورد شخصی" }).click();
    await expect(page).toHaveURL(/\/dashboards\/[0-9a-f-]+\/edit$/);
    const name = `UAT persistence ${Date.now()}`;
    await page.getByLabel("نام داشبورد").fill(name);
    await page.getByLabel("توضیح").fill("browser qualification persisted change");
    await page.getByRole("button", { name: "ذخیره", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("بدون تغییر");
    await page.getByRole("button", { name: "لغو و بازگشت" }).click();
    await expect(page.getByRole("heading", { name })).toBeVisible();
    await page.getByRole("button", { name: "خانه" }).click();
    await expect(page).toHaveURL(/\/expert$/);
    await page.goto("/operations/shipments");
    await page.getByRole("link", { name: "داشبوردهای من" }).click();
    await page.getByRole("heading", { name }).locator("xpath=ancestor::*[.//a[normalize-space()='باز کردن']][1]").getByRole("link", { name: "باز کردن" }).click();
    await expect(page.getByRole("heading", { name })).toBeVisible();
    expectClean(evidence);
  });

  test("B — dashboard remains usable without Control Tower or Shipment data", async ({ page }) => {
    const evidence = observe(page, [403]);
    await login(page, "dashboard_only");
    await page.goto("/dashboards");
    await expect(page.getByRole("heading", { name: "داشبوردهای من" })).toBeVisible();
    await page.getByRole("button", { name: "ایجاد داشبورد شخصی" }).click();
    await expect(page.getByRole("heading", { name: "ویرایش داشبورد" })).toBeVisible();
    await page.goto("/operations/control-tower");
    await expect(page.getByText("مجوز مشاهده عملیات برای نمایش برج کنترل لازم است.")).toBeVisible();
    await page.goto("/dashboards");
    await page.getByRole("link", { name: "باز کردن" }).first().click();
    await expect(page.getByText("فضای داشبورد در دسترس است، اما ابزارک‌های حمل‌ونقل بدون مجوز زندهٔ مشاهده عملیات داده‌ای نمایش نمی‌دهند.")).toBeVisible();
    await expect(page.getByText("[PA-UAT] O")).toHaveCount(0);
    expectClean(evidence);
  });

  test("C — Control Tower personal copy is listed and reopens", async ({ page }) => {
    const evidence = observe(page);
    await login(page, "expert_b");
    await page.goto("/operations/control-tower");
    await page.getByRole("button", { name: "ایجاد نسخه شخصی" }).click();
    await expect(page).toHaveURL(/\/dashboards\/[0-9a-f-]+$/);
    const targetPath = new URL(page.url()).pathname;
    const name = await page.locator("h1").textContent();
    await page.getByRole("button", { name: "خانه" }).click();
    await page.goto("/operations/shipments");
    await page.getByRole("link", { name: "داشبوردهای من" }).click();
    await expect(page.locator(`a[href="${targetPath}"]`)).toBeVisible();
    await page.locator(`a[href="${targetPath}"]`).click();
    await expect(page.locator("h1")).toHaveText(name || "");
    expectClean(evidence);
  });

  test("D — Saved View snapshot produces an independent TABLE widget", async ({ page }) => {
    const evidence = observe(page);
    await login(page, "expert_a");
    await page.goto("/operations/shipments");
    await page.getByLabel("نمای ذخیره‌شده").selectOption({ label: "[PA-UAT] Expert A shipments" });
    await page.getByLabel("داشبورد شخصی").selectOption({ label: "[PA-UAT] Expert A dashboard" });
    await page.getByRole("button", { name: "افزودن به داشبورد" }).click();
    await expect(page.getByText("نمای ذخیره‌شده با موفقیت ثبت شد.")).toBeVisible();
    await page.getByRole("link", { name: "داشبوردهای من" }).click();
    await page.getByRole("heading", { name: "[PA-UAT] Expert A dashboard" }).locator("xpath=ancestor::*[.//a[normalize-space()='باز کردن']][1]").getByRole("link", { name: "باز کردن" }).click();
    await expect(page.getByRole("heading", { name: "[PA-UAT] Expert A shipments" }).first()).toBeVisible();
    await expect(page.getByRole("table").last()).toBeVisible();
    expectClean(evidence);
  });

  test("E — admin UI exposes only canonical roles and persists Expert scope", async ({ page }) => {
    const evidence = observe(page);
    await login(page, "admin_a");
    await page.goto("/admin");
    await page.getByRole("tab", { name: "مدیریت کاربران" }).click();
    await expect(page.getByRole("heading", { name: "مدیریت کاربران" })).toBeVisible();
    for (const obsolete of ["مدیر CRM", "سرپرست", "کارشناس بازرگانی", "کارشناس بازاریابی"]) await expect(page.getByText(obsolete, { exact: true })).toHaveCount(0);
    const userCard = page.getByText("@personal_analytics_uat_expert_a").locator("xpath=ancestor::*[.//button[normalize-space()='ویرایش']][1]");
    await userCard.getByRole("button", { name: "ویرایش" }).click();
    const dialog = page.getByRole("dialog", { name: "ویرایش کاربر" });
    await expect(dialog.getByText("حمل داخلی", { exact: true })).toBeVisible();
    await expect(dialog.getByText("حمل بین‌المللی", { exact: true })).toBeVisible();
    const domestic = dialog.getByLabel("حمل داخلی");
    const target = !(await domestic.isChecked());
    await domestic.setChecked(target);
    await dialog.getByRole("button", { name: "ذخیره", exact: true }).click();
    await expect(dialog).toBeHidden();
    await userCard.getByRole("button", { name: "ویرایش" }).click();
    await expect(page.getByRole("dialog", { name: "ویرایش کاربر" }).getByLabel("حمل داخلی")).toBeChecked({ checked: target });
    expectClean(evidence);
  });

  test("F — Home, Back and fallback stay inside protected application", async ({ page }) => {
    const evidence = observe(page);
    await login(page, "expert_a");
    await page.goto("/operations/shipments");
    await page.getByRole("link", { name: "داشبوردهای من" }).click();
    await page.getByRole("button", { name: "بازگشت" }).click();
    await expect(page).toHaveURL(/\/operations\/shipments$/);
    await page.getByRole("button", { name: "خانه" }).click();
    await expect(page).toHaveURL(/\/expert$/);
    await page.evaluate(() => sessionStorage.clear());
    await page.goto("/dashboards");
    await page.getByRole("button", { name: "بازگشت" }).click();
    await expect(page).toHaveURL(/\/expert$/);
    expectClean(evidence);
  });
});
