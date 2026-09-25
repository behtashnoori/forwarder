import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("P3-01 qualification must use its disposable local runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as { shipment_a: string };
test.setTimeout(120_000);

type Evidence = { console: string[]; page: string[]; failed: string[]; unexpected: string[] };
function observe(page: Page): Evidence {
  const result: Evidence = { console: [], page: [], failed: [], unexpected: [] };
  page.on("console", item => {
    if (item.type() === "error" && !item.text().includes("favicon")) {
      result.console.push(`${item.text()} @ ${item.location().url || "unknown"}`);
    }
  });
  page.on("pageerror", error => result.page.push(error.message));
  page.on("requestfailed", request => result.failed.push(`${request.method()} ${request.url()}`));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      result.unexpected.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  return result;
}
function clean(result: Evidence) {
  expect(result.unexpected, "unexpected API failures").toEqual([]);
  expect(result.failed, "unexpected failed requests").toEqual([]);
  expect(result.page, "unexpected page errors").toEqual([]);
  expect(result.console, "unexpected console errors").toEqual([]);
}

async function login(page: Page, persona: "platform" | "admin" | "restricted" | "foreign") {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "خروج", exact: true }).first().click();
  await expect(page).toHaveURL(/\/$/);
}

const definitions = [
  { tab: "انواع کالا", code: "P3E2E_CARGO", fa: "کالای مرجع پی‌سه", en: "P3 reference cargo" },
  { tab: "واحدهای اندازه‌گیری", code: "P3E2E_UOM", fa: "واحد مرجع پی‌سه", en: "P3 reference unit", symbol: "P3U" },
  { tab: "انواع بسته‌بندی", code: "P3E2E_PACKAGE", fa: "بسته مرجع پی‌سه", en: "P3 reference package" },
  { tab: "انواع وسیله حمل", code: "P3E2E_MEANS", fa: "وسیله مرجع پی‌سه", en: "P3 reference means" },
  { tab: "تجهیزات و واحدهای بار", code: "P3E2E_EQUIPMENT", fa: "تجهیز مرجع پی‌سه", en: "P3 reference equipment" },
] as const;

async function createCentralDefinition(page: Page, definition: typeof definitions[number]) {
  await page.getByRole("tab", { name: definition.tab, exact: true }).last().click();
  const activePanel = page.locator('[role="tabpanel"][data-state="active"]').last();
  await activePanel.getByRole("button", { name: "ایجاد", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("کد ثابت تعریف مرکزی").fill(definition.code);
  await dialog.getByLabel("نام فارسی تعریف مرکزی").fill(definition.fa);
  await dialog.getByLabel("نام انگلیسی تعریف مرکزی").fill(definition.en);
  if ("symbol" in definition) await dialog.getByLabel("نماد واحد مرکزی").fill(definition.symbol);
  const response = page.waitForResponse(item =>
    item.request().method() === "POST" && item.url().includes("/api/admin/master-data/")
  );
  await dialog.getByRole("button", { name: "ذخیره", exact: true }).click();
  expect((await response).status()).toBe(201);
  await expect(activePanel.getByRole("row").filter({ hasText: definition.code })).toBeVisible();
}

async function openOrganizationFamily(page: Page, tab: string) {
  await page.getByRole("tab", { name: tab, exact: true }).last().click();
  return page.locator('[role="tabpanel"][data-state="active"]').last();
}

async function openCargoEditor(page: Page) {
  await page.locator("summary", { hasText: "جزئیات کالا، وسیله حمل و پیگیری" }).click();
  await page.locator("summary", { hasText: "افزودن کالا" }).click();
}

async function activateForOrganization(page: Page, definition: typeof definitions[number]) {
  const panel = await openOrganizationFamily(page, definition.tab);
  const card = panel.locator("article, [data-slot=card]").filter({ hasText: definition.code }).first();
  await expect(card).toBeVisible();
  const response = page.waitForResponse(item =>
    item.request().method() === "POST" && item.url().includes(`/organization-reference-catalog/`) && item.url().endsWith("/activate")
  );
  await card.getByRole("button", { name: "فعال‌سازی برای سازمان", exact: true }).click();
  expect([200, 201]).toContain((await response).status());
  await expect(card.getByText("فعال برای سازمان", { exact: true })).toBeVisible();
}

test("P3-01 — central definitions → organization activation → expert use → retained history", async ({ page }) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const evidence = observe(page);

  await login(page, "platform");
  await page.getByRole("tab", { name: "تعاریف مرکزی", exact: true }).click();
  await expect(page.getByText("این کاتالوگ مرجع مرکزی فقط زیر اختیار مدیر پلتفرم است.")).toBeVisible();
  await expect(page.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true })).toHaveCount(0);
  for (const definition of definitions) await createCentralDefinition(page, definition);
  await logout(page);

  await login(page, "admin");
  await expect(page.getByRole("tab", { name: "تعاریف مرکزی", exact: true })).toHaveCount(0);
  await page.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true }).click();
  await expect(page.getByRole("heading", { name: "تعاریف پایه حمل", exact: true })).toBeVisible();
  for (const definition of definitions) await activateForOrganization(page, definition);

  const packagePanel = await openOrganizationFamily(page, "انواع بسته‌بندی");
  const packageCard = packagePanel.locator("article, [data-slot=card]").filter({ hasText: "P3E2E_PACKAGE" }).first();
  await packageCard.getByRole("button", { name: "غیرفعال‌سازی برای سازمان", exact: true }).click();
  await expect(packageCard.getByText("غیرفعال برای سازمان", { exact: true }).first()).toBeVisible();
  await packageCard.getByRole("button", { name: "فعال‌سازی برای سازمان", exact: true }).click();
  await expect(packageCard.getByText("فعال برای سازمان", { exact: true })).toBeVisible();
  await logout(page);

  await login(page, "foreign");
  await page.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true }).click();
  const foreignCargoPanel = await openOrganizationFamily(page, "انواع کالا");
  const foreignCargoCard = foreignCargoPanel.locator("article, [data-slot=card]").filter({ hasText: "P3E2E_CARGO" }).first();
  await expect(foreignCargoCard).toBeVisible();
  await expect(foreignCargoCard.getByText("غیرفعال برای سازمان", { exact: true }).first()).toBeVisible();
  await logout(page);

  await login(page, "restricted");
  await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  const shipmentLink = page.locator(`a[href="/operations/shipments/${fixture.shipment_a}"]`);
  await expect(shipmentLink).toBeVisible();
  await shipmentLink.click();
  await expect(page.getByRole("heading", { name: "خلاصه محموله" })).toBeVisible();
  await openCargoEditor(page);
  await page.getByLabel("Cargo line number").fill("2");
  await page.getByLabel("Cargo display name").fill("[P3-01-E2E] کالای فعال سازمان");
  await page.getByLabel("Cargo type").selectOption({ label: "کالای مرجع پی‌سه" });
  await page.getByLabel("Cargo quantity").fill("7.25");
  await page.getByLabel("Unit of measure").selectOption({ label: "واحد مرجع پی‌سه (P3U)" });
  const createCargo = page.waitForResponse(item =>
    item.request().method() === "POST" && item.url().includes(`/operational-shipments/${fixture.shipment_a}/cargo-items`)
  );
  await page.getByRole("button", { name: "افزودن کالا", exact: true }).click();
  expect((await createCargo).status()).toBe(201);
  await expect(page.getByRole("article").filter({ hasText: "[P3-01-E2E] کالای فعال سازمان" }).first()).toBeVisible();
  await page.reload();
  await page.locator("summary", { hasText: "جزئیات کالا، وسیله حمل و پیگیری" }).click();
  await expect(page.getByRole("article").filter({ hasText: "[P3-01-E2E] کالای فعال سازمان" }).first()).toBeVisible();

  await page.goto("/expert");
  await logout(page);
  await login(page, "admin");
  await page.getByRole("tab", { name: "تعاریف قابل استفاده سازمان", exact: true }).click();
  const cargoPanel = await openOrganizationFamily(page, "انواع کالا");
  const cargoCard = cargoPanel.locator("article, [data-slot=card]").filter({ hasText: "P3E2E_CARGO" }).first();
  await cargoCard.getByRole("button", { name: "غیرفعال‌سازی برای سازمان", exact: true }).click();
  await expect(cargoCard.getByText("غیرفعال برای سازمان", { exact: true }).first()).toBeVisible();
  await logout(page);

  await login(page, "restricted");
  await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  await page.locator(`a[href="/operations/shipments/${fixture.shipment_a}"]`).click();
  await page.locator("summary", { hasText: "جزئیات کالا، وسیله حمل و پیگیری" }).click();
  await expect(page.getByRole("article").filter({ hasText: "[P3-01-E2E] کالای فعال سازمان" }).first()).toBeVisible();
  await page.locator("summary", { hasText: "افزودن کالا" }).click();
  await expect(page.getByText("این نوع در تعاریف سازمان موجود نیست. برای ادامه، مدیر سازمان باید آن را تعریف یا فعال کند.")).toBeVisible();
  await expect(page.getByRole("button", { name: "افزودن کالا", exact: true })).toBeDisabled();

  clean(evidence);
});
