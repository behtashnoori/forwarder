import fs from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const customerPassword = process.env.FORWARDER_E2E_CUSTOMER_PASSWORD;
const expertPassword = process.env.FORWARDER_E2E_PASSWORD;
if (!databaseUrl || !fixturePath || !customerPassword || !expertPassword) {
  throw new Error("HW_GEO_008 browser proof requires its owned runtime inputs.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_workspace_phase1_")) {
  throw new Error("HW_GEO_008 browser proof is restricted to its owned disposable database.");
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  portal_customer_email: string;
  usernames: { owner: string };
};

type Country = {
  id: number;
  code: string;
  name: string;
  name_en: string;
  international_locations_available: boolean;
};
type LocationPage = {
  items: Array<{ id: number; name: string; name_en: string }>;
};

const samples = ["IR", "CN", "TR", "TM", "RU", "JP", "KR", "IN", "DE", "FR", "BR", "ZA", "AU"];

async function catalog(page: Page): Promise<Country[]> {
  const response = await page.request.get("/api/countries");
  expect(response.status()).toBe(200);
  const rows = await response.json() as Country[];
  expect(rows).toHaveLength(249);
  expect(new Set(rows.map(row => `${row.id}:${row.code}`)).size).toBe(rows.length);
  for (const code of samples) expect(rows.some(row => row.code === code), code).toBe(true);
  return rows;
}

async function chooseCountry(page: Page, side: "origin" | "destination", country: Country) {
  const search = page.getByLabel(side === "origin" ? "جست‌وجوی کشور مبدأ" : "جست‌وجوی کشور مقصد");
  await search.fill(country.code);
  const control = page.getByRole("combobox").nth(side === "origin" ? 0 : 2);
  await control.click();
  await page.getByRole("option", { name: country.name, exact: true }).click();
  await expect(control).toContainText(country.name);
  return { search, control };
}

async function locations(page: Page, country: Country): Promise<LocationPage["items"]> {
  const response = await page.request.get(
    `/api/international-cities?country_id=${country.id}&paged=1&offset=0&limit=50`,
  );
  expect(response.status()).toBe(200);
  return ((await response.json()) as LocationPage).items;
}

async function loginCustomer(page: Page) {
  await page.goto("/customer");
  await page.locator("#customer-email").fill(fixture.portal_customer_email);
  await page.locator("#customer-password").fill(customerPassword!);
  await page.locator("form").getByRole("button", { name: "ورود" }).click();
  await expect(page).toHaveURL(/\/customer\/requests$/);
}

test.describe.serial("HW_GEO_008 country selection contract", () => {
  test("anonymous intake reaches countries outside corridor coverage without submitting", async ({ page }, testInfo) => {
    const countries = await catalog(page);
    await page.goto("/");
    await page.getByRole("button", { name: "شروع یک حمل جدید" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "ثبت درخواست حمل بین‌المللی" }).click();
    await expect(page.getByRole("heading", { name: "انتخاب مبدا و مقصد بین‌المللی" })).toBeVisible();

    const australia = countries.find(row => row.code === "AU")!;
    const brazil = countries.find(row => row.code === "BR")!;
    expect(australia.international_locations_available).toBe(false);
    expect(brazil.international_locations_available).toBe(false);
    const origin = await chooseCountry(page, "origin", australia);
    await chooseCountry(page, "destination", brazil);
    await expect(page.getByText(/کشور معتبر و انتخاب‌شده است/)).toHaveCount(2);
    await expect(page.getByLabel("انتخاب مکان مبدأ")).toBeDisabled();
    await expect(page.getByLabel("انتخاب مکان مقصد")).toBeDisabled();

    await origin.search.fill("");
    await expect(origin.control).toContainText(australia.name);
    await origin.search.fill("France");
    await origin.control.click();
    await expect(page.getByRole("option", { name: countries.find(row => row.code === "FR")!.name, exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(origin.control).toContainText(australia.name);
    await page.screenshot({ path: testInfo.outputPath("anonymous-complete-country-catalog.png"), fullPage: true });
  });

  test("authenticated Customer selects, retains and submits governed countries unchanged to Expert", async ({ page, browser }, testInfo) => {
    const countries = await catalog(page);
    await loginCustomer(page);
    await page.getByRole("link", { name: "ثبت درخواست جدید" }).click();
    await page.getByRole("button", { name: "ثبت درخواست حمل بین‌المللی" }).click();

    const france = countries.find(row => row.code === "FR")!;
    const unsupported = await chooseCountry(page, "origin", france);
    await expect(page.getByText(/کشور معتبر و انتخاب‌شده است/)).toBeVisible();
    await unsupported.search.fill("");
    await expect(unsupported.control).toContainText(france.name);

    const iran = countries.find(row => row.code === "IR")!;
    const turkey = countries.find(row => row.code === "TR")!;
    expect(iran.international_locations_available).toBe(true);
    expect(turkey.international_locations_available).toBe(true);
    await chooseCountry(page, "origin", iran);
    const iranLocations = await locations(page, iran);
    expect(iranLocations.length).toBeGreaterThan(0);
    await page.getByLabel("انتخاب مکان مبدأ").selectOption(String(iranLocations[0].id));

    await chooseCountry(page, "destination", turkey);
    const turkeyLocations = await locations(page, turkey);
    expect(turkeyLocations.length).toBeGreaterThan(0);
    await page.getByLabel("انتخاب مکان مقصد").selectOption(String(turkeyLocations[0].id));
    await page.getByLabel("شماره تماس").fill("09126666666");
    await page.getByLabel("نحوه انتخاب روش حمل", { exact: true }).click();
    await page.getByRole("option", { name: /انتخاب روش مناسب را به فورواردر می‌سپارم/ }).click();
    await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
    await expect(page.getByText(iran.name, { exact: false }).first()).toBeVisible();
    await expect(page.getByText(turkey.name, { exact: false }).first()).toBeVisible();

    const createdResponse = page.waitForResponse(response =>
      response.request().method() === "POST" && response.url().endsWith("/api/shipment-request"),
    );
    await page.getByRole("button", { name: "تایید و ارسال درخواست" }).click();
    const response = await createdResponse;
    expect(response.status()).toBe(201);
    const created = await response.json() as { request_public_id: string; tracking_code: string };
    await page.screenshot({ path: testInfo.outputPath("authenticated-country-selection-submitted.png"), fullPage: true });

    const expertContext = await browser.newContext({ locale: "fa-IR" });
    const expert = await expertContext.newPage();
    await expert.goto("/");
    await expert.getByRole("button", { name: "ورود به سامانه" }).first().click();
    await expert.getByLabel("نام کاربری").fill(fixture.usernames.owner);
    await expert.getByLabel("رمز عبور").fill(expertPassword!);
    await expert.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
    await expect(expert).not.toHaveURL(/\/$/);
    await expert.goto(`/expert/requests/${created.request_public_id}`);
    await expect(expert.getByRole("heading", { name: created.tracking_code, exact: true })).toBeVisible();
    await expect(expert.getByText(iran.name, { exact: false }).first()).toBeVisible();
    await expect(expert.getByText(turkey.name, { exact: false }).first()).toBeVisible();
    await expert.screenshot({ path: testInfo.outputPath("expert-received-country-identities.png"), fullPage: true });
    await expertContext.close();
  });
});
