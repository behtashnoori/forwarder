import fs from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!databaseUrl || !password || !fixturePath) {
  throw new Error("ADR-047 E2E requires its disposable database, password, and fixture manifest.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_integrated_cert_fixed_shipment_owner_e2e")) {
  throw new Error("ADR-047 browser proof is restricted to the owned loopback database.");
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  usernames: { e1: string; e2: string; admin: string };
  e2_id: number;
  customer_id: number;
  request_id: number;
  request_public_id: string;
  origin_province_id: number;
  destination_identity: string;
};

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page): BrowserEvidence {
  const evidence: BrowserEvidence = {
    consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [],
  };
  page.on("console", message => {
    if (message.type() === "error") evidence.consoleErrors.push(message.text());
  });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => evidence.failedRequests.push(
    `${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`,
  ));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400 && response.status() !== 404) {
      evidence.unexpectedResponses.push(
        `${response.status()} ${response.request().method()} ${response.url()}`,
      );
    }
  });
  return evidence;
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.pageErrors, "uncaught browser page errors").toEqual([]);
  expect(evidence.failedRequests, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  expect(
    evidence.consoleErrors.filter(item => !item.includes("favicon") && !item.includes("404")),
    "browser console errors",
  ).toEqual([]);
}

async function login(page: Page, username: string, expectedLanding: RegExp) {
  await page.context().clearCookies();
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).toHaveURL(expectedLanding);
}

async function token(page: Page) {
  const value = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(value).toBeTruthy();
  return value!;
}

async function waitForControlTower(page: Page) {
  await page.getByRole("status", { name: "در حال دریافت برج کنترل" }).waitFor({
    state: "hidden",
    timeout: 120_000,
  });
}

test("A-E — accepted Quote owner stays fixed across Request reassignment", async ({ page }, testInfo) => {
  test.setTimeout(300_000);
  const evidence = observe(page);

  // Journey A: E1 issues Q1, the Customer accepts it, and the governed UI creates S.
  await login(page, fixture.usernames.e1, /\/expert$/);
  await page.goto(`/expert/requests/${fixture.request_public_id}`);
  await page.getByRole("button", { name: "ثبت قیمت" }).click();
  const quoteDialog = page.getByRole("dialog", { name: "ارسال پیشنهاد" });
  await quoteDialog.getByLabel("مبلغ (الزامی)").fill("4700000");
  await quoteDialog.getByLabel("ارز").selectOption("EUR");
  await quoteDialog.getByLabel("توضیح کوتاه (اختیاری)").fill("پیشنهاد رسمی مالک ثابت");
  await quoteDialog.getByRole("button", { name: "ارسال پیشنهاد", exact: true }).click();
  await expect(quoteDialog).toBeHidden();

  await page.goto(`/request/${fixture.request_id}?customer=${fixture.customer_id}`);
  await expect(page.getByText("پیشنهاد (قیمت)")).toBeVisible();
  await page.getByRole("button", { name: "تأیید پیشنهاد" }).click();
  await expect(page.getByText("شما این پیشنهاد را تأیید کردید")).toBeVisible();

  await page.goto(`/expert/requests/${fixture.request_public_id}`);
  await expect(page.getByText("مشتری این قیمت را تأیید کرد")).toBeVisible();
  await page.getByRole("link", { name: "ایجاد پرونده عملیاتی" }).click();
  await expect(page).toHaveURL(/\/operations\/shipments\/new/);
  await expect(page.locator("#quote")).not.toHaveValue("");
  await page.getByLabel("مبدأ روش تعیین مکان").selectOption("geography");
  await page.getByLabel("مقصد روش تعیین مکان").selectOption("geography");
  await page.getByLabel("مبدأ استان").selectOption(String(fixture.origin_province_id));
  await page.getByLabel("مقصد در ایران", { exact: true }).selectOption(fixture.destination_identity);
  await page.getByLabel("زمان برنامه‌ریزی‌شده حرکت").fill("2026-09-19T08:00");
  await page.getByLabel("زمان برنامه‌ریزی‌شده رسیدن").fill("2026-09-20T08:00");
  await page.getByRole("button", { name: "ایجاد پرونده عملیاتی" }).click();
  await expect(page).toHaveURL(/\/operations\/shipments\/[0-9a-f-]{36}$/i);
  const shipmentId = page.url().split("/").pop()!;
  await page.getByText("جزئیات عملیاتی بیشتر", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "مدارک و مراجع حمل" })).toBeVisible();

  // Give the active Shipment a real governed attention reason for Control Tower.
  const exceptionPanel = page.getByRole("heading", {
    name: "استثناهای عملیاتی ثبت‌شده",
  }).locator("..");
  await exceptionPanel.getByLabel("دلیل مصوب استثنا").selectOption({
    label: "استثنای گواهی مالک ثابت",
  });
  await exceptionPanel.getByLabel("زمان وقوع").fill("2026-09-21T12:00");
  await exceptionPanel.getByLabel("یادداشت اختیاری").fill("گواهی برج کنترل مالک ثابت");
  await exceptionPanel.getByRole("button", { name: "ثبت استثنا عملیاتی" }).click();
  await expect(exceptionPanel.locator("article").getByText(
    "استثنای گواهی مالک ثابت", { exact: true },
  )).toBeVisible();

  // Journey C: the persisted owner can mutate Shipment Documents.
  await page.getByLabel("نوع یا دسته تجاری سند").fill("بارنامه مالک ثابت");
  await page.getByLabel("انتخاب فایل سند").setInputFiles({
    name: "fixed-owner-proof.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"),
  });
  await page.getByRole("button", { name: "بارگذاری سند برای محموله" }).click();
  await expect(page.getByText("fixed-owner-proof.pdf")).toBeVisible();

  // Journey B: use the existing governed assignment command; Shipment access stays with E1.
  const e1Token = await token(page);
  const reassigned = await page.request.post(`/api/expert/requests/${fixture.request_id}/assign`, {
    headers: { Authorization: `Bearer ${e1Token}` },
    data: { expert_id: fixture.e2_id },
  });
  expect(reassigned.status()).toBe(200);
  await page.reload();
  await page.getByText("جزئیات عملیاتی بیشتر", { exact: true }).click();
  await expect(page.getByText("fixed-owner-proof.pdf")).toBeVisible();

  // Journey D: E1 retains owner-scoped Control Tower population.
  await page.goto("/operations/control-tower");
  await waitForControlTower(page);
  await expect(page.getByText(shipmentId, { exact: true })).toBeVisible();
  await expect(page.getByText(/مسئول فعلی: کارشناس مالک ثابت یک/)).toBeVisible();

  // E2 owns the mutable Request only; guessed Shipment and Document mutation stay denied.
  await login(page, fixture.usernames.e2, /\/expert$/);
  const e2Token = await token(page);
  const e2Shipment = await page.request.get(`/api/operational-shipments/${shipmentId}`, {
    headers: { Authorization: `Bearer ${e2Token}` },
  });
  expect(e2Shipment.status()).toBe(404);
  const e2Document = await page.request.post(
    `/api/internal/operational-shipments/${shipmentId}/documents`,
    {
      headers: {
        Authorization: `Bearer ${e2Token}`,
        "Idempotency-Key": "adr047-e2-forbidden-document",
      },
      multipart: {
        title: "Forbidden",
        file: {
          name: "forbidden.pdf",
          mimeType: "application/pdf",
          buffer: Buffer.from("%PDF-1.4\n%%EOF"),
        },
      },
    },
  );
  expect(e2Document.status()).toBe(404);
  await page.goto("/operations/control-tower");
  await waitForControlTower(page);
  await expect(page.getByText(shipmentId, { exact: true })).toHaveCount(0);

  // Admin oversight is preserved, but Shipment Documents remain read-only.
  await login(page, fixture.usernames.admin, /\/admin$/);
  await page.goto(`/operations/shipments/${shipmentId}`);
  await page.getByText("جزئیات عملیاتی بیشتر", { exact: true }).click();
  await expect(page.getByText("fixed-owner-proof.pdf")).toBeVisible();
  await expect(page.getByText("دسترسی شما به این بخش فقط خواندنی است.")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/operations/control-tower");
  await waitForControlTower(page);
  await expect(page.getByText(shipmentId, { exact: true })).toBeVisible();
  await expect(page.getByText(/مسئول فعلی: کارشناس مالک ثابت یک/)).toBeVisible();

  // Journey E: representative affected surface remains usable on mobile RTL.
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "برج کنترل عملیات" })).toBeVisible();
  await expect(page.getByText(shipmentId, { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("fixed-owner-control-tower-mobile-rtl.png"), fullPage: true });

  expectClean(evidence);
});
