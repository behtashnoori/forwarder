import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Product Reality retest must be launched by its local qualification runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as { shipment_a: string; shipment_b: string };

type Evidence = { console: string[]; page: string[]; failed: string[]; unexpected: string[] };
function observe(page: Page): Evidence {
  const evidence: Evidence = { console: [], page: [], failed: [], unexpected: [] };
  page.on("console", item => { if (item.type() === "error" && !item.text().includes("favicon")) evidence.console.push(item.text()); });
  page.on("pageerror", error => evidence.page.push(error.message));
  page.on("requestfailed", request => evidence.failed.push(`${request.method()} ${request.url()}`));
  page.on("response", response => { if (response.url().includes("/api/") && response.status() >= 400) evidence.unexpected.push(`${response.status()} ${response.request().method()} ${response.url()}`); });
  return evidence;
}
function clean(evidence: Evidence) {
  expect(evidence.console, "unexpected console errors").toEqual([]);
  expect(evidence.page, "unexpected page errors").toEqual([]);
  expect(evidence.failed, "unexpected failed requests").toEqual([]);
  expect(evidence.unexpected, "unexpected API failures").toEqual([]);
}
async function login(page: Page, persona: "operator" | "restricted" | "zero") {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}
async function headers(page: Page) { return page.evaluate(() => ({ Authorization: `Bearer ${localStorage.getItem("expert_token") || ""}` })); }

test.describe("Product Reality corrective retest", () => {
  test("PR-01 — route-envelope shipment list is accessible, stable, and correctly empty by scope", async ({ page }) => {
    const e = observe(page); await login(page, "operator");
    const list = await page.request.get("/api/operational-shipments", { headers: await headers(page) });
    expect(list.status()).toBe(200); const payload = await list.json() as { data: Array<{ public_id: string }> };
    expect(payload.data.some(row => row.public_id === fixture.shipment_a)).toBeTruthy();
    await page.goto("/operations/shipments");
    const cards = page.getByRole("link", { name: /مشاهده محموله عملیاتی/ });
    await expect(cards).toHaveCount(payload.data.length);
    expect(await cards.count()).toBeGreaterThan(0);
    await page.reload(); await expect(cards).toHaveCount(payload.data.length);
    await page.goto("/expert"); await page.goto("/operations/shipments"); await expect(cards).toHaveCount(payload.data.length);
    const restrictedPage = await page.context().newPage(); await login(restrictedPage, "restricted");
    const restricted = await restrictedPage.request.get(`/api/operational-shipments/${fixture.shipment_b}`, { headers: await headers(restrictedPage) });
    expect([403, 404]).toContain(restricted.status());
    await restrictedPage.close();
    clean(e);

    const zero = await page.context().newPage(); const zeroEvidence = observe(zero); await login(zero, "zero");
    await zero.goto("/operations/shipments");
    await expect(zero.getByText("محموله عملیاتی منطبق با فیلترها یافت نشد. فیلترها را پاک کنید یا نخستین محموله عملیاتی را ایجاد کنید.")).toBeVisible();
    clean(zeroEvidence); await zero.close();
  });

  test("Work Queue — unauthorized actor has no actionable surface or background request", async ({ page }) => {
    const e = observe(page); await login(page, "restricted"); await page.goto("/operations/shipments");
    await expect(page.getByRole("link", { name: "صف کار برج کنترل" })).toHaveCount(0);
    expect(e.unexpected.filter(item => item.includes("work-queue") || item.includes("attention"))).toEqual([]);
    await expect(page.getByText("You are not allowed to perform this operation.")).toHaveCount(0);
    clean(e);
  });

  test("Control Tower — normal business view hides technical formulas and semantic codes", async ({ page }) => {
    const e = observe(page); await login(page, "operator"); await page.goto("/operations/control-tower");
    await expect(page.getByRole("heading", { name: "برج کنترل عملیات" })).toBeVisible();
    const text = await page.locator("main").innerText();
    for (const forbidden of ["PARTIAL_DIMENSION_COVERAGE", "semantic_version", "query_kind", "metric_keys", "dimension_keys", "coverage_percent", "eligible_count"]) expect(text).not.toContain(forbidden);
    clean(e);
  });
});
