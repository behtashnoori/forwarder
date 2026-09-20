import { expect, test, type Page } from "@playwright/test";
import pg from "pg";

const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) throw new Error("E2E_DATABASE_URL must identify the owned disposable PostgreSQL database.");
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_cargo_build")) {
  throw new Error("Request Cargo browser proof is restricted to the owned loopback database.");
}

const customerId = 900001;
const pool = new pg.Pool({ connectionString: databaseUrl.replace("postgresql+psycopg://", "postgresql://") });

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page): BrowserEvidence {
  const evidence: BrowserEvidence = { consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [] };
  page.on("console", message => { if (message.type() === "error") evidence.consoleErrors.push(message.text()); });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => evidence.failedRequests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      evidence.unexpectedResponses.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  return evidence;
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.pageErrors).toEqual([]);
  expect(evidence.failedRequests).toEqual([]);
  expect(evidence.unexpectedResponses).toEqual([]);
  expect(evidence.consoleErrors.filter(item => !item.includes("favicon"))).toEqual([]);
}

async function chooseSelect(page: Page, controlIndex: number, optionIndex: number) {
  await page.getByRole("combobox").nth(controlIndex).click();
  await page.getByRole("option").nth(optionIndex).click();
}

async function bindRequestToCustomer(page: Page) {
  await page.route("**/api/shipment-request", async route => {
    const request = route.request();
    if (request.method() !== "POST") return route.continue();
    const body = request.postDataJSON() as Record<string, unknown>;
    await route.continue({
      postData: JSON.stringify({ ...body, gamification_customer_id: customerId }),
      headers: { ...request.headers(), "content-type": "application/json" },
    });
  });
}

async function openCompletedDomesticForm(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "شروع یک حمل جدید" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "حمل داخلی" }).click();
  await expect(page.getByText("مشخصات کالا (اختیاری)", { exact: true })).toBeVisible();
  await chooseSelect(page, 0, 0);
  await chooseSelect(page, 1, 1);
  await page.getByLabel("شماره تماس").fill("09123456789");
  await chooseSelect(page, 2, 1);
}

async function submitAndReadResponse(page: Page) {
  await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
  await expect(page.getByRole("button", { name: "تایید و ارسال درخواست" })).toBeVisible();
  const responsePromise = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith("/api/shipment-request"),
  );
  await page.getByRole("button", { name: "تایید و ارسال درخواست" }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  return response.json() as Promise<{ id: number; tracking_code: string; cargo_items: Array<{ public_id: string; position: number; description: string | null; quantity: string | null }> }>;
}

async function reopenFromCustomerDashboard(page: Page, requestId: number) {
  await page.goto(`/customer/${customerId}`);
  const card = page.getByText(`درخواست #${requestId}`, { exact: true }).locator("xpath=ancestor::div[contains(@class,'rounded-xl')][1]");
  await expect(card).toBeVisible();
  await expect(card).toContainText(/[^()]+\([^()]+\)/);
  await card.getByRole("button", { name: "مشاهده جزئیات" }).click();
  await expect(page).toHaveURL(new RegExp(`/request/${requestId}\\?customer=${customerId}$`));
}

test.beforeAll(async () => {
  await pool.query(`
    INSERT INTO customer_gamification
      (id, email, phone, created_at, is_email_verified, total_requests,
       completed_requests, loyalty_points, customer_level)
    VALUES
      ($1, 'request-cargo-browser@example.test', '09120000999', now(), false,
       0, 0, 0, 'bronze')
    ON CONFLICT (id) DO UPDATE SET
      email=EXCLUDED.email,
      phone=EXCLUDED.phone,
      total_requests=COALESCE(customer_gamification.total_requests, 0),
      completed_requests=COALESCE(customer_gamification.completed_requests, 0),
      loyalty_points=COALESCE(customer_gamification.loyalty_points, 0),
      customer_level=COALESCE(customer_gamification.customer_level, 'bronze')
  `, [customerId]);
});

test.afterAll(async () => {
  await pool.end();
});

test.describe.serial("optional Request Cargo customer journey", () => {
  test("zero Cargo stays optional through submit and reopen", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await bindRequestToCustomer(page);
    await openCompletedDomesticForm(page);
    const created = await submitAndReadResponse(page);
    expect(created.cargo_items).toEqual([]);
    await expect(page.getByText("هیچ قلم کالایی اضافه نشده است.")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("zero-cargo-created.png"), fullPage: true });
    await reopenFromCustomerDashboard(page, created.id);
    await expect(page.getByText("هیچ قلم کالایی اضافه نشده است.")).toBeVisible();
    expectClean(evidence);
  });

  test("multiple Cargo Items retain identity, order, precision and detail", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await bindRequestToCustomer(page);
    await openCompletedDomesticForm(page);
    await page.getByRole("button", { name: "مشخصات کالا (اختیاری)" }).click();
    const add = page.getByRole("button", { name: "افزودن قلم کالا" });
    await add.click();
    await add.click();
    await add.click();
    const descriptions = page.getByLabel("توضیحات کالا");
    await descriptions.nth(0).fill("Browser cargo alpha");
    await descriptions.nth(1).fill("Browser cargo beta");
    await descriptions.nth(2).fill("Browser cargo gamma");
    await page.getByLabel("مقدار دقیق").nth(2).fill("3.250000");
    await page.getByLabel("واحد مقدار").nth(2).selectOption("b2222222-2222-4222-8222-222222222222");

    const created = await submitAndReadResponse(page);
    expect(created.cargo_items.map(item => item.position)).toEqual([1, 2, 3]);
    expect(new Set(created.cargo_items.map(item => item.public_id)).size).toBe(3);
    expect(created.cargo_items[2].quantity).toBe("3.250000");
    for (const description of ["Browser cargo alpha", "Browser cargo beta", "Browser cargo gamma"]) {
      await expect(page.getByText(description)).toBeVisible();
    }
    await page.screenshot({ path: testInfo.outputPath("multi-cargo-created.png"), fullPage: true });

    await reopenFromCustomerDashboard(page, created.id);
    const detailItems = page.locator("ol").filter({ hasText: "Browser cargo alpha" }).locator("li");
    await expect(detailItems).toHaveCount(3);
    await expect(detailItems.nth(0)).toContainText("Browser cargo alpha");
    await expect(detailItems.nth(1)).toContainText("Browser cargo beta");
    await expect(detailItems.nth(2)).toContainText("Browser cargo gamma");
    await expect(detailItems.nth(2)).toContainText("۳٫۲۵ kg");
    await page.screenshot({ path: testInfo.outputPath("multi-cargo-reopened.png"), fullPage: true });
    expectClean(evidence);
  });

  test("invalid voluntary row is understandable and does not submit", async ({ page }) => {
    const evidence = observe(page);
    let createCalls = 0;
    await bindRequestToCustomer(page);
    page.on("request", request => {
      if (request.method() === "POST" && request.url().endsWith("/api/shipment-request")) createCalls += 1;
    });
    await openCompletedDomesticForm(page);
    await page.getByRole("button", { name: "مشخصات کالا (اختیاری)" }).click();
    await page.getByRole("button", { name: "افزودن قلم کالا" }).click();
    await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
    const item = page.getByRole("article", { name: /قلم کالا/ });
    await expect(item.getByRole("alert")).toContainText("برای این قلم، توضیح، نوع کالا یا مقدار همراه واحد را وارد کنید");
    expect(createCalls).toBe(0);

    await page.getByLabel("توضیحات کالا").fill("Draft remains present");
    await page.getByLabel("مقدار دقیق").fill("1.0000001");
    await page.getByLabel("واحد مقدار").selectOption("b2222222-2222-4222-8222-222222222222");
    await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
    await expect(item.getByRole("alert")).toContainText("مقدار حداکثر می‌تواند ۶ رقم اعشار داشته باشد.");
    await expect(page.getByLabel("توضیحات کالا")).toHaveValue("Draft remains present");
    expect(createCalls).toBe(0);
    expectClean(evidence);
  });
});
