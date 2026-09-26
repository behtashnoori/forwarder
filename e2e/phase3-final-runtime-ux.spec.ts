import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Use the owned P3-14 qualification runner");

const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p304_shipment: string;
  p309_accounts: Record<string, { email: string; public_id: string }>;
};

test.setTimeout(180_000);

async function loginExpert(page: Page, persona: "restricted" | "admin") {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}

async function loginCustomer(page: Page, account: "a") {
  await page.goto("/customer");
  await page.locator("#customer-email").fill(fixture.p309_accounts[account].email);
  await page.locator("#customer-password").fill(password!);
  await page.locator("form button").first().click();
  await expect(page).toHaveURL(/\/customer\/requests/);
}

async function token(page: Page) {
  const value = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(value).toBeTruthy();
  return value!;
}

test("P3-14 Expert context navigation and Workspace/Tower shared truth", async ({ browser }, info) => {
  const context = await browser.newContext({ locale: "fa-IR" });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await loginExpert(page, "restricted");

  const authorization = { Authorization: `Bearer ${await token(page)}` };
  const workspaceResponse = await page.request.get("/api/operational-workspace?limit=20", { headers: authorization });
  const towerResponse = await page.request.get("/api/control-tower/shipments?page_size=100", { headers: authorization });
  expect(workspaceResponse.status()).toBe(200);
  expect(towerResponse.status()).toBe(200);
  const workspace = await workspaceResponse.json();
  const tower = await towerResponse.json();
  expect(tower.data.attentionEvaluation.sourceWatermark).toBe(
    workspace.meta.attention_projection.source_watermark,
  );

  const workspaceTruth = new Map<string, unknown>(
    workspace.data.attention_items
      .filter((item: { truth?: { fingerprint: string } }) => item.truth)
      .map((item: { truth: { fingerprint: string } }) => [item.truth.fingerprint, item.truth]),
  );
  const towerTruth = tower.data.items.flatMap((item: { primaryReason: unknown; additionalReasons: unknown[] }) =>
    [item.primaryReason, ...item.additionalReasons],
  ).filter((reason: { truth?: { fingerprint: string } }) => reason.truth);
  const matching = towerTruth.find((reason: { truth: { fingerprint: string } }) =>
    workspaceTruth.has(reason.truth.fingerprint),
  );
  expect(matching, "at least one shared governed Attention fact").toBeTruthy();
  const workspaceMatch = workspaceTruth.get(matching.truth.fingerprint) as {
    rank: { policy_id: string; policy_version: string; urgency: string; severity: string; priority: string };
    freshness: { status: string; calculated_at: string; source_watermark: string };
  };
  expect(matching.truth.rank).toEqual({
    policyId: workspaceMatch.rank.policy_id,
    policyVersion: workspaceMatch.rank.policy_version,
    urgency: workspaceMatch.rank.urgency,
    severity: workspaceMatch.rank.severity,
    priority: workspaceMatch.rank.priority,
  });
  expect(matching.truth.freshness).toEqual({
    status: workspaceMatch.freshness.status,
    calculatedAt: workspaceMatch.freshness.calculated_at,
    sourceWatermark: workspaceMatch.freshness.source_watermark,
  });

  await page.goto(`/operations/shipments/${fixture.p304_shipment}`);
  await expect(page.getByRole("heading", { name: "خلاصه محموله", exact: true })).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "بخش‌های پرونده حمل" });
  await expect(navigation.getByRole("link", { name: "اقدام بعدی", exact: true })).toHaveAttribute("href", "#shipment-next-action");
  await expect(navigation.getByRole("link", { name: "تکمیل و بستن", exact: true })).toHaveAttribute("href", "#shipment-closure");
  await expect(page.getByText("مرحله فعلی و تازگی پرونده", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("expert-shipment-mobile-rtl.png"), fullPage: true });
  expect(errors).toEqual([]);
  await context.close();
});

test("P3-14 Organization Admin reaches account support through normal navigation", async ({ browser }, info) => {
  const context = await browser.newContext({ locale: "fa-IR" });
  const page = await context.newPage();
  await loginExpert(page, "admin");
  const support = page.getByRole("button", { name: "پشتیبانی حساب‌های پرتال", exact: true });
  await expect(support).toBeVisible();
  await support.click();
  await expect(page).toHaveURL(/\/admin\/customer-portal-accounts$/);
  await expect(page.getByRole("heading", { name: "پشتیبانی حساب‌های پرتال مشتری" })).toBeVisible();
  await page.getByLabel("جستجوی حساب پرتال").fill(fixture.p309_accounts.a.email);
  await page.getByRole("button", { name: "جستجو", exact: true }).click();
  await expect(page.getByText(fixture.p309_accounts.a.email, { exact: true })).toBeVisible();
  const recovery = page.getByRole("button", { name: "ارسال ایمیل بازیابی", exact: true });
  await expect(recovery).toHaveCount(1);
  await expect(recovery).toBeEnabled();
  await recovery.click();
  await expect(page.getByText(/ارسال واقعی ایمیل در این محیط غیرفعال است|ایمیل بازیابی برای تحویل به سرویس ایمیل سپرده شد/)).toBeVisible();
  await page.screenshot({ path: info.outputPath("admin-account-support.png"), fullPage: true });
  await context.close();
});

test("P3-14 Customer mobile projection keeps section navigation and privacy", async ({ browser }, info) => {
  const context = await browser.newContext({ locale: "fa-IR", viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await loginCustomer(page, "a");
  await page.getByRole("link", { name: "حمل‌های من", exact: true }).click();
  await page.locator(`a[href="/customer/shipments/${fixture.p304_shipment}"]`).click();
  await expect(page.getByRole("heading", { name: "کالاهای من", exact: true })).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "بخش‌های پرونده حمل مشتری" });
  await expect(navigation).toBeVisible();
  await expect(navigation.getByRole("link", { name: "اسناد", exact: true })).toHaveAttribute("href", "#customer-shipment-documents");
  await expect(navigation.getByRole("link", { name: "تحویل", exact: true })).toHaveAttribute("href", "#customer-shipment-deliveries");
  await expect(page.getByText("این حمل به‌صورت مشترک انجام می‌شود.", { exact: true })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("PRIVATE");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("customer-shipment-mobile-navigation.png"), fullPage: true });
  await context.close();
});
