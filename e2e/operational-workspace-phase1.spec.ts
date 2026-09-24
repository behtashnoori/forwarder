import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const expertPassword = process.env.FORWARDER_E2E_PASSWORD;
const customerPassword = process.env.FORWARDER_E2E_CUSTOMER_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const evidencePath = process.env.OPERATIONAL_WORKSPACE_EVIDENCE_PATH;
if (!databaseUrl || !expertPassword || !customerPassword || !fixturePath || !evidencePath) {
  throw new Error("Operational Workspace E2E requires its owned runtime inputs.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_workspace_phase1_")) {
  throw new Error("Operational Workspace browser proof is restricted to its owned loopback database.");
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  usernames: { owner: string; peer: string; empty: string; foreign: string; admin: string };
  peer_id: number;
  request_id: number;
  active_shipment_public_id: string;
  terminal_shipment_public_id: string;
  foreign_shipment_public_id: string;
  portal_customer_email: string;
  portal_request_public_id: string;
  portal_request_id: number;
  public_capability: string;
};

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page, expectedStatuses: number[] = []): BrowserEvidence {
  const evidence: BrowserEvidence = {
    consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [],
  };
  page.on("console", message => {
    const value = message.text();
    const expectedHttpNoise = expectedStatuses.some(status => value.includes(`status of ${status}`));
    if (message.type() === "error" && !expectedHttpNoise) evidence.consoleErrors.push(value);
  });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => evidence.failedRequests.push(
    `${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`,
  ));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400 && !expectedStatuses.includes(response.status())) {
      evidence.unexpectedResponses.push(
        `${response.status()} ${response.request().method()} ${response.url()}`,
      );
    }
  });
  return evidence;
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.pageErrors, "uncaught browser errors").toEqual([]);
  expect(evidence.failedRequests, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  expect(
    evidence.consoleErrors.filter(item => !item.includes("favicon")),
    "browser console errors",
  ).toEqual([]);
}

async function loginExpert(page: Page, username: string, expectedLanding: RegExp) {
  await page.context().clearCookies();
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole("button", { name: /ورود/ }).first().click();
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور").fill(expertPassword!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).toHaveURL(expectedLanding);
}

async function expertToken(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(token).toBeTruthy();
  return token!;
}

async function screenshot(page: Page, name: string) {
  const target = path.join(evidencePath!, name);
  await page.screenshot({ path: target, fullPage: true });
}

test.describe.serial("Operational Workspace Phase 1 governed browser proof", () => {
  test("normal expert journey reaches sourced overview, shipment context, and history", async ({ page }) => {
    test.setTimeout(240_000);
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);

    await expect(page.getByRole("heading", { name: "امروز چه چیزی نیاز به توجه من دارد؟" })).toBeVisible();
    await expect(page.getByRole("link", { name: "فضای کار امروز" })).toBeVisible();
    await expect(page.getByText("مشتری عملیاتی آزمایشی", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("کارشناس مسئول ثابت: کارشناس مالک ثابت")).toBeVisible();
    await expect(page.getByText("موعد یک مرحله عملیاتی گذشته است")).toBeVisible();
    await expect(page.getByText("منبع: پیگیری عملیاتی ثبت‌شده", { exact: false })).toBeVisible();
    await expect(page.getByText("آخرین به‌روزرسانی:", { exact: false })).toBeVisible();
    await screenshot(page, "workspace-overview.png");

    await page.getByRole("link", { name: /مشاهده محموله مشتری عملیاتی آزمایشی/ }).click();
    await expect(page).toHaveURL(new RegExp(`/operations/shipments/${fixture.active_shipment_public_id}$`));
    await expect(page.getByText("کارشناس مسئول ثابت", { exact: true })).toBeVisible();
    await expect(page.getByText("کارشناس مالک ثابت", { exact: true })).toBeVisible();
    await expect(page.getByText("تهران", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("تبریز", { exact: false }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "تاریخچه یکپارچه محموله" })).toBeVisible();
    await expect(page.getByText("در حال دریافت تاریخچه…")).toBeHidden({ timeout: 30_000 });
    await expect(page.getByLabel("تاریخچه عملیات حمل")).not.toContainText("دریافت تاریخچه عملیات ممکن نشد");
    await screenshot(page, "shipment-context-history.png");

    await page.getByRole("link", { name: /بازگشت به فضای کار امروز/ }).click();
    await expect(page).toHaveURL(/\/operations$/);
    await expect(page.getByRole("heading", { name: "امروز چه چیزی نیاز به توجه من دارد؟" })).toBeVisible();

    await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل" }).click();
    await expect(page).toHaveURL(/\/operations\/shipments$/);
    await expect(page.getByText("مشتری عملیاتی آزمایشی", { exact: false }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /مشاهده محموله عملیاتی مشتری عملیاتی آزمایشی/ })).toHaveCount(1);
    await page.getByRole("button", { name: "نمایش همه وضعیت‌ها" }).click();
    await expect(page.getByRole("link", { name: /مشاهده محموله عملیاتی مشتری عملیاتی آزمایشی/ })).toHaveCount(2);
    expectClean(evidence);
  });

  test("request reassignment does not transfer fixed shipment visibility", async ({ page }) => {
    const evidence = observe(page, [404]);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    const ownerToken = await expertToken(page);
    const reassigned = await page.request.post(`/api/expert/requests/${fixture.request_id}/assign`, {
      headers: { Authorization: `Bearer ${ownerToken}` },
      data: { expert_id: fixture.peer_id },
    });
    expect(reassigned.status()).toBe(200);
    await page.reload();
    await expect(page.getByText("کارشناس مسئول ثابت: کارشناس مالک ثابت")).toBeVisible();

    await loginExpert(page, fixture.usernames.peer, /\/operations$/);
    await expect(page.getByText("محموله فعالی در دامنه دسترسی شما وجود ندارد.")).toBeVisible();
    const peerToken = await expertToken(page);
    const guessedOwnerShipment = await page.request.get(
      `/api/operational-shipments/${fixture.active_shipment_public_id}`,
      { headers: { Authorization: `Bearer ${peerToken}` } },
    );
    expect(guessedOwnerShipment.status()).toBe(404);

    await loginExpert(page, fixture.usernames.foreign, /\/operations$/);
    await expect(page.getByText("مشتری سازمان دیگر", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("مشتری عملیاتی آزمایشی", { exact: false })).toHaveCount(0);
    const foreignToken = await expertToken(page);
    const crossTenant = await page.request.get(
      `/api/operational-shipments/${fixture.active_shipment_public_id}`,
      { headers: { Authorization: `Bearer ${foreignToken}` } },
    );
    expect(crossTenant.status()).toBe(404);
    expectClean(evidence);
  });

  test("empty and temporary-error states remain explicit", async ({ page }) => {
    const evidence = observe(page, [503]);
    await loginExpert(page, fixture.usernames.empty, /\/operations$/);
    await expect(page.getByText("محموله فعالی در دامنه دسترسی شما وجود ندارد.")).toBeVisible();
    await screenshot(page, "workspace-empty.png");

    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    await page.route("**/api/operational-workspace?limit=8", route => route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ message: "synthetic temporary failure" }),
    }));
    await page.reload();
    await expect(page.getByRole("alert")).toContainText("فضای کار عملیاتی در حال حاضر بارگذاری نشد");
    await expect(page.getByRole("button", { name: "تلاش دوباره" })).toBeVisible();
    await page.unroute("**/api/operational-workspace?limit=8");
    expectClean(evidence);
  });

  test("Customer Account private requests, quote history/response, recovery, and tenant admin remain intact", async ({ page }) => {
    const evidence = observe(page);
    await page.context().clearCookies();
    await page.goto("/customer");
    await page.locator("#customer-email").fill(fixture.portal_customer_email);
    await page.locator("#customer-password").fill(customerPassword!);
    await page.locator("form").getByRole("button").first().click();
    await expect(page).toHaveURL(/\/customer\/requests$/);
    await expect(page.getByText(fixture.public_capability, { exact: true })).toBeVisible();
    await page.getByRole("link", { name: /مشاهده جزئیات/ }).first().click();
    await expect(page).toHaveURL(new RegExp(`/customer/requests/${fixture.portal_request_public_id}$`));
    await expect(page.getByText("پیشنهاد جاری برای پاسخ مرورگری")).toBeVisible();
    await expect(page.getByText("پیام سابق مشتری")).toBeVisible();
    await page.locator("#customer-discussion").fill("پیام مرورگری مشتری");
    await page.locator("#customer-discussion").locator("xpath=following-sibling::button").click();
    await expect(page.getByText("پیام مرورگری مشتری").first()).toBeVisible();

    await page.context().clearCookies();
    await page.goto("/customer/forgot-password");
    await page.locator("#recovery-email").fill(fixture.portal_customer_email);
    await page.locator("form").getByRole("button").first().click();
    const knownResponse = await page.getByRole("status").innerText();
    await page.reload();
    await page.locator("#recovery-email").fill("missing-account@example.invalid");
    await page.locator("form").getByRole("button").first().click();
    await expect(page.getByRole("status")).toHaveText(knownResponse);

    await loginExpert(page, fixture.usernames.admin, /\/admin$/);
    const adminToken = await expertToken(page);
    const accounts = await page.request.get("/api/admin/customer-portal-accounts", {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    expect(accounts.status()).toBe(200);
    expect(JSON.stringify(await accounts.json())).toContain(fixture.portal_customer_email);
    expectClean(evidence);
  });

  test("Public Tracking remains capability-only and anonymous request creation remains available", async ({ page }) => {
    const evidence = observe(page, [404]);
    await page.context().clearCookies();
    await page.goto(`/customer/track/${fixture.public_capability}`);
    await expect(page.getByRole("heading", { name: fixture.public_capability })).toBeVisible();
    await expect(page.getByText("Shanghai، China", { exact: true })).toBeVisible();
    await expect(page.getByText("Tehran، Iran", { exact: true })).toBeVisible();
    await expect(page.getByText("OW-PHASE1-UNIT", { exact: false })).toBeVisible();
    await expect(page.getByText("در مسیر مقصد", { exact: false })).toBeVisible();

    const publicResponse = await page.request.get(`/api/public/track/${fixture.public_capability}`);
    expect(publicResponse.status()).toBe(200);
    const publicBody = await publicResponse.json();
    expect(Object.keys(publicBody).sort()).toEqual([
      "assigned_at", "created_at", "domestic_transport_method",
      "international_transport_method", "route", "shipping_type", "status",
      "tracking_number", "transport_method", "transport_method_preference",
      "unit_tracking", "workflow_steps_simple",
    ]);
    const serialized = JSON.stringify(publicBody);
    for (const forbidden of [
      "organization_id", "Private origin address", "Private destination address",
      "Private workspace tracking note", fixture.portal_customer_email,
    ]) expect(serialized).not.toContain(forbidden);

    const numericProbe = await page.request.get(`/api/public/track/${fixture.portal_request_id}`);
    expect(numericProbe.status()).toBe(404);
    expect(await numericProbe.json()).toEqual({ message: "درخواست یافت نشد" });

    const anonymous = await page.request.post("/api/shipment-request", {
      data: {
        shipping_type: "international",
        origin_country: "China",
        origin_city_international: "Shenzhen",
        dest_country: "Turkey",
        dest_city_international: "Istanbul",
        contact_phone: "09128888888",
        international_transport_method: "Combined Transport",
        transport_method_preference: "customer_choice",
        cargo_items: [],
      },
    });
    expect(anonymous.status()).toBe(201);
    const created = await anonymous.json();
    expect(created.tracking_code).toMatch(/^SR2-[A-Za-z0-9_-]{22}$/);
    await page.goto(`/customer/track/${created.tracking_code}`);
    await expect(page.getByRole("heading", { name: created.tracking_code })).toBeVisible();
    expectClean(evidence);
  });
});
