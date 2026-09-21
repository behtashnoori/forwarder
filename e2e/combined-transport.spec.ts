import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const password = process.env.FORWARDER_E2E_PASSWORD;
if (!databaseUrl || !password) throw new Error("Combined Transport E2E requires its disposable database and password.");
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_combined_transport_qa")) {
  throw new Error("Combined Transport browser proof is restricted to the owned loopback database.");
}

const customerId = 900021;
let zeroCargoRequestId = 0;
let multiCargoRequestId = 0;
let zeroCargoTrackingNumber = "";
let multiCargoTrackingNumber = "";

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

async function openCombinedDomesticForm(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "شروع یک حمل جدید" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "حمل داخلی" }).click();
  await chooseSelect(page, 0, 0);
  await chooseSelect(page, 1, 1);
  await page.getByLabel("شماره تماس").fill("09123456789");
  await page.getByRole("combobox").nth(3).click();
  await page.getByRole("option", { name: /حمل ترکیبی/ }).click();
  await expect(page.getByRole("combobox").nth(3)).toContainText("حمل ترکیبی");
}

async function submit(page: Page) {
  await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
  await expect(page.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
  const responsePromise = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith("/api/shipment-request"),
  );
  await page.getByRole("button", { name: "تایید و ارسال درخواست" }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  return response.json() as Promise<{
    id: number;
    tracking_code: string;
    request_transport_intent: string;
    cargo_items: Array<{ description: string | null }>;
  }>;
}

async function reopen(page: Page, requestId: number) {
  await page.goto(`/customer/${customerId}`);
  const card = page.getByText(`درخواست #${requestId}`, { exact: true }).locator("xpath=ancestor::div[contains(@class,'rounded-xl')][1]");
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "مشاهده جزئیات" }).click();
  await expect(page).toHaveURL(new RegExp(`/request/${requestId}\\?customer=${customerId}$`));
  await expect(page.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
}

async function loginAsExpert(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill("combined_transport_e2e_expert");
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).toHaveURL(/\/expert$/);
}

test.describe.serial("Combined Transport Request intent", () => {
  test("A — Combined plus zero Cargo submits and reopens", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await bindRequestToCustomer(page);
    await openCombinedDomesticForm(page);
    const created = await submit(page);
    zeroCargoRequestId = created.id;
    zeroCargoTrackingNumber = created.tracking_code;
    expect(created.request_transport_intent).toBe("Combined Transport");
    expect(created.cargo_items).toEqual([]);
    await reopen(page, created.id);
    await expect(page.getByText("هیچ قلم کالایی اضافه نشده است.")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("combined-zero-cargo-rtl.png"), fullPage: true });
    expectClean(evidence);
  });

  test("B — Combined plus multiple Cargo Items preserves both facts", async ({ page }) => {
    const evidence = observe(page);
    await bindRequestToCustomer(page);
    await openCombinedDomesticForm(page);
    await page.getByRole("button", { name: "مشخصات کالا (اختیاری)" }).click();
    const add = page.getByRole("button", { name: "افزودن قلم کالا" });
    await add.click();
    await add.click();
    await page.getByLabel("توضیحات کالا").nth(0).fill("Combined cargo alpha");
    await page.getByLabel("توضیحات کالا").nth(1).fill("Combined cargo beta");
    const created = await submit(page);
    multiCargoRequestId = created.id;
    multiCargoTrackingNumber = created.tracking_code;
    expect(created.request_transport_intent).toBe("Combined Transport");
    expect(created.cargo_items.map(item => item.description)).toEqual(["Combined cargo alpha", "Combined cargo beta"]);
    await reopen(page, created.id);
    await expect(page.getByText("Combined cargo alpha")).toBeVisible();
    await expect(page.getByText("Combined cargo beta")).toBeVisible();
    expectClean(evidence);
  });

  test("C/D — Expert sees the same localized intent in list and responsive detail", async ({ page }, testInfo) => {
    expect(zeroCargoRequestId).toBeGreaterThan(0);
    expect(multiCargoRequestId).toBeGreaterThan(0);
    expect(zeroCargoTrackingNumber).not.toBe("");
    expect(multiCargoTrackingNumber).not.toBe("");
    const evidence = observe(page);
    await loginAsExpert(page);
    await page.getByRole("tab", { name: "همه" }).click();
    const zeroCargoCard = page.getByText(zeroCargoTrackingNumber, { exact: true })
      .locator("xpath=ancestor::div[contains(@class,'rounded-3xl')][1]");
    const multiCargoCard = page.getByText(multiCargoTrackingNumber, { exact: true })
      .locator("xpath=ancestor::div[contains(@class,'rounded-3xl')][1]");
    await expect(zeroCargoCard.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
    await expect(multiCargoCard.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
    await zeroCargoCard.getByRole("button", { name: "مشاهده جزئیات" }).click();
    await expect(page.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("combined-expert-mobile-390.png"), fullPage: true });
    expectClean(evidence);
  });
});
