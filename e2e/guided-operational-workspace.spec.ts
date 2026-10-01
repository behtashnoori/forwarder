import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const expertPassword = process.env.FORWARDER_E2E_PASSWORD;
const customerPassword = process.env.FORWARDER_E2E_CUSTOMER_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const evidencePath = process.env.OPERATIONAL_WORKSPACE_EVIDENCE_PATH;
if (
  !databaseUrl ||
  !expertPassword ||
  !customerPassword ||
  !fixturePath ||
  !evidencePath
) {
  throw new Error(
    "Guided Operational Workspace E2E requires owned runtime inputs.",
  );
}
if (
  !databaseUrl.includes("127.0.0.1") ||
  !databaseUrl.includes("/forwarder_workspace_phase1_")
) {
  throw new Error(
    "Guided workspace proof is restricted to its owned loopback database.",
  );
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  usernames: { owner: string; admin: string };
  request_id: number;
  active_shipment_public_id: string;
  portal_customer_email: string;
  portal_request_public_id: string;
};

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page): BrowserEvidence {
  const evidence: BrowserEvidence = {
    consoleErrors: [],
    pageErrors: [],
    failedRequests: [],
    unexpectedResponses: [],
  };
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("favicon"))
      evidence.consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => evidence.pageErrors.push(error.message));
  page.on("requestfailed", (request) =>
    evidence.failedRequests.push(
      `${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`,
    ),
  );
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      evidence.unexpectedResponses.push(
        `${response.status()} ${response.request().method()} ${response.url()}`,
      );
    }
  });
  return evidence;
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.consoleErrors, "browser console errors").toEqual([]);
  expect(evidence.pageErrors, "uncaught browser errors").toEqual([]);
  expect(evidence.failedRequests, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
}

async function loginExpert(
  page: Page,
  username: string,
  expectedLanding: RegExp,
) {
  await page.context().clearCookies();
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole("button", { name: /ورود/ }).first().click();
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور").fill(expertPassword!);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "ورود", exact: true })
    .click();
  await expect(page).toHaveURL(expectedLanding);
}

async function loginCustomer(page: Page) {
  await page.context().clearCookies();
  await page.goto("/customer");
  await page.locator("#customer-email").fill(fixture.portal_customer_email);
  await page.locator("#customer-password").fill(customerPassword!);
  await page.locator("form").getByRole("button").first().click();
  await expect(page).toHaveURL(/\/customer\/requests$/);
}

async function screenshot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(evidencePath!, name),
    fullPage: true,
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  const geometry = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth + 1);
}

test.describe
  .serial("Guided Operational Workspace read-only browser proof", () => {
  test("expert home starts with a priority and exception queue", async ({
    page,
  }) => {
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    await page.goto("/expert");
    await expect(
      page.getByRole("heading", { name: "امروز چه چیزی باید جلو برود؟" }),
    ).toBeVisible();
    await expect(
      page.getByText("صف عملیاتی من", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("نیازمند توجه", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByText("OW-OPERATIONAL-001", { exact: true }).first(),
    ).toBeVisible();
    await screenshot(page, "guided-expert-home-priority.png");
    await expectNoHorizontalOverflow(page);
    expectClean(evidence);
  });

  test("shipment list is an actionable priority queue on desktop and mobile", async ({
    page,
  }) => {
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    const listResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" &&
        response.url().includes("/api/operational-shipments?"),
    );
    await page.goto("/operations/shipments");
    const listResponse = await listResponsePromise;
    expect(listResponse.status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: "محموله‌ها بر اساس اولویت اقدام" }),
    ).toBeVisible();
    await expect(
      page.getByRole("group", { name: "فیلتر صف عملیاتی" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", {
        name: /مشاهده محموله عملیاتی مشتری عملیاتی آزمایشی/,
      }),
    ).toHaveCount(1, { timeout: 30_000 });
    await expect(
      page.getByText("پیشرفت عملیات", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("مهم‌ترین موضوع", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("اقدام بعدی", { exact: true })).toBeVisible();
    await screenshot(page, "guided-shipment-priority-queue-desktop.png");
    await expectNoHorizontalOverflow(page);

    await page.setViewportSize({ width: 390, height: 844 });
    const mobileListResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" &&
        response.url().includes("/api/operational-shipments?"),
    );
    await page.reload();
    expect((await mobileListResponsePromise).status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: "محموله‌ها بر اساس اولویت اقدام" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", {
        name: /مشاهده محموله عملیاتی مشتری عملیاتی آزمایشی/,
      }),
    ).toHaveCount(1, { timeout: 30_000 });
    await expectNoHorizontalOverflow(page);
    await screenshot(page, "guided-shipment-priority-queue-mobile.png");
    expectClean(evidence);
  });

  test("five-second summary separates process progress from task readiness", async ({
    page,
  }) => {
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    const token = await page.evaluate(() =>
      localStorage.getItem("expert_token"),
    );
    const projection = await page.request.get(
      `/api/operational-shipments/${fixture.active_shipment_public_id}/operational-projection`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(projection.status()).toBe(200);
    const projectionBody = (await projection.json()).data;
    expect(projectionBody.meta.freshness).toBe("ON_REQUEST");
    expect(projectionBody.meta.rebuild).toContain("no backfill");
    expect(projectionBody.meta.projection_version).toBe(
      "guided-operational-workspace-v2",
    );
    expect(projectionBody.stage_progress.semantic).toBe(
      "OPERATIONAL_PROGRESS",
    );
    expect(projectionBody.readiness.semantic).toBe("CASE_READINESS");
    expect(projectionBody.recommended_action).toBeTruthy();
    expect(projectionBody.secondary_actions.length).toBeLessThanOrEqual(3);
    expect(
      projectionBody.tasks.every(
        (task: { category?: string; blocking?: boolean }) =>
          typeof task.category === "string" &&
          typeof task.blocking === "boolean",
      ),
    ).toBe(true);
    const blocker = projectionBody.attention.find(
      (item: { blocking: boolean }) => item.blocking,
    );
    if (blocker) {
      expect(projectionBody.recommended_action.category).not.toBe("WARNING");
    }

    await page.goto(
      `/operations/shipments/${fixture.active_shipment_public_id}/summary`,
    );
    await expect(
      page.getByRole("heading", { name: "OW-OPERATIONAL-001" }),
    ).toBeVisible();
    await expect(
      page.getByText("بهترین اقدام بعدی", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("progressbar", { name: "پیشرفت مراحل عملیاتی" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "آمادگی پرونده" }),
    ).toBeVisible();
    await expect(
      page.getByText("پیشرفت عملیات با آمادگی پرونده یکی نیست.", {
        exact: false,
      }),
    ).toBeVisible();
    await expect(
      page.getByText(/مانع|نیازمند اقدام|هشدار|اطلاعاتی/, { exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "رفتن به اقدام" })).toHaveCount(
      1,
    );
    await expect(page.getByText("آخرین موقعیت", { exact: true })).toBeVisible();
    await expect(page.getByText("ETA نهایی", { exact: true })).toBeVisible();
    await screenshot(page, "guided-shipment-five-second-summary.png");
    await expectNoHorizontalOverflow(page);
    expectClean(evidence);
  });

  test("representative all-stages-complete state ranks Final Delivery above warnings", async ({
    page,
  }) => {
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    await page.route("**/operational-projection", async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      const value = body.data;
      value.process_status = "AWAITING_CLOSURE";
      value.stage_progress = {
        ...value.stage_progress,
        completed: 5,
        total: 5,
        current: null,
        items: ["پذیرش", "برنامه‌ریزی", "بارگیری", "در مسیر", "تحویل"].map(
          (display_name_fa, index) => ({
            public_id: `representative-stage-${index + 1}`,
            code: `REPRESENTATIVE_${index + 1}`,
            display_name_fa,
            status: "COMPLETED",
            required_for_completion: true,
          }),
        ),
        semantic: "OPERATIONAL_PROGRESS",
      };
      value.attention = [
        {
          key: "closure-final_delivery_exists",
          source_code: "FINAL_DELIVERY_EXISTS",
          category: "BLOCKER",
          severity: "BLOCKER",
          blocking: true,
          precedence: "CLOSURE_BLOCKER",
          label: "تحویل نهایی محموله به‌صراحت ثبت نشده است",
          action_label: "ثبت تحویل نهایی",
          reason: "این واقعیت برای آمادگی پرونده هنوز کامل نیست.",
          section: "delivery",
        },
        {
          key: "closure-actual_cargo_unknown",
          source_code: "ACTUAL_CARGO_UNKNOWN",
          category: "WARNING",
          severity: "WARNING",
          blocking: false,
          precedence: "OPTIONAL_IMPROVEMENT",
          label: "مقدار واقعی یک یا چند کالا هنوز نامشخص است",
          action_label: "تکمیل واقعیت کالای حمل‌شده",
          reason: "این هشدار مانع ادامه چرخه نیست.",
          section: "cargo",
        },
      ];
      value.recommended_action = {
        rank: 40,
        precedence: "CLOSURE_BLOCKER",
        category: "BLOCKER",
        blocking: true,
        section: "delivery",
        label: "ثبت تحویل نهایی",
        reason: "تحویل نهایی محموله هنوز به‌صراحت ثبت نشده است.",
        href: `/operations/shipments/${fixture.active_shipment_public_id}/delivery`,
      };
      value.secondary_actions = [
        {
          rank: 50,
          precedence: "OPTIONAL_IMPROVEMENT",
          category: "WARNING",
          blocking: false,
          section: "cargo",
          label: "تکمیل واقعیت کالای حمل‌شده",
          reason: "این هشدار مانع ادامه چرخه نیست.",
          href: `/operations/shipments/${fixture.active_shipment_public_id}/cargo`,
        },
      ];
      value.readiness = {
        ...value.readiness,
        semantic: "CASE_READINESS",
        blocker_count: 1,
        warning_count: 1,
        closure_ready: false,
      };
      await route.fulfill({ response, json: body });
    });

    await page.goto(
      `/operations/shipments/${fixture.active_shipment_public_id}/summary`,
    );
    await expect(
      page.getByRole("heading", { name: "ثبت تحویل نهایی" }),
    ).toBeVisible();
    await expect(page.getByText("مانع", { exact: true })).toBeVisible();
    await expect(page.getByText("هشدار", { exact: true })).toBeVisible();
    await expect(
      page.getByText("مقدار واقعی یک یا چند کالا هنوز نامشخص است", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("progressbar", { name: "پیشرفت مراحل عملیاتی" }),
    ).toHaveAttribute("aria-valuenow", "5");
    await screenshot(page, "guided-final-delivery-before-warning.png");
    await expectNoHorizontalOverflow(page);
    expectClean(evidence);
  });

  test("expert request and quote work is guided by commercial state", async ({
    page,
  }) => {
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    await page.goto(`/expert/requests/${fixture.request_id}`);

    await expect(
      page.getByRole("heading", { name: "OW-OPERATIONAL-001" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "از درخواست تا جمع‌بندی تجاری" }),
    ).toBeVisible();
    for (const label of [
      "ثبت درخواست",
      "تخصیص کارشناس",
      "آماده‌سازی پیشنهاد",
      "پاسخ مشتری",
      "جمع‌بندی تجاری",
    ]) {
      await expect(
        page.getByText(label, { exact: true }).first(),
      ).toBeVisible();
    }
    await expect(
      page.getByText("ادامه در فضای عملیات", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "مشاهده محموله عملیاتی" }),
    ).toHaveCount(1);
    await expect(
      page.getByText("waiting_for_customer", { exact: true }),
    ).toHaveCount(0);
    await screenshot(page, "guided-expert-request-quote-workspace.png");
    await expectNoHorizontalOverflow(page);
    expectClean(evidence);
  });

  test("customer request puts the current quote and next action before detail", async ({
    page,
  }) => {
    const evidence = observe(page);
    await loginCustomer(page);
    await page.goto(`/customer/requests/${fixture.portal_request_public_id}`);

    await expect(
      page.getByRole("heading", { name: "پیگیری درخواست و پیشنهاد" }),
    ).toBeVisible();
    await expect(
      page.getByText("بررسی و پاسخ به پیشنهاد", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "مشاهده و پاسخ به پیشنهاد" }),
    ).toHaveCount(1);
    await expect(
      page.getByText("پیشنهاد جاری برای پاسخ مرورگری", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("جزئیات درخواست", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/تاریخچه پیشنهادها/).first()).toBeVisible();
    await expect(page.getByText("in_progress", { exact: true })).toHaveCount(0);
    await screenshot(page, "guided-customer-request-quote-workspace.png");
    await expectNoHorizontalOverflow(page);
    expectClean(evidence);
  });

  test("route, closure, and organization admin hierarchy remain distinct and read-only", async ({
    page,
  }) => {
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    await page.goto(
      `/operations/shipments/${fixture.active_shipment_public_id}/route`,
    );
    await expect(
      page.getByRole("heading", { name: "مسیر و اجرای عملیاتی" }),
    ).toBeVisible();
    await expect(
      page.getByText("اقدام اصلی", { exact: false }).first(),
    ).toBeVisible();
    await expect(
      page.getByText("زمان مرجع و مبنای برنامه", { exact: true }),
    ).toBeVisible();

    await page.goto(
      `/operations/shipments/${fixture.active_shipment_public_id}/closure`,
    );
    await expect(
      page.getByRole("heading", { name: "بررسی بستن پرونده" }),
    ).toBeVisible();
    await expect(
      page.getByText(/آماده بستن|هنوز آماده بستن نیست/).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("progressbar", { name: "پیشرفت آمادگی بستن" }),
    ).toBeVisible();
    await screenshot(page, "guided-closure-readiness.png");

    await loginExpert(page, fixture.usernames.admin, /\/admin$/);
    await expect(
      page.getByText("نمای کلی و گزارش", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("افراد، دسترسی و تخصیص کار", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("قواعد عملیات سازمان", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("داده و شبکه سازمان", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("حاکمیت سراسری پلتفرم", { exact: true }),
    ).toHaveCount(0);
    await screenshot(page, "guided-admin-semantic-ia.png");
    await expectNoHorizontalOverflow(page);
    expectClean(evidence);
  });
});
