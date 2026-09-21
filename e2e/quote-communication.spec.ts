import fs from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!databaseUrl || !password || !fixturePath) {
  throw new Error("Quote communication E2E requires its disposable database, password, and fixture manifest.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_integrated_cert_quote_communication_e2e")) {
  throw new Error("Quote communication browser proof is restricted to the owned loopback database.");
}

type Journey = {
  customer_id: number;
  request_id: number;
  request_public_id: string;
  tracking_code: string;
  quote_public_id: string;
  initial_amount: number;
  initial_currency: string;
};
const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  username: string;
  journeys: Record<"approve" | "discussion" | "reject", Journey>;
};

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page, expectedStatuses: number[] = []): BrowserEvidence {
  const evidence: BrowserEvidence = { consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [] };
  page.on("console", message => { if (message.type() === "error") evidence.consoleErrors.push(message.text()); });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => evidence.failedRequests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400 && !expectedStatuses.includes(response.status())) {
      evidence.unexpectedResponses.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  return evidence;
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.pageErrors, "uncaught browser page errors").toEqual([]);
  expect(evidence.failedRequests, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  expect(evidence.consoleErrors.filter(item => !item.includes("favicon")), "browser console errors").toEqual([]);
}

async function openCustomer(page: Page, journey: Journey) {
  await page.goto(`/request/${journey.request_id}?customer=${journey.customer_id}`);
  await expect(page.getByText("پیشنهاد (قیمت)")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
}

async function loginExpert(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(fixture.username);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).toHaveURL(/\/expert$/);
}

test.describe.serial("Simple Quote Communication", () => {
  test("A — Customer approves an official quote without entering commercial terms", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await openCustomer(page, fixture.journeys.approve);
    const actions = page.getByRole("button").filter({ hasText: /تأیید پیشنهاد|نیاز به گفتگو|رد پیشنهاد/ });
    await expect(actions).toHaveCount(3);
    await expect(page.getByRole("spinbutton")).toHaveCount(0);
    await page.getByRole("button", { name: "تأیید پیشنهاد" }).click();
    await expect(page.getByText("شما این پیشنهاد را تأیید کردید")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("quote-approved-desktop-rtl.png"), fullPage: true });
    expectClean(evidence);
  });

  test("B — Customer sends one bounded discussion message on mobile RTL", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await openCustomer(page, fixture.journeys.discussion);
    await expect(page.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
    await expect(page.getByText("کالای اول برای حمل ترکیبی")).toBeVisible();
    await expect(page.getByText("کالای دوم برای حمل ترکیبی")).toBeVisible();
    await page.getByRole("button", { name: "نیاز به گفتگو" }).click();
    const message = page.getByLabel("پیام کوتاه برای کارشناس");
    await expect(message).toHaveAttribute("maxlength", "500");
    await expect(page.getByText("این پیام مبلغ یا ارز پیشنهاد رسمی را تغییر نمی‌دهد.")).toBeVisible();
    await message.fill("لطفاً شرایط پرداخت و زمان تحویل را هماهنگ کنیم");
    await page.getByRole("button", { name: "ارسال درخواست گفتگو" }).click();
    await expect(page.getByText("برای این پیشنهاد درخواست گفتگو فرستادید")).toBeVisible();
    await expect(page.getByText("لطفاً شرایط پرداخت و زمان تحویل را هماهنگ کنیم")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("quote-discussion-mobile-rtl.png"), fullPage: true });
    expectClean(evidence);
  });

  test("C — Expert sees the message and issues a new official Quote object", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await loginExpert(page);
    await page.goto(`/expert/requests/${fixture.journeys.discussion.request_public_id}`);
    await expect(page.getByText("مشتری نیاز به گفتگو دارد")).toBeVisible();
    await expect(page.getByText("لطفاً شرایط پرداخت و زمان تحویل را هماهنگ کنیم")).toBeVisible();
    await page.getByRole("button", { name: "صدور پیشنهاد بازنگری‌شده" }).click();
    const dialog = page.getByRole("dialog", { name: "ارسال پیشنهاد" });
    await dialog.getByLabel("مبلغ (الزامی)").fill("1500000");
    await dialog.getByLabel("ارز").selectOption("USD");
    await dialog.getByLabel("توضیح کوتاه (اختیاری)").fill("پیشنهاد بازنگری‌شده رسمی");
    await dialog.getByRole("button", { name: "ارسال پیشنهاد", exact: true }).click();
    await expect(page.getByText("۱٬۵۰۰٬۰۰۰ USD")).toBeVisible();
    await expect(page.getByText("تاریخچه پیشنهادها")).toBeVisible();
    await expect(page.getByText("لطفاً شرایط پرداخت و زمان تحویل را هماهنگ کنیم")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("quote-revised-expert-desktop.png"), fullPage: true });
    expectClean(evidence);
  });

  test("D — Customer responds to Q2 while Q1 remains immutable history", async ({ page }) => {
    const evidence = observe(page);
    await openCustomer(page, fixture.journeys.discussion);
    await expect(page.getByText("۱٬۵۰۰٬۰۰۰ USD")).toBeVisible();
    await page.getByRole("button", { name: "تأیید پیشنهاد" }).click();
    await expect(page.getByText("شما این پیشنهاد را تأیید کردید")).toBeVisible();
    await expect(page.getByText("تاریخچه پیشنهادهای رسمی")).toBeVisible();
    await expect(page.getByText("لطفاً شرایط پرداخت و زمان تحویل را هماهنگ کنیم")).toBeVisible();
    expectClean(evidence);
  });

  test("E — Customer rejects and a conflicting second command is stable 409", async ({ page }) => {
    const evidence = observe(page, [409]);
    const journey = fixture.journeys.reject;
    await openCustomer(page, journey);
    await page.getByRole("button", { name: "رد پیشنهاد" }).click();
    await expect(page.getByText("شما این پیشنهاد را رد کردید")).toBeVisible();
    const conflict = await page.request.post(`/api/customer/quotes/${journey.quote_public_id}/response`, {
      data: {
        tracking_code: journey.tracking_code,
        customer_id: journey.customer_id,
        response: "accepted",
      },
    });
    expect(conflict.status()).toBe(409);
    expect((await conflict.json()).code).toBe("QUOTE_RESPONSE_CONFLICT");
    expectClean(evidence);
  });
});
