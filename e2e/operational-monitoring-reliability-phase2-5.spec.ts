import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { expect, test, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const expertPassword = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const evidencePath = process.env.OPERATIONAL_MONITORING_RELIABILITY_EVIDENCE_PATH;
if (!databaseUrl || !expertPassword || !fixturePath || !evidencePath) {
  throw new Error("Operational Monitoring Phase 2.5 E2E requires owned runtime inputs.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_workspace_phase2_")) {
  throw new Error("Phase 2.5 browser proof is restricted to its owned loopback database.");
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  usernames: { owner: string; admin: string };
  organization_id: number;
  active_shipment_public_id: string;
};
const backgroundActionTitle = "پیگیری پس‌زمینه بدون مرورگر";

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page): BrowserEvidence {
  const evidence: BrowserEvidence = { consoleErrors: [], pageErrors: [], failedRequests: [], unexpectedResponses: [] };
  page.on("console", message => {
    if (message.type() === "error") evidence.consoleErrors.push(message.text());
  });
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

async function screenshot(page: Page, name: string) {
  await page.screenshot({ path: path.join(evidencePath!, name), fullPage: true });
}

test("shows background-evaluated Attention, then one shared stale truth in Workspace and Control Tower", async ({ page }) => {
  test.setTimeout(180_000);
  const firstPageEvidence = observe(page);

  await loginExpert(page, fixture.usernames.owner, /\/operations$/);
  const ownerAuthorization = { Authorization: `Bearer ${await token(page)}` };
  const createdAction = await page.request.post(
    `/api/operational-shipments/${fixture.active_shipment_public_id}/actions`,
    {
      headers: ownerAuthorization,
      data: {
        what: backgroundActionTitle,
        expected_result: "ثبت نتیجه پیگیری مصنوعی پس‌زمینه",
        due_at: new Date(Date.now() - 20 * 60_000).toISOString(),
        context_type: "SHIPMENT",
      },
    },
  );
  expect(createdAction.status()).toBe(201);

  const browserContext = page.context();
  await page.close();
  const evaluation = spawnSync(
    "python",
    [
      "-m", "backend.operational_cli", "evaluate-sla",
      "--organization-id", String(fixture.organization_id), "--confirm",
    ],
    { cwd: process.cwd(), encoding: "utf8", env: process.env },
  );
  expect(evaluation.status, evaluation.stderr || evaluation.stdout).toBe(0);
  fs.writeFileSync(
    path.join(evidencePath!, "browser-closed-background-evaluation.log"),
    evaluation.stdout,
    "utf8",
  );

  const productPage = await browserContext.newPage();
  const evidence = observe(productPage);
  await loginExpert(productPage, fixture.usernames.owner, /\/operations$/);
  const workspaceResponse = await productPage.request.get("/api/operational-workspace?limit=20", {
    headers: { Authorization: `Bearer ${await token(productPage)}` },
  });
  expect(workspaceResponse.status()).toBe(200);
  expect((await workspaceResponse.json()).data.attention_items).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: "ACTION_FOLLOW_UP", why: backgroundActionTitle }),
  ]));
  await expect(productPage.getByText("اقدام عملیاتی نیاز به پیگیری دارد", { exact: true })).toBeVisible();
  await expect(productPage.getByTestId("attention-freshness-warning")).toHaveCount(0);
  await screenshot(productPage, "phase2-5-workspace-background-evaluation-fresh.png");

  await loginExpert(productPage, fixture.usernames.admin, /\/admin$/);
  const authorization = { Authorization: `Bearer ${await token(productPage)}` };
  const rulesResponse = await productPage.request.get("/api/organization-sla-rules", { headers: authorization });
  expect(rulesResponse.status()).toBe(200);
  const rules = (await rulesResponse.json()).data.rules as Array<{
    public_id: string;
    duration_minutes: number;
    version: number;
  }>;
  expect(rules.length).toBeGreaterThan(0);
  const changed = await productPage.request.patch(`/api/organization-sla-rules/${rules[0].public_id}`, {
    headers: authorization,
    data: {
      expected_version: rules[0].version,
      duration_minutes: rules[0].duration_minutes + 1,
    },
  });
  expect(changed.status()).toBe(200);

  await loginExpert(productPage, fixture.usernames.owner, /\/operations$/);
  const staleOwnerAuthorization = { Authorization: `Bearer ${await token(productPage)}` };
  const workspaceWarning = productPage.getByTestId("attention-freshness-warning");
  await expect(workspaceWarning).toBeVisible();
  await expect(workspaceWarning).toContainText("آخرین ارزیابی Attention به‌روز نیست");
  await expect(workspaceWarning).toContainText("نبود هشدار");
  await screenshot(productPage, "phase2-5-workspace-stale.png");

  const towerResponse = await productPage.request.get("/api/control-tower/shipments?page_size=25", {
    headers: staleOwnerAuthorization,
  });
  expect(towerResponse.status()).toBe(200);
  const towerPayload = await towerResponse.json();
  expect(towerPayload.data.attentionEvaluation).toMatchObject({
    state: "STALE",
    trustworthy: false,
  });
  await productPage.route("**/api/control-tower/shipments?*", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(towerPayload),
  }));
  await productPage.goto("/operations/control-tower");
  await expect(productPage.getByRole("heading", { name: "برج کنترل عملیات" })).toBeVisible();
  const towerWarning = productPage.getByTestId("control-tower-attention-freshness");
  await expect(towerWarning).toBeVisible();
  await expect(towerWarning).toContainText("ارزیابی Attention به‌روز نیست");
  await expect(towerWarning).toContainText("اثبات سلامت عملیات نیست");
  await screenshot(productPage, "phase2-5-control-tower-stale.png");
  await productPage.unroute("**/api/control-tower/shipments?*");

  expectClean(firstPageEvidence);
  expectClean(evidence);
});
