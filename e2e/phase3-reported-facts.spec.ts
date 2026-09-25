import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("P3-07 requires an owned synthetic fixture");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as { p304_shipment: string; p307_units: string[] };
test.setTimeout(180_000);

async function openReports(page: Page) {
  await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  await page.locator(`a[href="/operations/shipments/${fixture.p304_shipment}"]`).click();
  await page.locator("summary", { hasText: "گزارش موقعیت و تغییرات حمل" }).click();
  return page.getByRole("region", { name: "گزارش‌های موقعیت و تغییرات حمل" });
}

test("P3-07 normal Chrome report, two scoped units, correction and reopen", async ({ page }) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill("shared_transport_e2e_restricted");
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  let reports = await openReports(page);
  for (const [index, source] of ["CARRIER_REPORT", "DRIVER_REPORT"].entries()) {
    await reports.getByRole("button", { name: "گزارش تازه" }).click();
    await reports.getByLabel("منبع گزارش").selectOption(source);
    await reports.getByLabel("بخش مربوط به گزارش").selectOption(fixture.p307_units[index]);
    await reports.getByLabel("زمان وقوع گزارش").fill("2026-09-20T10:30");
    await reports.getByLabel("موقعیت گزارش‌شده", { exact: true }).fill(index ? "نزدیک مرز دوم" : "نزدیک مرز اول");
    await reports.getByLabel("یادداشت داخلی گزارش").fill("یادداشت داخلی آزمایشی");
    const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/reported-facts"));
    await reports.getByRole("button", { name: "ثبت گزارش", exact: true }).click();
    expect((await saved).status()).toBe(201);
    await expect(reports.getByRole("button", { name: "گزارش تازه" })).toBeVisible();
  }
  await expect(reports.getByText("آخرین موقعیت گزارش‌شده: نزدیک مرز اول", { exact: true })).toBeVisible();
  await expect(reports.getByText("آخرین موقعیت گزارش‌شده: نزدیک مرز دوم", { exact: true })).toBeVisible();
  const first = reports.locator("article[data-report-id]").filter({ hasText: "نزدیک مرز اول" });
  await first.getByRole("button", { name: "اصلاح گزارش" }).click();
  await reports.getByLabel("موقعیت گزارش‌شده", { exact: true }).fill("مرز اصلاح‌شده");
  await reports.getByLabel("دلیل اصلاح گزارش").fill("اصلاح نشانی گزارش اولیه");
  await reports.getByRole("button", { name: "ثبت اصلاح گزارش", exact: true }).click();
  await expect(reports.getByText("اصلاح ثبت شد؛ اصل گزارش در سابقه محفوظ است.")).toBeVisible();
  reports = await openReports(page);
  await expect(reports.getByText("آخرین موقعیت گزارش‌شده: مرز اصلاح‌شده", { exact: true })).toBeVisible();
  await expect(reports.getByText("آخرین موقعیت گزارش‌شده: نزدیک مرز دوم", { exact: true })).toBeVisible();
  await expect(reports.getByText("اصلاح‌شده؛ محفوظ در سابقه", { exact: true })).toBeVisible();
  await expect(reports.getByText("دلیل اصلاح: اصلاح نشانی گزارش اولیه", { exact: true })).toBeVisible();
  await expect(reports.locator("article[data-report-id]")).toHaveCount(3);
  await reports.evaluate(node => node.scrollIntoView({ block: "start" }));
  await page.evaluate(() => window.scrollBy(0, -180));
  await page.screenshot({ path: test.info().outputPath("reported-facts-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await reports.evaluate(node => node.scrollIntoView({ block: "start" }));
  await page.evaluate(() => window.scrollBy(0, -180));
  await page.screenshot({ path: test.info().outputPath("reported-facts-mobile.png") });
  expect(errors).toEqual([]);
});
