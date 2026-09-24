import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const expertPassword = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const evidencePath = process.env.OPERATIONAL_WORKSPACE_EVIDENCE_PATH;
if (!databaseUrl || !expertPassword || !fixturePath || !evidencePath) {
  throw new Error("Operational Workspace Phase 2 E2E requires owned runtime inputs.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_workspace_phase2_")) {
  throw new Error("Phase 2 browser proof is restricted to its owned loopback database.");
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  usernames: { owner: string; foreign: string; admin: string };
  active_shipment_public_id: string;
  exception_rule_public_id: string;
  phase2_exception_public_ids: string[];
};

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page, expectedStatuses: number[] = []): BrowserEvidence {
  const evidence: BrowserEvidence = { consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [] };
  page.on("console", message => {
    const expectedHttpNoise = expectedStatuses.some(status => message.text().includes(`status of ${status}`));
    if (message.type() === "error" && !expectedHttpNoise) evidence.consoleErrors.push(message.text());
  });
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
  expect(evidence.pageErrors, "uncaught browser errors").toEqual([]);
  expect(evidence.failedRequests, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  expect(evidence.consoleErrors.filter(item => !item.includes("favicon")), "browser console errors").toEqual([]);
}

async function loginExpert(page: Page, username: string, landing: RegExp) {
  await page.context().clearCookies();
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole("button", { name: /ورود/ }).first().click();
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور").fill(expertPassword!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).toHaveURL(landing);
}

async function token(page: Page) {
  const value = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(value).toBeTruthy();
  return value!;
}

async function reconcile(page: Page) {
  const response = await page.request.post("/api/oip/reconcile", {
    headers: { Authorization: `Bearer ${await token(page)}` },
    data: {},
  });
  expect(response.status()).toBe(200);
}

async function screenshot(page: Page, name: string) {
  await page.screenshot({ path: path.join(evidencePath!, name), fullPage: true });
}

test.describe.serial("Operational Workspace Phase 2 governed browser proof", () => {
  test("organization admin creates and versions tenant-owned SLA rules", async ({ page }) => {
    const evidence = observe(page, [403]);
    await loginExpert(page, fixture.usernames.admin, /\/admin$/);
    await page.getByRole("tab", { name: "SLA سازمان" }).click();
    await expect(page.getByRole("heading", { name: "قواعد SLA سازمان" })).toBeVisible();
    await expect(page.getByText("SLA تعریف نشده", { exact: true })).toHaveCount(1);

    await page.getByLabel("مدت پیگیری اقدام عملیاتی").fill("30");
    await page.getByLabel("هشدار پیگیری اقدام عملیاتی").fill("10");
    await page.getByRole("button", { name: "ایجاد قاعده", exact: true }).click();
    await expect(page.getByText("فعال · نسخه 1", { exact: true })).toHaveCount(2);

    await page.getByLabel("مدت رسیدگی به استثنای عملیاتی").fill("90");
    await page.getByRole("button", { name: "ذخیره نسخه جدید", exact: true }).first().click();
    await expect(page.getByText("فعال · نسخه 2", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "نمایش تاریخچه", exact: true }).first().click();
    await expect(page.getByText(/تغییر ·/).first()).toBeVisible();
    await screenshot(page, "phase2-sla-administration.png");

    await loginExpert(page, fixture.usernames.foreign, /\/operations$/);
    const denied = await page.request.get("/api/organization-sla-rules", {
      headers: { Authorization: `Bearer ${await token(page)}` },
    });
    expect(denied.status()).toBe(403);
    expectClean(evidence);
  });

  test("workspace explains healthy, warning, and breached SLA without false SLA attention", async ({ page }) => {
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    await expect(page.getByText("SLA نقض شده", { exact: true })).toBeVisible();
    await expect(page.getByText("SLA نقض شده است", { exact: true })).toBeVisible();
    await expect(page.getByText("SLA به مرز هشدار نزدیک شده است", { exact: true })).toBeVisible();
    await expect(page.getByText(/بر اساس قاعده «پاسخ به استثنای مصنوعی»/).first()).toBeVisible();

    const workspace = await page.request.get("/api/operational-workspace?limit=20", {
      headers: { Authorization: `Bearer ${await token(page)}` },
    });
    expect(workspace.status()).toBe(200);
    const body = await workspace.json();
    const commitments = body.data.active_shipments
      .find((item: { public_id: string }) => item.public_id === fixture.active_shipment_public_id)
      .sla.commitments;
    expect(commitments.map((item: { status: string }) => item.status).sort()).toEqual(["BREACHED", "WARNING", "WITHIN"]);
    expect(body.data.attention_items.filter((item: { kind: string }) => item.kind === "SLA_COMMITMENT_RISK")).toHaveLength(2);
    await screenshot(page, "phase2-workspace-sla-attention.png");
    expectClean(evidence);
  });

  test("expert records exception evidence, follows and resolves an Action, and keeps history", async ({ page }) => {
    test.setTimeout(120_000);
    const evidence = observe(page);
    await loginExpert(page, fixture.usernames.owner, /\/operations$/);
    await page.getByRole("link", { name: /مشاهده محموله مشتری عملیاتی آزمایشی/ }).click();
    await expect(page).toHaveURL(new RegExp(`/operations/shipments/${fixture.active_shipment_public_id}$`));
    await page.getByText("جزئیات عملیاتی بیشتر", { exact: true }).click();
    await expect(page.getByRole("heading", { name: "مسائل عملیاتی" })).toBeVisible();

    const note = "استثنای مرورگری Phase 2";
    const impact = "توقف هماهنگی تحویل تا دریافت تأیید طرف عملیاتی";
    const proof = "تماس ثبت‌شده مصنوعی و گزارش وضعیت شماره ۴";
    const exceptionSection = page.getByRole("heading", { name: "استثناهای عملیاتی ثبت‌شده" }).locator("xpath=..");
    await exceptionSection.getByLabel("دلیل مصوب استثنا").selectOption({ label: "اختلال هماهنگی مصنوعی" });
    await exceptionSection.getByLabel("زمان وقوع").fill(new Date(Date.now() - 60_000).toISOString().slice(0, 16));
    await exceptionSection.getByLabel("یادداشت اختیاری").fill(note);
    await exceptionSection.getByLabel("اثر بر عملیات").fill(impact);
    await exceptionSection.getByLabel("شواهد موجود").fill(proof);
    const createException = exceptionSection.getByRole("button", { name: "ثبت استثنا عملیاتی", exact: true });
    await expect(createException).toBeEnabled();
    await createException.click();
    const exceptionCard = page.getByText(note, { exact: true }).locator("xpath=ancestor::article");
    await expect(exceptionCard.getByText(impact, { exact: false })).toBeVisible();
    await expect(exceptionCard.getByText(proof, { exact: false })).toBeVisible();

    const actionTitle = "پیگیری تأیید طرف عملیاتی";
    await page.getByLabel("چه کاری لازم است؟").fill(actionTitle);
    await page.getByLabel("نتیجه مورد انتظار").fill("تأیید کتبی طرف عملیاتی ثبت شود");
    await page.getByLabel("موعد").fill(new Date(Date.now() - 120_000).toISOString().slice(0, 16));
    await page.getByLabel("زمینه").selectOption("EXCEPTION");
    const linkedException = page.getByLabel("استثنای مرتبط");
    const conditionsResponse = await page.request.get(
      `/api/v2/operational-shipments/${fixture.active_shipment_public_id}/execution/exceptions`,
      { headers: { Authorization: `Bearer ${await token(page)}` } },
    );
    expect(conditionsResponse.status()).toBe(200);
    const createdException = (await conditionsResponse.json()).data.find(
      (item: { note: string }) => item.note === note,
    );
    expect(createdException?.public_id).toBeTruthy();
    await linkedException.selectOption(createdException.public_id);
    await page.getByRole("button", { name: "ثبت اقدام", exact: true }).click();

    const actionCard = page.getByText(actionTitle, { exact: true }).locator("xpath=ancestor::article");
    await expect(actionCard.getByText("مسئول داخلی: کارشناس مالک ثابت", { exact: false })).toBeVisible();
    await expect(actionCard.getByText("تأیید کتبی طرف عملیاتی ثبت شود", { exact: false })).toBeVisible();
    await actionCard.getByLabel(`یادداشت پیگیری ${actionTitle}`).fill("تماس اول انجام شد و پاسخ در انتظار است");
    await actionCard.getByRole("button", { name: "ثبت پیگیری", exact: true }).click();
    await expect(actionCard.getByText("تماس اول انجام شد و پاسخ در انتظار است", { exact: false })).toBeVisible();

    await reconcile(page);
    const actionWorkspace = await page.request.get("/api/operational-workspace?limit=20", {
      headers: { Authorization: `Bearer ${await token(page)}` },
    });
    expect(actionWorkspace.status()).toBe(200);
    expect((await actionWorkspace.json()).data.attention_items).toEqual(expect.arrayContaining([
      expect.objectContaining({ kind: "ACTION_FOLLOW_UP", why: actionTitle }),
    ]));
    await page.getByRole("link", { name: "فضای کار امروز", exact: true }).click();
    await expect(page.getByText("اقدام عملیاتی نیاز به پیگیری دارد", { exact: true })).toBeVisible();
    const towerResponse = await page.request.get("/api/control-tower/shipments?page_size=25", {
      headers: { Authorization: `Bearer ${await token(page)}` },
    });
    expect(towerResponse.status()).toBe(200);
    const towerPayload = await towerResponse.json();
    const towerItem = towerPayload.data.items.find(
      (item: { key: string }) => item.key === fixture.active_shipment_public_id,
    );
    expect(towerItem).toBeTruthy();
    const towerSemantics = [towerItem.primaryReason, ...towerItem.additionalReasons]
      .map((reason: { semantic: string }) => reason.semantic);
    expect(towerSemantics).toEqual(expect.arrayContaining(["sla_breach", "action_follow_up"]));
    await page.route("**/api/control-tower/shipments?*", route => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(towerPayload),
    }));
    await page.goto("/operations/control-tower");
    await expect(page.getByRole("heading", { name: "برج کنترل عملیات" })).toBeVisible();
    const towerCardLink = page.getByRole("link", { name: "مشاهده جزئیات محموله" }).first();
    await expect(towerCardLink).toBeVisible();
    await screenshot(page, "phase2-control-tower.png");
    await page.unroute("**/api/control-tower/shipments?*");

    await page.goto(`/operations/shipments/${fixture.active_shipment_public_id}`);
    await page.getByText("جزئیات عملیاتی بیشتر", { exact: true }).click();
    const refreshedAction = page.getByText(actionTitle, { exact: true }).locator("xpath=ancestor::article");
    await refreshedAction.getByLabel(`نتیجه اقدام ${actionTitle}`).fill("تأیید کتبی دریافت و در پرونده ثبت شد");
    await refreshedAction.getByRole("button", { name: "ثبت نتیجه و بستن", exact: true }).click();
    await expect(refreshedAction.getByText("رفع‌شده", { exact: true })).toBeVisible();
    await refreshedAction.getByRole("button", { name: "تاریخچه اقدام", exact: true }).click();
    await expect(refreshedAction.getByText(/created ·/)).toBeVisible();
    await expect(refreshedAction.getByText(/follow_up_recorded ·/)).toBeVisible();
    await expect(refreshedAction.getByText(/resolved ·/)).toBeVisible();
    await expect(exceptionCard).toContainText("فعال");
    await exceptionCard.getByRole("button", { name: "رفع استثنا", exact: true }).click();
    await expect(exceptionCard).toContainText("رفع‌شده");
    await screenshot(page, "phase2-exception-action-history.png");
    expectClean(evidence);
  });
});
