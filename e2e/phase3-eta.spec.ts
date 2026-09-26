import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Owned P3-11 runner required");
type Case = { shipment: string; cargo: string; plan: number; private_cargo: string | null; report: string | null;
  location: string; basis: string; references: { public_id: string; id: number }[] };
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p311_cases: Record<string, Case>; p311_accounts: Record<string, { email: string; public_id: string }> };
type Estimate = { available: boolean; earliest: string | null; latest: string | null; reason: string | null };
type Snapshot = { public_id: string; sequence: number; next: Estimate; final: Estimate; as_of: string;
  planned_distance: null; source_fingerprint?: string; provenance?: unknown };
test.setTimeout(240_000);

async function login(page: Page, persona: string) {
  await page.goto("/"); await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}
async function open(page: Page, item: Case, customer = false) {
  await page.getByRole("link", { name: customer ? "حمل‌های من" : "پرونده‌های عملیاتی حمل", exact: true }).first().click();
  await page.locator(`a[href="/${customer ? "customer" : "operations"}/shipments/${item.shipment}"]`).click();
  const response = page.waitForResponse(r => r.url().includes(`/cargo/${item.cargo}/eta/ensure`) && r.status() === 200);
  await page.locator("summary", { hasText: customer ? /^زمان تقریبی رسیدن کالا$/ : "زمان تقریبی رسیدن کالاها" }).click();
  const value = await (await response).json() as Snapshot;
  await expect(page.getByRole("region", { name: "زمان تقریبی رسیدن کالا", exact: true })).toContainText("زمان محاسبه:");
  return value;
}
function range(value: Estimate, basis: string, lower: number, upper: number) {
  expect(value.available).toBe(true);
  expect(Date.parse(value.earliest!) - Date.parse(basis)).toBe(lower * 3_600_000);
  expect(Date.parse(value.latest!) - Date.parse(basis)).toBe(upper * 3_600_000);
}
async function command(page: Page, path: string, body: unknown) {
  const token = await page.evaluate(() => localStorage.getItem("expert_token"));
  return page.request.post(path, { headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() }, data: body });
}
async function refresh(page: Page, item: Case) {
  const response = page.waitForResponse(r => r.url().includes(`/cargo/${item.cargo}/eta/ensure`) && r.status() === 200);
  await page.getByRole("button", { name: "تازه‌سازی برآورد", exact: true }).click();
  return await (await response).json() as Snapshot;
}

test("P3-11 Expert normal navigation: stop placement, independent unknowns, completion, history and mobile", async ({ browser }, info) => {
  const context = await browser.newContext(); const page = await context.newPage();
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await login(page, "restricted");
  const cases = fixture.p311_cases;
  const start = await open(page, cases.departure);
  range(start.next, cases.departure.basis, 1, 2); range(start.final, cases.departure.basis, 6, 12);
  const root = page.getByRole("region", { name: "زمان تقریبی رسیدن کالا", exact: true });
  await expect(root).toContainText("فاصله برنامه‌ریزی‌شده: تعریف نشده");
  await expect(root).toContainText("مدت عملیات پس از رسیدن به مقصد نهایی در آن حساب نمی‌شود");
  await root.screenshot({ path: info.outputPath("expert-arrival-ranges.png") });
  for (const [name, low, high] of [["arrived", 5, 10], ["complete", 2, 3], ["next_departure", 1, 2], ["zero", 1, 2]] as const) {
    const value = await open(page, cases[name]);
    range(value.next, cases[name].basis, low, high); range(value.final, cases[name].basis, low, high);
  }
  const unknown = await open(page, cases.unknown);
  expect(unknown.next.reason).toBe("REFERENCE_UNDEFINED"); expect(unknown.final.available).toBe(false);
  const partial = await open(page, cases.missing_later);
  range(partial.next, cases.missing_later.basis, 5, 10); expect(partial.final.reason).toBe("REFERENCE_UNDEFINED");
  expect((await open(page, cases.origin)).next.reason).toBe("DEPARTURE_UNDEFINED");
  expect((await open(page, cases.destination)).final.reason).toBe("DESTINATION_REACHED");
  expect((await open(page, cases.split)).next.reason).toBe("PROGRESS_AMBIGUOUS");
  const item = cases.arrived;
  const before = await open(page, item);
  const correctedAt = new Date(Date.parse(item.basis) - 3_600_000).toISOString();
  const correction = await command(page, `/api/operational-shipments/${item.shipment}/reported-facts`, {
    scope: "CARGO", target_public_id: item.cargo, kind: "LOCATION", source: "CARRIER_REPORT",
    occurred_at: correctedAt, location: { canonical_location_public_id: item.location },
    impacted_cargo_public_ids: [item.cargo], corrects_public_id: item.report, reason: "Synthetic occurrence correction" });
  expect(correction.status()).toBe(201);
  const after = await refresh(page, item); range(after.next, correctedAt, 5, 10);
  expect(after.public_id).not.toBe(before.public_id);
  await page.getByRole("button", { name: "برآوردهای قبلی", exact: true }).click();
  await expect(root.getByText(/برآورد قبلی/)).toHaveCount(2);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await root.screenshot({ path: info.outputPath("expert-history-mobile.png") });
  await page.setViewportSize({ width: 1280, height: 900 });
  const reopened = await open(page, item); expect(reopened.public_id).toBe(after.public_id);
  expect(errors).toEqual([]); await context.close();
});

test("P3-11 Customer normal navigation, safe own-Cargo basis, partial ETA and private source exclusion", async ({ browser }, info) => {
  const context = await browser.newContext(); const page = await context.newPage();
  await page.goto("/customer");
  await page.locator("#customer-email").fill(fixture.p311_accounts.a.email);
  await page.locator("#customer-password").fill(password!);
  const loggedIn = page.waitForResponse(r => r.url().endsWith("/api/customer/login"));
  await page.locator("form button").first().click(); expect((await loggedIn).status()).toBe(200);
  await expect(page).toHaveURL(/\/customer\/requests/);
  const cases = fixture.p311_cases;
  const complete = await open(page, cases.complete, true);
  range(complete.next, cases.complete.basis, 5, 10); // private operation completion cannot shorten Customer ETA
  const value = await open(page, cases.missing_later, true);
  range(value.next, cases.missing_later.basis, 5, 10); expect(value.final.available).toBe(false);
  expect(value.provenance).toBeUndefined(); expect(value.source_fingerprint).toBeUndefined();
  expect(value.planned_distance).toBeNull();
  await expect(page.locator("body")).not.toContainText("PRIVATE");
  const root = page.getByRole("region", { name: "زمان تقریبی رسیدن کالا", exact: true });
  await root.screenshot({ path: info.outputPath("customer-independent-results.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await root.screenshot({ path: info.outputPath("customer-mobile.png") });
  const own = await open(page, cases.arrived, true);
  await expect(page.locator("body")).not.toContainText("PRIVATE");
  const path = `/api/customer/shipments/${cases.arrived.shipment}/cargo/${cases.arrived.private_cargo}/eta`;
  expect((await page.request.post(`${path}/ensure`, { data: {} })).status()).toBe(404);
  expect((await page.request.get(`${path}/history`)).status()).toBe(404);
  const returned = await open(page, cases.arrived, true); expect(returned.public_id).toBe(own.public_id);
  expect((await open(page, cases.origin, true)).next.reason).toBe("DEPARTURE_UNDEFINED");
  expect((await open(page, cases.split, true)).next.reason).toBe("PROGRESS_AMBIGUOUS");
  await context.close();
  const otherContext = await browser.newContext(); const other = await otherContext.newPage();
  await other.goto("/customer");
  await other.locator("#customer-email").fill(fixture.p311_accounts.b.email);
  await other.locator("#customer-password").fill(password!);
  const otherLoggedIn = other.waitForResponse(r => r.url().endsWith("/api/customer/login"));
  await other.locator("form button").first().click(); expect((await otherLoggedIn).status()).toBe(200);
  await expect(other).toHaveURL(/\/customer\/requests/);
  const privateItem = { ...cases.arrived, cargo: cases.arrived.private_cargo! };
  expect((await open(other, privateItem, true)).next.available).toBe(false);
  const forbidden = `/api/customer/shipments/${cases.arrived.shipment}/cargo/${cases.arrived.cargo}/eta`;
  expect((await other.request.post(`${forbidden}/ensure`, { data: {} })).status()).toBe(404);
  expect((await other.request.get(`${forbidden}/history`)).status()).toBe(404);
  await otherContext.close();
});

test("P3-11 applicable reference changes append history and leave P3-10 plan pins intact", async ({ browser }) => {
  const context = await browser.newContext(); const page = await context.newPage();
  const adminContext = await browser.newContext(); const admin = await adminContext.newPage();
  await login(page, "restricted"); await login(admin, "admin");
  const item = fixture.p311_cases.zero;
  const before = await open(page, item); range(before.next, item.basis, 1, 2);
  const root = `/api/operational-shipments/${item.shipment}`;
  const token = await page.evaluate(() => localStorage.getItem("expert_token"));
  const pins = async () => (await (await page.request.get(`${root}/route-plans/${item.plan}/reference-times`,
    { headers: { Authorization: `Bearer ${token}` } })).json()).data.items.map((row: { selected: Record<string, unknown> | null }) => {
      if (!row.selected) return null;
      // P3-10 closes the old applicability interval when a new version is
      // created. The selected identity and its fixed durations must remain.
      const { reference, ...selection } = row.selected;
      const { effective_until: intervalEnd, ...fixedReference } = reference as Record<string, unknown>;
      expect(intervalEnd === null || typeof intervalEnd === "string").toBe(true);
      return { ...selection, reference: fixedReference };
    });
  const originalPins = await pins();
  expect((await command(admin, `/api/admin/organization-route-reference-times/${item.references[1].public_id}/versions`, {
    expected_version: 1, movement_min_minutes: 180, movement_max_minutes: 240,
    stop_min_minutes: 0, stop_max_minutes: 0, effective_from: new Date(Date.now() + 2000).toISOString() })).status()).toBe(201);
  await expect.poll(async () => (await refresh(page, item)).public_id, { timeout: 20_000 }).not.toBe(before.public_id);
  const after = await refresh(page, item); range(after.next, item.basis, 3, 4);
  expect(await pins()).toEqual(originalPins);
  const history = await page.request.get(`${root}/cargo/${item.cargo}/eta/history`, { headers: { Authorization: `Bearer ${token}` } });
  const rows = (await history.json()).items as Snapshot[];
  expect(rows.find(row => row.public_id === before.public_id)?.next).toEqual(before.next);
  await page.getByRole("button", { name: "برآوردهای قبلی", exact: true }).click();
  await expect(page.getByRole("region", { name: "زمان تقریبی رسیدن کالا", exact: true }).getByText(/برآورد قبلی/)).toHaveCount(2);
  await context.close(); await adminContext.close();
});
