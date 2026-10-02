import { expect, test, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { openShipmentSection } from "./helpers/shipment-workspace";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const apiBase = process.env.VITE_BACKEND_URL || "http://127.0.0.1:5001";
if (!password || !fixturePath) throw new Error("P3-02 qualification must use its disposable local runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  shipment_a: string;
  p3_request_tracking_code: string;
  p3_customer_a_label: string;
  p3_customer_b_label: string;
  p3_packaging_label: string;
  p3_weight_uom_label: string;
  p3_volume_uom_label: string;
};
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

async function login(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill("shared_transport_e2e_restricted");
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}

async function openShipment(page: Page) {
  await page.goto(`/operations/shipments/${fixture.shipment_a}`);
  await expect(page.getByRole("navigation", { name: "بخش‌های پرونده حمل" })).toBeVisible();
  await openShipmentSection(page, "cargo", fixture.shipment_a);
  await expect(page.getByText("کالا، مشتری و درخواست منبع", { exact: true })).toBeVisible();
}

async function selectOptionContaining(select: Locator, text: string) {
  const value = await select.locator("option").filter({ hasText: text }).first().getAttribute("value");
  expect(value, `option containing ${text}`).toBeTruthy();
  await select.selectOption(value!);
}

async function createRequestCargo(page: Page) {
  await page.locator("summary", { hasText: "افزودن ردیف کالا" }).click();
  await page.getByLabel("شماره ردیف کالا", { exact: true }).fill("2");
  await selectOptionContaining(page.getByLabel("درخواست منبع", { exact: true }), fixture.p3_request_tracking_code);
  await selectOptionContaining(page.getByLabel("قلم کالای درخواست منبع", { exact: true }), "پمپ‌های درخواستی پی‌سه");
  await expect(page.getByLabel("مالک کالا", { exact: true })).toHaveValue(/\d+/);
  await expect(page.getByLabel("مقدار درخواستی", { exact: true })).toHaveValue(/^12(?:\.0+)?$/);
  await page.getByLabel("مقدار برنامه‌ریزی‌شده", { exact: true }).fill("10");
  await page.getByLabel("نوع بسته‌بندی", { exact: true }).selectOption({ label: fixture.p3_packaging_label });
  const created = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().includes(`/operational-shipments/${fixture.shipment_a}/cargo-items`)
  );
  await page.getByRole("button", { name: "افزودن کالا", exact: true }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  return (await response.json()) as { item: { public_id: string } };
}

async function createDirectCargo(page: Page) {
  await page.getByLabel("شماره ردیف کالا", { exact: true }).fill("3");
  await page.getByLabel("نام نمایشی کالا", { exact: true }).fill("[P3-02-E2E] کالای مستقیم مشتری دوم");
  await page.getByLabel("نوع کالا", { exact: true }).selectOption({ label: "بار آزمایشی" });
  await page.getByLabel("مالک کالا", { exact: true }).selectOption({ label: fixture.p3_customer_b_label });
  await page.getByLabel("درخواست منبع", { exact: true }).selectOption("");
  await page.getByLabel("مقدار برنامه‌ریزی‌شده", { exact: true }).fill("5");
  await selectOptionContaining(page.getByLabel("واحد اندازه‌گیری", { exact: true }), "پالت");
  const created = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().includes(`/operational-shipments/${fixture.shipment_a}/cargo-items`)
  );
  await page.getByRole("button", { name: "افزودن کالا", exact: true }).click();
  const response = await created;
  expect(response.status()).toBe(201);
}

test("P3-02 — Request lineage, direct cargo, progressive completion, and reopen", async ({ page }, testInfo) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const evidence = observe(page);

  await login(page);
  await openShipment(page);
  const requestCreated = await createRequestCargo(page);
  const requestCard = page.getByRole("article").filter({ hasText: "پمپ‌های درخواستی پی‌سه" }).first();
  await expect(requestCard).toContainText(fixture.p3_customer_a_label);
  await expect(requestCard).toContainText(`درخواست ${fixture.p3_request_tracking_code}`);
  await expect(requestCard).toContainText("درخواستی12");
  await expect(requestCard).toContainText("برنامه‌ریزی‌شده10");
  await expect(requestCard).toContainText("واقعیهنوز ثبت نشده");
  await expect(requestCard).toContainText("اطلاعات قابل تکمیل: HS، وزن، حجم");

  await createDirectCargo(page);
  const directCard = page.getByRole("article").filter({ hasText: "[P3-02-E2E] کالای مستقیم مشتری دوم" }).first();
  await expect(directCard).toContainText(fixture.p3_customer_b_label);
  await expect(directCard).toContainText("منبع: ثبت مستقیم");
  await expect(directCard.locator("p").filter({ hasText: "منبع:" }).first()).toHaveText("منبع: ثبت مستقیم");

  await requestCard.locator("summary", { hasText: "تکمیل یا اصلاح اطلاعات" }).click();
  const actualInput = requestCard.getByLabel("ویرایش مقدار واقعی ردیف 2");
  await actualInput.fill("۸٫۵");
  await expect(actualInput).toHaveValue("8.5");
  await requestCard.getByLabel("ویرایش کد HS ردیف 2").fill("84137090");
  await requestCard.getByLabel("ویرایش مقصد ردیف 2").fill("انبار مقصد تهران");
  await requestCard.getByLabel("ویرایش وزن ناخالص ردیف 2").fill("2500");
  await selectOptionContaining(requestCard.getByLabel("ویرایش واحد وزن ردیف 2"), fixture.p3_weight_uom_label);
  await requestCard.getByLabel("ویرایش حجم ردیف 2").fill("18");
  await selectOptionContaining(requestCard.getByLabel("ویرایش واحد حجم ردیف 2"), fixture.p3_volume_uom_label);
  const updated = page.waitForResponse(response =>
    response.request().method() === "PATCH" && response.url().includes(`/cargo-items/${requestCreated.item.public_id}`)
  );
  await requestCard.getByRole("button", { name: "ذخیره اطلاعات کالا", exact: true }).click();
  const updatedResponse = await updated;
  expect(updatedResponse.status()).toBe(200);
  const updatedBody = await updatedResponse.json();
  expect(Number(updatedBody.item.quantities.planned)).toBe(10);
  expect(Number(updatedBody.item.quantities.actual)).toBe(8.5);
  expect(updatedBody.item.version).toBeGreaterThan(1);
  await expect(page.getByText(/مقدار واقعی کالا ثبت شد:.*8.5/)).toBeVisible();
  await expect(requestCard).toContainText("واقعی8.5");
  await expect(requestCard).toContainText("HS: 84137090");
  await expect(requestCard).toContainText("انبار مقصد تهران");
  await expect(requestCard.getByText(/اطلاعات قابل تکمیل/)).toHaveCount(0);

  const history = await page.evaluate(async ({ shipment, item, base }) => {
    const token = localStorage.getItem("expert_token");
    const response = await fetch(
      `${base}/api/internal/operational-shipments/${shipment}/cargo-items/${item}/history`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    return { status: response.status, body: await response.json() };
  }, { shipment: fixture.shipment_a, item: requestCreated.item.public_id, base: apiBase });
  expect(history.status).toBe(200);
  expect(history.body.history.map((entry: { action: string }) => entry.action)).toEqual(
    expect.arrayContaining(["SHIPMENT_CARGO_CREATED", "SHIPMENT_CARGO_UPDATED"]),
  );
  const actualHistory = history.body.history.find((entry: { changes?: Record<string, { before: string | null; after: string | null }> }) =>
    entry.changes?.actual_quantity?.after !== null && entry.changes?.actual_quantity?.after !== undefined,
  );
  expect(actualHistory.changes.actual_quantity.before).toBeNull();
  expect(Number(actualHistory.changes.actual_quantity.after)).toBe(8.5);
  expect(actualHistory.changes).not.toHaveProperty("planned_quantity");

  await openShipment(page);
  const reopenedRequest = page.getByRole("article").filter({ hasText: "پمپ‌های درخواستی پی‌سه" }).first();
  const reopenedDirect = page.getByRole("article").filter({ hasText: "[P3-02-E2E] کالای مستقیم مشتری دوم" }).first();
  await expect(reopenedRequest).toContainText("درخواستی12");
  await expect(reopenedRequest).toContainText("برنامه‌ریزی‌شده10");
  await expect(reopenedRequest).toContainText("واقعی8.5");
  await reopenedRequest.locator("summary", { hasText: "تکمیل یا اصلاح اطلاعات" }).click();
  await expect(reopenedRequest.getByLabel("ویرایش مقدار برنامه‌ریزی‌شده ردیف 2")).toHaveValue(/^10(?:\.0+)?$/);
  await expect(reopenedRequest.getByLabel("ویرایش مقدار واقعی ردیف 2")).toHaveValue(/^8\.5(?:0+)?$/);
  await expect(reopenedDirect).toContainText("منبع: ثبت مستقیم");

  expect(await page.locator("html").getAttribute("dir")).toBe("rtl");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  const reopenedScreenshot = testInfo.outputPath("actual-cargo-reopened.png");
  await page.screenshot({ path: reopenedScreenshot, fullPage: true });
  await testInfo.attach("p3-02-cargo-lineage-reopened", {
    path: reopenedScreenshot,
    contentType: "image/png",
  });

  expect(evidence.unexpected, "unexpected API failures").toEqual([]);
  expect(evidence.failed, "unexpected failed requests").toEqual([]);
  expect(evidence.page, "unexpected page errors").toEqual([]);
  expect(evidence.console, "unexpected console errors").toEqual([]);
});
