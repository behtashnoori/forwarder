import fs from "node:fs";
import path from "node:path";
import { expect, test, type Browser, type Page } from "@playwright/test";

const databaseUrl = process.env.E2E_DATABASE_URL;
const customerPassword = process.env.FORWARDER_E2E_CUSTOMER_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const evidencePath = process.env.PHASE3_FINAL_CANDIDATE_EVIDENCE_PATH;
const browserBase = process.env.PLAYWRIGHT_BASE_URL;
const replacementPassword = process.env.FORWARDER_E2E_REPLACEMENT_PASSWORD;
if (!databaseUrl || !customerPassword || !replacementPassword || !fixturePath || !evidencePath || !browserBase) {
  throw new Error("P3-15 final-candidate proof requires its owned runtime inputs.");
}
if (!databaseUrl.includes("127.0.0.1") || !databaseUrl.includes("/forwarder_workspace_phase1_")) {
  throw new Error("P3-15 browser proof is restricted to its owned loopback database.");
}

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  portal_customer_email: string;
  public_capability: string;
  recovery: { valid_token: string; expired_token: string };
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
    const expectedHttpNoise = expectedStatuses.some(status => message.text().includes(`status of ${status}`));
    if (message.type() === "error" && !expectedHttpNoise) evidence.consoleErrors.push(message.text());
  });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => evidence.failedRequests.push(
    `${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`,
  ));
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

async function chooseSelect(page: Page, controlIndex: number, optionIndex: number) {
  await page.getByRole("combobox").nth(controlIndex).click();
  await page.getByRole("option").nth(optionIndex).click();
}

async function loginCustomer(page: Page, password: string) {
  await page.goto("/customer");
  await page.locator("#customer-email").fill(fixture.portal_customer_email);
  await page.locator("#customer-password").fill(password);
  await page.locator("form").getByRole("button").first().click();
}

async function submitRecoveryToken(page: Page, token: string, password: string) {
  await page.goto(`/customer/reset-password?token=${encodeURIComponent(token)}`);
  await page.locator("#token-password").fill(password);
  await page.locator("#token-confirm").fill(password);
  await page.locator("form").getByRole("button").click();
}

test.describe.serial("P3-15 final candidate browser acceptance", () => {
  test("FWD-J01 anonymous UI intake returns an opaque public-tracking capability", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await page.goto("/");
    await page.getByRole("button", { name: "شروع یک حمل جدید" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "حمل داخلی" }).click();
    await chooseSelect(page, 0, 0);
    await chooseSelect(page, 1, 1);
    await page.getByLabel("شماره تماس").fill("09128888888");
    await page.getByRole("combobox").nth(3).click();
    await page.getByRole("option", { name: /حمل ترکیبی/ }).click();
    await page.getByRole("button", { name: "ثبت درخواست حمل" }).click();
    await expect(page.getByText("حمل ترکیبی", { exact: true })).toBeVisible();

    const createdResponse = page.waitForResponse(response =>
      response.request().method() === "POST" && response.url().endsWith("/api/shipment-request"),
    );
    await page.getByRole("button", { name: "تایید و ارسال درخواست" }).click();
    const response = await createdResponse;
    expect(response.status()).toBe(201);
    const created = await response.json() as { tracking_code: string };
    expect(created.tracking_code).toMatch(/^SR2-[A-Za-z0-9_-]{22}$/);

    await page.goto(`/customer/track/${created.tracking_code}`);
    await expect(page.getByRole("heading", { name: created.tracking_code })).toBeVisible();
    await expect(page.getByText("در انتظار بررسی", { exact: true }).first()).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("anonymous-intake-public-tracking.png"), fullPage: true });
    expectClean(evidence);
  });

  test("FWD-DEC-03 recovery proves expiry, one use, session revocation, new login, and replay denial", async ({ page, browser }: { page: Page; browser: Browser }, testInfo) => {
    const evidence = observe(page, [400, 401]);
    await loginCustomer(page, customerPassword!);
    await expect(page).toHaveURL(/\/customer\/requests$/);
    await expect(page.getByText(fixture.public_capability, { exact: true })).toBeVisible();

    const staleContext = await browser.newContext({ baseURL: browserBase, locale: "fa-IR" });
    const staleLogin = await staleContext.request.post("/api/customer/login", {
      data: { email: fixture.portal_customer_email, password: customerPassword },
    });
    expect(staleLogin.status()).toBe(200);
    expect((await staleContext.request.get("/api/customer/session")).status()).toBe(200);

    await submitRecoveryToken(page, fixture.recovery.valid_token, replacementPassword);
    await expect(page.getByRole("status")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("recovery-success.png"), fullPage: true });

    expect(await (await staleContext.request.get("/api/customer/session")).json()).toEqual({ authenticated: false });
    expect((await staleContext.request.get("/api/customer/requests")).status()).toBe(401);

    await submitRecoveryToken(page, fixture.recovery.valid_token, `${replacementPassword}Replay`);
    await expect(page.getByRole("alert")).toBeVisible();
    await submitRecoveryToken(page, fixture.recovery.expired_token, `${replacementPassword}Expired`);
    await expect(page.getByRole("alert")).toBeVisible();

    await loginCustomer(page, customerPassword!);
    await expect(page.getByRole("alert")).toBeVisible();
    await page.locator("#customer-password").fill(replacementPassword);
    await page.locator("form").getByRole("button").first().click();
    await expect(page).toHaveURL(/\/customer\/requests$/);
    await expect(page.getByText(fixture.public_capability, { exact: true })).toBeVisible();

    await page.context().clearCookies();
    await page.goto("/customer/forgot-password");
    await page.locator("#recovery-email").fill(fixture.portal_customer_email);
    await page.locator("form").getByRole("button").first().click();
    const knownResponse = await page.getByRole("status").innerText();
    await page.reload();
    await page.locator("#recovery-email").fill("missing-p315-account@example.invalid");
    await page.locator("form").getByRole("button").first().click();
    await expect(page.getByRole("status")).toHaveText(knownResponse);

    await staleContext.close();
    fs.mkdirSync(evidencePath!, { recursive: true });
    fs.writeFileSync(path.join(evidencePath!, "recovery-contract.json"), JSON.stringify({
      request_to_valid_token: "SAFE_TEST_ADAPTER",
      expired_token: "DENIED",
      single_use: "PASS",
      prior_session_revoked: "PASS",
      old_password_login: "DENIED",
      new_password_login: "PASS",
      replay: "DENIED",
      external_email_delivery: "RELEASE_UAT_EVIDENCE_REQUIRED",
    }, null, 2));
    expectClean(evidence);
  });
});
