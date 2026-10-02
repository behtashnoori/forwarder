import fs from "node:fs";
import { expect, test, type Browser, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL || "";
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH || "";
const customerPassword = process.env.FORWARDER_E2E_CUSTOMER_PASSWORD || "";
const expertPassword = process.env.FORWARDER_E2E_PASSWORD || "";
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_workspace_phase1_customer_location_browser_") || !fixturePath || !customerPassword || !expertPassword) {
  throw new Error("HW_GEO_009 requires its owned disposable browser runtime.");
}
const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  portal_customer_email: string;
  usernames: { owner: string; peer: string; empty: string };
};
test.setTimeout(180_000);

type Country = { id: number; code: string; name: string };
type City = { source_id: number; name_fa: string; name_en: string };

async function countries(page: Page) {
  const response = await page.request.get("/api/countries");
  expect(response.status()).toBe(200);
  const rows = await response.json() as Country[];
  expect(rows).toHaveLength(249);
  return rows;
}

async function enterInternational(page: Page, authenticated = false) {
  if (authenticated) {
    await page.goto("/customer");
    await page.locator("#customer-email").fill(fixture.portal_customer_email);
    await page.locator("#customer-password").fill(customerPassword);
    await page.locator("form").getByRole("button", { name: "ورود" }).click();
    await expect(page).toHaveURL(/\/customer\/requests$/);
    await page.getByRole("link", { name: "ثبت درخواست جدید" }).click();
  } else {
    await page.goto("/");
    await page.getByRole("button", { name: "شروع یک حمل جدید" }).click();
  }
  await page.getByRole("button", { name: "ثبت درخواست حمل بین‌المللی" }).click();
  await expect(page.getByRole("heading", { name: "انتخاب مبدا و مقصد بین‌المللی" })).toBeVisible();
}

async function chooseCountry(page: Page, side: "origin" | "destination", country: Country) {
  const search = page.getByLabel(side === "origin" ? "جست‌وجوی کشور مبدأ" : "جست‌وجوی کشور مقصد");
  await search.fill(country.code);
  const select = page.getByRole("combobox").nth(side === "origin" ? 0 : 2);
  await select.click();
  await page.getByRole("option", { name: country.name, exact: true }).click();
}

async function chooseCity(page: Page, side: "origin" | "destination", name: string) {
  await page.getByLabel(side === "origin" ? "جست‌وجوی شهر مبدأ" : "جست‌وجوی شهر مقصد").fill(name);
  const select = page.getByLabel(side === "origin" ? "انتخاب شهر مبدأ" : "انتخاب شهر مقصد");
  const exactEnglishName = new RegExp(`·\\s*${name.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}\\s*·`);
  const option = select.locator("option").filter({ hasText: exactEnglishName });
  await expect(option).toHaveCount(1);
  await select.selectOption(await option.getAttribute("value") || "");
}

async function suggestionAndPhone(page: Page, phone: string) {
  await page.getByLabel("شماره تماس").fill(phone);
  await page.getByLabel("نحوه انتخاب روش حمل", { exact: true }).click();
  await page.getByRole("option", { name: /انتخاب روش مناسب را به فورواردر می‌سپارم/ }).click();
}

function usernameForAssignee(fullName: string) {
  const key = ({
    "کارشناس مالک ثابت": "owner",
    "کارشناس ارجاع جدید": "peer",
    "کارشناس بدون محموله": "empty",
  } as const)[fullName];
  if (!key) throw new Error(`Unexpected seeded assignee: ${fullName}`);
  return fixture.usernames[key];
}

async function loginExpert(browser: Browser, username: string) {
  const context = await browser.newContext({ locale: "fa-IR" });
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور").fill(expertPassword);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
  return { context, page };
}

test.describe.serial("HW_GEO_009 Customer Request location contract", () => {
  test("anonymous intake reaches canonical cities, clears stale country values, and reviews a declared place", async ({ page }, info) => {
    const rows = await countries(page);
    const china = rows.find(row => row.code === "CN")!;
    const iran = rows.find(row => row.code === "IR")!;
    const brazil = rows.find(row => row.code === "BR")!;
    await enterInternational(page);
    await chooseCountry(page, "origin", china);
    await chooseCity(page, "origin", "Beijing");
    await chooseCountry(page, "destination", iran);
    await chooseCity(page, "destination", "Bandar Abbas");
    await chooseCountry(page, "destination", brazil);
    await expect(page.getByLabel("انتخاب شهر مقصد")).toHaveValue("");
    await page.getByRole("button", { name: "محل موردنظر در فهرست نیست" }).nth(1).click();
    await page.getByLabel("نام شهر یا محل موردنظر مقصد").fill("Santos customer warehouse");
    await suggestionAndPhone(page, "09121111111");
    await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
    await expect(page.getByText(/Santos customer warehouse/)).toBeVisible();
    await expect(page.getByText(/محل اعلام‌شده مشتری؛ نیازمند بررسی کارشناس/)).toBeVisible();
    await page.screenshot({ path: info.outputPath("anonymous-declared-review.png"), fullPage: true });
  });

  test("authenticated canonical China to Iran request survives Customer and Expert detail", async ({ page, browser }, info) => {
    const rows = await countries(page);
    await enterInternational(page, true);
    await chooseCountry(page, "origin", rows.find(row => row.code === "CN")!);
    await chooseCity(page, "origin", "Beijing");
    await chooseCountry(page, "destination", rows.find(row => row.code === "IR")!);
    await chooseCity(page, "destination", "Bandar Abbas");
    await suggestionAndPhone(page, "09122222222");
    await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
    const posted = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/shipment-request"));
    await page.getByRole("button", { name: "تایید و ارسال درخواست" }).click();
    const response = await posted; expect(response.status()).toBe(201);
    const body = await response.json() as { request_public_id: string; customer_workspace_path: string; tracking_code: string; assigned_expert: { display_name: string } };
    await page.goto(body.customer_workspace_path);
    await page.getByText("جزئیات درخواست", { exact: true }).click();
    await expect(page.getByText("پکن", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("بندرعباس", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("مکان مرجع انتخاب‌شده", { exact: true })).toHaveCount(2);
    const expert = await loginExpert(browser, usernameForAssignee(body.assigned_expert.display_name));
    await expert.page.goto(`/expert/requests/${body.request_public_id}`);
    await expect(expert.page.getByRole("heading", { name: body.tracking_code })).toBeVisible();
    await expect(expert.page.getByText("مکان مرجع انتخاب‌شده", { exact: true })).toHaveCount(2);
    await expert.page.screenshot({ path: info.outputPath("expert-canonical-request.png"), fullPage: true });
    await expert.context.close();
  });

  test("declared Brazil destination persists and legacy airport remains separately typed", async ({ page, browser }, info) => {
    const rows = await countries(page);
    const china = rows.find(row => row.code === "CN")!;
    const brazil = rows.find(row => row.code === "BR")!;
    const iran = rows.find(row => row.code === "IR")!;
    await enterInternational(page, true);
    await chooseCountry(page, "origin", china); await chooseCity(page, "origin", "Beijing");
    await chooseCountry(page, "destination", iran);
    await page.getByRole("button", { name: "فرودگاه یا بندر" }).nth(1).click();
    const physical = page.getByLabel("انتخاب نقطه مرجع مقصد");
    const airport = physical.getByRole("option", { name: /فرودگاه امام خمینی/ });
    await expect(airport).toBeAttached();
    await physical.selectOption(await airport.getAttribute("value") || "");
    await expect(page.getByText("فرودگاه و بندر جدا از شهر ثبت می‌شوند.")).toBeVisible();
    await chooseCountry(page, "destination", brazil);
    await page.getByRole("button", { name: "محل موردنظر در فهرست نیست" }).nth(1).click();
    await page.getByLabel("نام شهر یا محل موردنظر مقصد").fill("Santos customer warehouse");
    await suggestionAndPhone(page, "09123333333");
    await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
    const posted = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/shipment-request"));
    await page.getByRole("button", { name: "تایید و ارسال درخواست" }).click();
    const response = await posted; expect(response.status()).toBe(201);
    const body = await response.json() as { request_public_id: string; customer_workspace_path: string; tracking_code: string; assigned_expert: { display_name: string } };
    await page.goto(body.customer_workspace_path);
    await page.getByText("جزئیات درخواست", { exact: true }).click();
    await expect(page.getByText("Santos customer warehouse", { exact: false })).toBeVisible();
    await expect(page.getByText("محل اعلام‌شده مشتری؛ هنوز به مکان مرجع متصل نیست", { exact: true })).toBeVisible();
    const expert = await loginExpert(browser, usernameForAssignee(body.assigned_expert.display_name));
    await expert.page.goto(`/expert/requests/${body.request_public_id}`);
    await expect(expert.page.getByText("Santos customer warehouse", { exact: false })).toBeVisible();
    await expect(expert.page.getByText("محل اعلام‌شده مشتری؛ هنوز به مکان مرجع متصل نیست", { exact: true })).toBeVisible();
    const customerSession = await (await page.request.get("/api/customer/session")).json() as { csrf_token: string };
    const invalid = await page.request.post("/api/shipment-request", { headers: { "X-CSRF-Token": customerSession.csrf_token }, data: {
      shipping_type: "international", contact_phone: "09124444444", transport_method_preference: "forwarder_suggestion",
      origin_country_id: china.id, origin_location: { kind: "canonical_city", source_id: (await (await page.request.get("/api/geography/cities?country_code=IR&q=Tehran&limit=1")).json() as { items: City[] }).items[0].source_id },
      dest_country_id: brazil.id, destination_location: { kind: "declared", description: "Santos" },
    }});
    expect(invalid.status()).toBe(400);
    expect((await invalid.json() as { error: { code: string } }).error.code).toBe("LOCATION_COUNTRY_MISMATCH");
    await expert.page.screenshot({ path: info.outputPath("expert-declared-request.png"), fullPage: true });
    await expert.context.close();
  });
});
