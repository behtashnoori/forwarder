import { expect, test, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { openShipmentSection } from "./helpers/shipment-workspace";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Use the owned Organization Shipment stages runner");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  organization_stage_shipment: string;
  organization_stage_cargo: string;
  p308_geography: { country_id: number; admin1_geoname_id: number; city_geoname_id: number };
};
test.setTimeout(240_000);

async function login(page: Page, persona: "admin" | "restricted" | "foreign") {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}

function local(date: Date) {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function selectDestination(delivery: Locator) {
  await delivery.getByLabel("مقصد تحویل کشور", { exact: true }).selectOption(String(fixture.p308_geography.country_id));
  const province = delivery.getByLabel("مقصد تحویل استان", { exact: true });
  await expect(province.locator(`option[value="${fixture.p308_geography.admin1_geoname_id}"]`)).toHaveCount(1, { timeout: 30_000 });
  await province.selectOption(String(fixture.p308_geography.admin1_geoname_id));
  const city = delivery.getByLabel("مقصد تحویل شهر", { exact: true });
  await expect(city.locator(`option[value="${fixture.p308_geography.city_geoname_id}"]`)).toHaveCount(1, { timeout: 30_000 });
  await city.selectOption(String(fixture.p308_geography.city_geoname_id));
  await delivery.getByLabel("یادداشت مقصد تحویل", { exact: true }).fill("مقصد مصنوعی آزمون مراحل");
}

test("Organization Admin configures projectless stages and Expert closes only after explicit facts", async ({ browser }, testInfo) => {
  const adminContext = await browser.newContext();
  const expertContext = await browser.newContext();
  const foreignContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const expert = await expertContext.newPage();
  const foreign = await foreignContext.newPage();
  const errors: string[] = [];
  for (const page of [admin, expert, foreign]) {
    page.on("pageerror", error => errors.push(error.message));
    await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
    await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  }

  await login(admin, "admin");
  await admin.getByRole("tab", { name: "مراحل محموله", exact: true }).click();
  await expect(admin.getByText("هنوز نسخه فعالی برای مراحل محموله تعریف نشده است.")).toBeVisible();
  await admin.getByRole("button", { name: "تعریف نسخه تازه مراحل" }).click();
  await admin.getByLabel("شروع اعتبار (زمان محلی)").fill(local(new Date(Date.now() - 60_000)));
  const stageConfigured = admin.waitForResponse(response => response.url().endsWith("/shipment-stage-configuration/versions") && response.request().method() === "POST");
  await admin.getByRole("button", { name: "انتشار نسخه مراحل" }).click();
  expect((await stageConfigured).status()).toBe(201);
  await expect(admin.getByText(/نسخه 1/)).toBeVisible();
  await admin.screenshot({ path: testInfo.outputPath("organization-stage-configuration.png"), fullPage: true });

  await admin.getByRole("tab", { name: "قواعد بستن پرونده", exact: true }).click();
  await admin.getByRole("button", { name: "تعریف نسخه V1 قواعد" }).click();
  await admin.getByLabel("شروع اعتبار (زمان محلی)").fill(local(new Date(Date.now() - 60_000)));
  const policyConfigured = admin.waitForResponse(response => response.url().endsWith("/closure-policy/versions") && response.request().method() === "POST");
  await admin.getByRole("button", { name: "ثبت نسخه قواعد" }).click();
  expect((await policyConfigured).status()).toBe(201);
  await expect(admin.getByText(/نسخه 1/)).toBeVisible();

  await login(expert, "restricted");
  await expert.goto(`/operations/shipments/${fixture.organization_stage_shipment}`);
  await openShipmentSection(expert, "closure", fixture.organization_stage_shipment);
  let closure = expert.getByRole("region", { name: "بررسی بستن پرونده" });
  await expect(closure.locator("li", { hasText: "تحویل نهایی محموله به‌صراحت ثبت شده باشد" })).toBeVisible();
  await expect(closure.locator("li", { hasText: "همه مراحل عملیاتی الزامی محموله کامل شده باشند" })).toBeVisible();
  await expect(closure.getByRole("button", { name: "بستن پرونده", exact: true })).toHaveCount(0);

  await openShipmentSection(expert, "stages", fixture.organization_stage_shipment);
  const stages = expert.getByRole("region", { name: "مراحل عملیاتی محموله" });
  await expect(stages.getByText("این زنجیره به پروژه وابسته نیست.", { exact: false })).toBeVisible();
  await expect(stages.locator("ol > li")).toHaveCount(5);
  await stages.getByLabel("زمان رخداد مرحله").fill(local(new Date()));
  for (let index = 0; index < 5; index += 1) {
    const start = stages.locator("button:enabled", { hasText: "شروع مرحله" }).first();
    const started = expert.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/events"));
    await start.click(); expect((await started).status()).toBe(201);
    const complete = stages.locator("button:enabled", { hasText: "تکمیل مرحله" }).first();
    const completed = expert.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/events"));
    await complete.click(); expect((await completed).status()).toBe(201);
  }
  await expect(stages.getByText("کامل‌شده", { exact: false })).toHaveCount(5);

  await openShipmentSection(expert, "closure", fixture.organization_stage_shipment);
  closure = expert.getByRole("region", { name: "بررسی بستن پرونده" });
  await expect(closure.getByRole("button", { name: "بستن پرونده", exact: true })).toHaveCount(0);
  await openShipmentSection(expert, "delivery", fixture.organization_stage_shipment);
  const delivery = expert.getByRole("region", { name: "تحویل کالاها" });
  await delivery.getByRole("button", { name: /تحویل تازه برای/ }).click();
  await delivery.getByLabel("مقدار تحویل", { exact: true }).fill("95");
  await selectDestination(delivery);
  await delivery.getByLabel("زمان وقوع تحویل").fill(local(new Date()));
  await delivery.getByLabel("تحویل نهایی محموله").check();
  const delivered = expert.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/deliveries"));
  await delivery.getByRole("button", { name: "ثبت تحویل", exact: true }).click();
  expect((await delivered).status()).toBe(201);
  await expect(delivery.getByText("تحویل نهایی صریح", { exact: false })).toBeVisible();

  await openShipmentSection(expert, "closure", fixture.organization_stage_shipment);
  closure = expert.getByRole("region", { name: "بررسی بستن پرونده" });
  await expect(closure.getByText("معیارها کامل‌اند؛ اجرای حمل باقی مانده است")).toBeVisible();
  await expect(closure.getByText(/0 مسدودکننده سیاست · 1 پیش‌نیاز چرخه عمر · 3 هشدار/)).toBeVisible();
  await expect(closure.getByRole("link", { name: "رفتن به اجرای مسیر" })).toBeVisible();
  await expect(closure.getByRole("button", { name: "بستن پرونده", exact: true })).toHaveCount(0);
  await expect(closure.getByText("کامل نیست", { exact: true })).toHaveCount(0);
  expect(await closure.getByText("نیازمند توجه", { exact: true }).count()).toBeGreaterThan(0);

  await openShipmentSection(expert, "summary", fixture.organization_stage_shipment);
  const guidance = expert.locator("section[aria-labelledby='guided-operation-heading']");
  await expect(guidance.getByText("ثبت حرکت", { exact: true })).toBeVisible();
  const executionTask = guidance.getByRole("listitem").filter({ hasText: "اجرای حمل" }).first();
  await expect(executionTask).toContainText("نیازمند اقدام");
  await expect(guidance.getByText("اجرای حمل", { exact: true }).last()).toBeVisible();

  await openShipmentSection(expert, "route", fixture.organization_stage_shipment);
  const departed = expert.waitForResponse(response => response.request().method() === "POST" && response.url().includes("/milestones/") && response.url().endsWith("/events"));
  await expert.getByRole("button", { name: "ثبت حرکت", exact: true }).click();
  expect((await departed).status()).toBe(201);
  const arrived = expert.waitForResponse(response => response.request().method() === "POST" && response.url().includes("/milestones/") && response.url().endsWith("/events"));
  await expert.getByRole("button", { name: "ثبت رسیدن", exact: true }).click();
  expect((await arrived).status()).toBe(201);

  await openShipmentSection(expert, "closure", fixture.organization_stage_shipment);
  closure = expert.getByRole("region", { name: "بررسی بستن پرونده" });
  await expect(closure.getByText("آماده بستن عادی")).toBeVisible();
  await expect(closure.getByText(/0 مسدودکننده سیاست · 0 پیش‌نیاز چرخه عمر · 3 هشدار/)).toBeVisible();
  await expect(closure.getByRole("button", { name: "بستن پرونده", exact: true })).toBeEnabled();
  await closure.getByRole("button", { name: "بستن پرونده", exact: true }).click();
  const closed = expert.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/close"));
  await closure.getByRole("button", { name: "تأیید نهایی بستن" }).click();
  expect((await closed).status()).toBe(201);
  await expect(closure.getByText(/پرونده بسته شده است/)).toBeVisible();

  await openShipmentSection(expert, "history", fixture.organization_stage_shipment);
  const history = expert.getByRole("region", { name: "تاریخچه یکپارچه محموله" });
  await history.getByRole("button", { name: "به‌روزرسانی تاریخچه" }).click();
  await expect(history.getByText("مرحله عملیاتی شروع شد", { exact: true }).first()).toBeVisible();
  await expect(history.getByText("مرحله عملیاتی کامل شد", { exact: true }).first()).toBeVisible();
  await expect(history.getByText("تحویل نهایی محموله ثبت شد", { exact: true })).toBeVisible();
  await expect(history.locator("ol > li").filter({ hasText: "رخداد مسیر" })).toHaveCount(2);
  await expect(history.getByText("پرونده بسته شد", { exact: true })).toBeVisible();
  await expert.screenshot({ path: testInfo.outputPath("projectless-stage-history-desktop.png"), fullPage: true });
  await history.getByLabel("دسته‌بندی").selectOption("CLOSURE");
  await expect(history.locator("ol > li")).toHaveCount(1);
  await expect(history.getByText("پرونده بسته شد",{exact:true})).toBeVisible();
  await expect(history.locator("ol > li details")).not.toHaveAttribute("open");
  await expert.screenshot({path:testInfo.outputPath("closure-category-desktop.png"),fullPage:true});
  await openShipmentSection(expert,"summary",fixture.organization_stage_shipment);
  await expect(expert.getByText("کامل بودن اطلاعات",{exact:true}).first()).toBeVisible();
  await expect(expert.getByRole("link",{name:"رفتن به اقدام"})).toHaveCount(0);
  await expert.screenshot({path:testInfo.outputPath("closed-summary-desktop.png"),fullPage:true});
  await openShipmentSection(expert,"documents",fixture.organization_stage_shipment);
  await expect(expert.getByLabel("انتخاب فایل سند")).toHaveCount(0);
  await expect(expert.getByRole("button",{name:"اصلاح سوابق اسناد"})).toBeVisible();
  await expert.screenshot({path:testInfo.outputPath("closed-documents-readonly-desktop.png"),fullPage:true});
  await expert.getByRole("button",{name:"اصلاح سوابق اسناد"}).click();
  await expect(expert.getByLabel("انتخاب فایل سند")).toBeVisible();
  await expert.getByRole("button",{name:"بازگشت به نمایش فقط خواندنی"}).click();
  await expect(expert.getByLabel("انتخاب فایل سند")).toHaveCount(0);
  await openShipmentSection(expert,"history",fixture.organization_stage_shipment);
  await expert.setViewportSize({ width: 390, height: 844 });
  expect(await expert.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await expert.screenshot({ path: testInfo.outputPath("projectless-stage-history-mobile.png"), fullPage: true });

  await login(foreign, "foreign");
  const foreignToken = await foreign.evaluate(() => localStorage.getItem("expert_token"));
  const isolation = await foreign.request.get(`/api/operational-shipments/${fixture.organization_stage_shipment}/operational-stages`, {
    headers: { Authorization: `Bearer ${foreignToken}` },
  });
  expect([403, 404]).toContain(isolation.status());
  expect(errors).toEqual([]);
  await adminContext.close(); await expertContext.close(); await foreignContext.close();
});
