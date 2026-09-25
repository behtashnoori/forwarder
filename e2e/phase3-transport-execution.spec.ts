import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("P3-04 qualification must use its disposable local runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p304_shipment: string;
  p304_project: string;
  p304_plan: number;
  p304_road_leg: number;
  p304_rail_leg: number;
  p304_foreign_leg: number;
  p304_truck: string;
  p304_train: string;
  p304_foreign_means: string;
  p304_trailer: string;
  p304_wagon: string;
  p304_container: string;
  p304_foreign_equipment: string;
  p304_carrier_a: number;
  p304_carrier_b: number;
  p304_foreign_carrier: number;
  p304_carrier_a_label: string;
  p304_carrier_b_label: string;
  tenant_b_shipment: string;
};
test.setTimeout(180_000);

type Evidence = { console: string[]; page: string[]; failed: string[]; unexpected: string[] };
type CreatedExecution = { data: { execution_public_id: string; unit_version: number } };

function observe(page: Page): Evidence {
  const result: Evidence = { console: [], page: [], failed: [], unexpected: [] };
  page.on("console", item => {
    if (item.type() === "error" && !item.text().includes("favicon")) {
      result.console.push(`${item.text()} @ ${item.location().url || "unknown"}`);
    }
  });
  page.on("pageerror", error => result.page.push(error.message));
  page.on("requestfailed", request => result.failed.push(`${request.method()} ${request.url()}`));
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      result.unexpected.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  return result;
}

async function login(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  await page.getByLabel("نام کاربری").fill("shared_transport_e2e_restricted");
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}

async function tokenFor(request: APIRequestContext, persona: "admin" | "zero" | "platform") {
  const response = await request.post("/api/expert/auth/login", {
    data: { username: `shared_transport_e2e_${persona}`, password },
  });
  expect(response.status()).toBe(200);
  return ((await response.json()) as { tokens: { access_token: string } }).tokens.access_token;
}

async function ownerHeaders(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(token).toBeTruthy();
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function openShipmentThroughNavigation(page: Page) {
  await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  const shipment = page.locator(`a[href="/operations/shipments/${fixture.p304_shipment}"]`);
  await expect(shipment).toBeVisible();
  await shipment.click();
  await expect(page.getByRole("heading", { name: "خلاصه محموله" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "وسیله و شرکت حمل هر بخش مسیر" })).toBeVisible();
}

function stage(page: Page, name: string): Locator {
  return page.getByRole("heading", { name, exact: true }).locator("xpath=..");
}

async function openCreateForm(targetStage: Locator) {
  const details = targetStage.locator("details").filter({ hasText: "افزودن اجرای حمل دیگر" });
  if ((await details.getAttribute("open")) === null) {
    await details.locator("summary", { hasText: "افزودن اجرای حمل دیگر" }).click();
  }
  await expect(details.getByLabel("نوع وسیله حمل")).toBeVisible();
  return details;
}

async function createRoadExecution(
  page: Page,
  targetStage: Locator,
  values: { carrier: string; meansIdentifier: string; equipmentIdentifier: string },
) {
  const form = await openCreateForm(targetStage);
  await form.getByLabel("نوع وسیله حمل").selectOption({ label: "کامیون آزمایشی" });
  await form.getByLabel("شرکت حمل").selectOption({ label: values.carrier });
  await form.getByLabel("شناسه وسیله حمل").fill(values.meansIdentifier);
  await form.getByRole("button", { name: "افزودن واحد یا ظرف", exact: true }).click();
  await form.getByLabel("نوع واحد حمل 1").selectOption({ label: "تریلر آزمایشی" });
  if (values.equipmentIdentifier) {
    await form.getByLabel("شناسه واحد حمل 1").fill(values.equipmentIdentifier);
  }
  const saved = page.waitForResponse(response =>
    response.request().method() === "POST"
    && response.url().endsWith(`/legs/${fixture.p304_road_leg}/transport-executions`),
  );
  await form.getByRole("button", { name: "ثبت اجرای حمل", exact: true }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  return (await response.json()) as CreatedExecution;
}

async function createRailExecution(page: Page, targetStage: Locator) {
  const form = await openCreateForm(targetStage);
  await form.getByLabel("نوع وسیله حمل").selectOption({ label: "قطار آزمایشی" });
  await form.getByLabel("شرکت حمل").selectOption({ label: fixture.p304_carrier_a_label });
  await form.getByLabel("شناسه وسیله حمل").fill("TRAIN-C");
  await form.getByRole("button", { name: "افزودن واحد یا ظرف", exact: true }).click();
  await form.getByLabel("نوع واحد حمل 1").selectOption({ label: "واگن آزمایشی" });
  await form.getByLabel("شناسه واحد حمل 1").fill("WAGON-01");
  await form.getByRole("button", { name: "افزودن واحد یا ظرف", exact: true }).click();
  await form.getByLabel("نوع واحد حمل 2").selectOption({ label: "کانتینر آزمایشی" });
  await form.getByLabel("شناسه واحد حمل 2").fill("CONT-01");
  const saved = page.waitForResponse(response =>
    response.request().method() === "POST"
    && response.url().endsWith(`/legs/${fixture.p304_rail_leg}/transport-executions`),
  );
  await form.getByRole("button", { name: "ثبت اجرای حمل", exact: true }).click();
  expect((await saved).status()).toBe(201);
}

test("P3-04 — stage executions, progressive detail, rail chain, history, and scope", async ({ page }, testInfo) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const evidence = observe(page);

  await login(page);
  await openShipmentThroughNavigation(page);
  let roadStage = stage(page, "بخش مسیر 1 · جاده چین تا مرز");
  let railStage = stage(page, "بخش مسیر 2 · ریل خورگوس تا آکتائو");
  const first = await createRoadExecution(page, roadStage, {
    carrier: fixture.p304_carrier_a_label,
    meansIdentifier: "TRUCK-A",
    equipmentIdentifier: "",
  });
  await expect(roadStage.getByText(/برخی جزئیات اجرایی هنوز مشخص نیست/)).toBeVisible();
  await expect(roadStage.getByText(/این وضعیت، مسئله عملیاتی محسوب نمی‌شود/)).toBeVisible();

  const headers = await ownerHeaders(page);
  const oldEvent = await page.request.post(
    `/api/v2/projects/${fixture.p304_project}/execution-units/${first.data.execution_public_id}/events`,
    {
      headers: { ...headers, "Idempotency-Key": "p304-browser-event-truck-a" },
      data: { expected_version: 1, internal_note: "رویداد ثبت‌شده زیر کامیون A" },
    },
  );
  expect(oldEvent.status()).toBe(201);

  await createRoadExecution(page, roadStage, {
    carrier: fixture.p304_carrier_b_label,
    meansIdentifier: "TRUCK-18",
    equipmentIdentifier: "TRAILER-18",
  });
  await createRailExecution(page, railStage);

  await openShipmentThroughNavigation(page);
  roadStage = stage(page, "بخش مسیر 1 · جاده چین تا مرز");
  railStage = stage(page, "بخش مسیر 2 · ریل خورگوس تا آکتائو");
  await expect(roadStage.getByRole("article")).toHaveCount(2);
  await expect(roadStage.getByRole("article").filter({ hasText: "TRUCK-A" })).toContainText(fixture.p304_carrier_a_label);
  await expect(roadStage.getByRole("article").filter({ hasText: "TRUCK-18" })).toContainText(fixture.p304_carrier_b_label);
  const railCard = railStage.getByRole("article").filter({ hasText: "TRAIN-C" });
  await expect(railCard).toContainText("قطار آزمایشی");
  await expect(railCard).toContainText("واگن آزمایشی · WAGON-01");
  await expect(railCard).toContainText("کانتینر آزمایشی · CONT-01");
  await expect(railCard.getByText("شرکت حمل", { exact: true }).first()).toBeVisible();
  await expect(railCard.getByText("وسیله حمل", { exact: true }).first()).toBeVisible();
  await expect(railCard.getByText("واحد / ظرف حمل 1", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/پس از آن، کالا را در بخش تخصیص همان مسیر ثبت کنید/)).toBeVisible();

  const firstCard = roadStage.getByRole("article").filter({ hasText: "TRUCK-A" });
  await firstCard.locator("summary", { hasText: "تکمیل یا تغییر اطلاعات" }).click();
  await firstCard.getByLabel("شرکت حمل").selectOption({ label: fixture.p304_carrier_b_label });
  await firstCard.getByLabel("شناسه وسیله حمل").fill("TRUCK-B");
  await firstCard.getByLabel("شناسه واحد حمل 1").fill("TRAILER-B");
  await firstCard.getByLabel("دلیل تغییر اجرای حمل").fill("تعویض کامیون در مرز");
  const revised = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().includes("/revisions"),
  );
  await firstCard.getByRole("button", { name: "ثبت نسخه تازه", exact: true }).click();
  expect((await revised).status()).toBe(201);
  roadStage = stage(page, "بخش مسیر 1 · جاده چین تا مرز");
  const revisedCard = roadStage.getByRole("article").filter({ hasText: "TRUCK-B" });
  await expect(revisedCard).toContainText(fixture.p304_carrier_b_label);
  await expect(revisedCard).toContainText("تریلر آزمایشی · TRAILER-B");
  await revisedCard.locator("summary", { hasText: "سابقه تغییرات (1)" }).click();
  await expect(revisedCard).toContainText("TRUCK-A");
  await expect(revisedCard).toContainText("تعویض کامیون در مرز");

  const timeline = await page.request.get(
    `/api/v2/projects/${fixture.p304_project}/execution-units/${first.data.execution_public_id}/timeline`,
    { headers },
  );
  expect(timeline.status()).toBe(200);
  const timelineBody = (await timeline.json()) as {
    data: Array<{ transport_context: { means_identifier: string; revision_number: number } }>;
  };
  expect(timelineBody.data).toHaveLength(1);
  expect(timelineBody.data[0].transport_context).toMatchObject({
    means_identifier: "TRUCK-A",
    revision_number: 1,
  });
  const exceptions = await page.request.get(
    `/api/operational-shipments/${fixture.p304_shipment}/route-exceptions?status=open`,
    { headers },
  );
  expect(exceptions.status()).toBe(200);
  expect(((await exceptions.json()) as { data: unknown[] }).data).toEqual([]);

  const adminToken = await tokenFor(page.request, "admin");
  const adminHeaders = { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" };
  for (const [resource, publicId] of [
    ["transport-means-types", fixture.p304_truck],
    ["transport-equipment-types", fixture.p304_trailer],
  ] as const) {
    const deactivated = await page.request.post(
      `/api/admin/organization-reference-catalog/${resource}/${publicId}/deactivate`,
      { headers: adminHeaders, data: { version: 1 } },
    );
    expect(deactivated.status()).toBe(200);
  }
  await page.reload();
  roadStage = stage(page, "بخش مسیر 1 · جاده چین تا مرز");
  await expect(roadStage.getByRole("article").filter({ hasText: "TRUCK-B" })).toContainText("کامیون آزمایشی");
  const postDeactivateForm = await openCreateForm(roadStage);
  await expect(postDeactivateForm.getByLabel("نوع وسیله حمل").locator("option", { hasText: "کامیون آزمایشی" })).toHaveCount(0);
  await postDeactivateForm.getByRole("button", { name: "افزودن واحد یا ظرف", exact: true }).click();
  await expect(postDeactivateForm.getByLabel("نوع واحد حمل 1").locator("option", { hasText: "تریلر آزمایشی" })).toHaveCount(0);

  const createUrl = `/api/operational-shipments/${fixture.p304_shipment}/route-plans/${fixture.p304_plan}/legs/${fixture.p304_road_leg}/transport-executions`;
  const validBase = {
    transport_means_type_public_id: fixture.p304_train,
    carrier_customer_id: fixture.p304_carrier_a,
    equipment: [],
  };
  const foreignCarrier = await page.request.post(createUrl, {
    headers: { ...headers, "Idempotency-Key": "p304-browser-foreign-carrier" },
    data: { ...validBase, carrier_customer_id: fixture.p304_foreign_carrier },
  });
  expect(foreignCarrier.status()).toBe(403);
  const foreignMeans = await page.request.post(createUrl, {
    headers: { ...headers, "Idempotency-Key": "p304-browser-foreign-means" },
    data: { ...validBase, transport_means_type_public_id: fixture.p304_foreign_means },
  });
  expect(foreignMeans.status()).toBe(409);
  const foreignEquipment = await page.request.post(createUrl, {
    headers: { ...headers, "Idempotency-Key": "p304-browser-foreign-equipment" },
    data: { ...validBase, equipment: [{ type_public_id: fixture.p304_foreign_equipment }] },
  });
  expect(foreignEquipment.status()).toBe(409);
  const foreignLeg = await page.request.post(
    `/api/operational-shipments/${fixture.p304_shipment}/route-plans/${fixture.p304_plan}/legs/${fixture.p304_foreign_leg}/transport-executions`,
    {
      headers: { ...headers, "Idempotency-Key": "p304-browser-foreign-leg" },
      data: validBase,
    },
  );
  expect(foreignLeg.status()).toBe(404);
  const foreignShipment = await page.request.get(
    `/api/operational-shipments/${fixture.tenant_b_shipment}/transport-execution-options`,
    { headers },
  );
  expect(foreignShipment.status()).toBe(404);
  const adminMutation = await page.request.post(createUrl, {
    headers: { ...adminHeaders, "Idempotency-Key": "p304-browser-admin-denied" },
    data: validBase,
  });
  expect(adminMutation.status()).toBe(403);
  const platformToken = await tokenFor(page.request, "platform");
  const platformMutation = await page.request.post(createUrl, {
    headers: { Authorization: `Bearer ${platformToken}`, "Idempotency-Key": "p304-browser-platform-denied" },
    data: validBase,
  });
  expect(platformMutation.status()).toBe(403);
  const nonOwnerToken = await tokenFor(page.request, "zero");
  const nonOwnerMutation = await page.request.post(createUrl, {
    headers: { Authorization: `Bearer ${nonOwnerToken}`, "Idempotency-Key": "p304-browser-nonowner" },
    data: validBase,
  });
  expect([403, 404]).toContain(nonOwnerMutation.status());
  const guessedExecution = await page.request.post(
    `/api/operational-shipments/${fixture.p304_shipment}/route-plans/${fixture.p304_plan}/transport-executions/00000000-0000-0000-0000-000000000404/revisions`,
    {
      headers: { ...headers, "Idempotency-Key": "p304-browser-guessed-execution" },
      data: { ...validBase, expected_version: 1 },
    },
  );
  expect(guessedExecution.status()).toBe(404);

  expect(await page.locator("html").getAttribute("dir")).toBe("rtl");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await testInfo.attach("p3-04-route-stage-transport-execution", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  expect(evidence.unexpected, "unexpected API failures").toEqual([]);
  expect(evidence.failed, "unexpected failed requests").toEqual([]);
  expect(evidence.page, "unexpected page errors").toEqual([]);
  expect(evidence.console, "unexpected console errors").toEqual([]);
});
