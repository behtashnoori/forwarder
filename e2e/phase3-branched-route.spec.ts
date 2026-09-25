import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("P3-03 qualification must use its disposable local runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  p3_route_shipment: string;
  p3_route_cargo_a: string;
  p3_route_cargo_b: string;
  p3_route_foreign_logistics_point: string;
  tenant_b_cargo: string;
  tenant_b_shipment: string;
  p3_route_places: Record<"origin" | "hub" | "tehran" | "qazvin" | "deviation", { id: number; label: string }>;
};
test.setTimeout(180_000);

type Evidence = { console: string[]; page: string[]; failed: string[]; unexpected: string[] };
type Leg = {
  id: number;
  sequence_number: number;
  parent_route_leg_id: number | null;
  branch_label: string | null;
  transport_mode: string | null;
  planned_departure: string | null;
  planned_arrival: string | null;
  departure_milestone_id?: string | null;
  arrival_milestone_id?: string | null;
  origin: { canonical_reference: { source_type: string; source_id: number | string } };
  destination: { canonical_reference: { source_type: string; source_id: number | string } };
};
type Plan = {
  id: number;
  revision_number: number;
  status: string;
  is_active: boolean;
  version: number;
  is_complete: boolean;
  incomplete_fields: string[];
  legs: Leg[];
  cargo_destinations: Array<{ cargo_item_public_id: string; destination_route_leg_id: number }>;
  actual_route: Array<{ public_id: string; is_deviation: boolean; notes: string | null }>;
  actual_traversal_count: number;
  actual_deviation_count: number;
};

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

async function tokenFor(request: APIRequestContext, persona: "admin" | "foreign") {
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

async function plans(page: Page): Promise<Plan[]> {
  const response = await page.request.get(
    `/api/operational-shipments/${fixture.p3_route_shipment}/route-plans`,
    { headers: await ownerHeaders(page) },
  );
  expect(response.status()).toBe(200);
  return ((await response.json()) as { data: Plan[] }).data;
}

async function plan(page: Page, id: number): Promise<Plan> {
  const response = await page.request.get(
    `/api/operational-shipments/${fixture.p3_route_shipment}/route-plans/${id}`,
    { headers: await ownerHeaders(page) },
  );
  expect(response.status()).toBe(200);
  return ((await response.json()) as { data: Plan }).data;
}

async function waitForCatalogOption(select: Locator, label: string) {
  await expect(select.locator("option").filter({ hasText: label })).toHaveCount(1);
  await select.selectOption({ label: `استان · ${label}` });
}

async function addLeg(
  page: Page,
  values: {
    sequence: string;
    origin: string;
    destination: string;
    branch: string;
    parentId?: number;
    departure?: string;
    arrival?: string;
  },
) {
  await page.getByRole("button", { name: "افزودن بخش مسیر", exact: true }).click();
  await page.locator("#leg-seq-new").fill(values.sequence);
  if (values.parentId) await page.locator("#leg-parent-new").selectOption(String(values.parentId));
  await page.locator("#leg-branch-new").fill(values.branch);
  await waitForCatalogOption(page.locator("#leg-origin-new"), values.origin);
  await waitForCatalogOption(page.locator("#leg-destination-new"), values.destination);
  if (values.departure) {
    await page.locator("#leg-mode-new").selectOption("road");
    await page.locator("#leg-departure-new").fill(values.departure);
    await page.locator("#leg-arrival-new").fill(values.arrival!);
  }
  const saved = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith("/legs"),
  );
  await page.getByRole("button", { name: "ذخیره بخش مسیر", exact: true }).click();
  expect((await saved).status()).toBe(201);
}

async function assignCargo(page: Page, cargoId: string, optionLabel: string) {
  const select = page.locator(`#cargo-destination-${cargoId}`);
  await select.selectOption({ label: optionLabel });
  const saved = page.waitForResponse(response =>
    response.request().method() === "PUT" && response.url().includes(`/cargo-destinations/${cargoId}`),
  );
  await select.locator("xpath=../..").getByRole("button", { name: "ثبت مقصد", exact: true }).click();
  expect((await saved).status()).toBe(200);
}

test("P3-03 — progressive branched plan, actual deviation, history, and authority", async ({ page }, testInfo) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const evidence = observe(page);

  await login(page);
  await page.goto(`/operations/shipments/${fixture.p3_route_shipment}`);
  await expect(page.getByRole("heading", { name: "خلاصه محموله" })).toBeVisible();
  await page.getByRole("button", { name: "ایجاد مسیر عملیات", exact: true }).click();
  await expect(page.getByText(/پیش‌نویس برنامه مسیر/)).toBeVisible();

  await addLeg(page, {
    sequence: "1",
    origin: fixture.p3_route_places.origin.label,
    destination: fixture.p3_route_places.hub.label,
    branch: "بخش مشترک",
  });
  await expect(page.getByText(/روش حمل نامشخص/)).toBeVisible();
  await expect(page.getByText(/زمان برنامه هنوز کامل نیست/)).toBeVisible();

  await page.reload();
  await expect(page.getByText(/پیش‌نویس برنامه مسیر/)).toBeVisible();
  await expect(page.getByText(/این برنامه هنوز ناقص است/)).toBeVisible();
  const draftSummary = (await plans(page)).find(item => item.status === "draft")!;
  let draft = await plan(page, draftSummary.id);
  expect(draft.is_complete).toBe(false);
  expect(draft.legs[0]).toMatchObject({ transport_mode: null, planned_departure: null, planned_arrival: null });
  expect(draft.legs[0]).toMatchObject({ departure_milestone_id: null, arrival_milestone_id: null });

  await page.getByRole("button", { name: "ویرایش بخش مسیر", exact: true }).click();
  await page.locator(`#leg-mode-${draft.legs[0].id}`).selectOption("road");
  await page.locator(`#leg-departure-${draft.legs[0].id}`).fill("2030-01-01T08:00");
  await page.locator(`#leg-arrival-${draft.legs[0].id}`).fill("2030-01-01T10:00");
  const rootUpdated = page.waitForResponse(response =>
    response.request().method() === "PATCH" && response.url().endsWith(`/legs/${draft.legs[0].id}`),
  );
  await page.getByRole("button", { name: "ذخیره بخش مسیر", exact: true }).click();
  expect((await rootUpdated).status()).toBe(200);

  draft = await plan(page, draft.id);
  const rootId = draft.legs[0].id;
  await addLeg(page, {
    sequence: "2",
    origin: fixture.p3_route_places.hub.label,
    destination: fixture.p3_route_places.tehran.label,
    branch: "مقصد تهران",
    parentId: rootId,
    departure: "2030-01-01T11:00",
    arrival: "2030-01-01T13:00",
  });
  await addLeg(page, {
    sequence: "3",
    origin: fixture.p3_route_places.hub.label,
    destination: fixture.p3_route_places.qazvin.label,
    branch: "مقصد قزوین",
    parentId: rootId,
    departure: "2030-01-01T11:00",
    arrival: "2030-01-01T14:00",
  });
  draft = await plan(page, draft.id);
  const tehran = draft.legs.find(item => item.branch_label === "مقصد تهران")!;
  const qazvin = draft.legs.find(item => item.branch_label === "مقصد قزوین")!;

  const foreignCargo = await page.request.put(
    `/api/operational-shipments/${fixture.p3_route_shipment}/route-plans/${draft.id}/cargo-destinations/${fixture.tenant_b_cargo}`,
    { headers: await ownerHeaders(page), data: { destination_route_leg_id: tehran.id } },
  );
  expect(foreignCargo.status()).toBe(404);
  const foreignLocation = await page.request.post(
    `/api/operational-shipments/${fixture.p3_route_shipment}/route-plans/${draft.id}/legs`,
    {
      headers: await ownerHeaders(page),
      data: {
        sequence_number: 4,
        parent_route_leg_id: rootId,
        origin: { source_type: "province", source_id: fixture.p3_route_places.hub.id },
        destination: { source_type: "logistics_point", source_id: fixture.p3_route_foreign_logistics_point },
      },
    },
  );
  expect(foreignLocation.status()).toBe(404);

  const adminToken = await tokenFor(page.request, "admin");
  const adminMutation = await page.request.post(
    `/api/operational-shipments/${fixture.p3_route_shipment}/route-plans`,
    { headers: { Authorization: `Bearer ${adminToken}` }, data: {} },
  );
  expect(adminMutation.status()).toBe(403);
  const foreignToken = await tokenFor(page.request, "foreign");
  const foreignRoute = await page.request.post(
    `/api/operational-shipments/${fixture.p3_route_shipment}/route-plans`,
    { headers: { Authorization: `Bearer ${foreignToken}` }, data: {} },
  );
  expect(foreignRoute.status()).toBe(404);

  await assignCargo(page, fixture.p3_route_cargo_a, "بخش 2 · مقصد تهران");
  await assignCargo(page, fixture.p3_route_cargo_b, "بخش 3 · مقصد قزوین");
  await page.getByRole("button", { name: "بررسی و اعتبارسنجی مسیر", exact: true }).click();
  await expect(page.getByText("مسیر برای فعال‌سازی معتبر است.", { exact: true })).toBeVisible();
  const activated = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith(`/route-plans/${draft.id}/activate`),
  );
  await page.getByRole("button", { name: "فعال‌سازی مسیر", exact: true }).click();
  expect((await activated).status()).toBe(200);

  await expect(page.getByRole("heading", { name: "بخش مسیر 1 · بخش مشترک", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "بخش مسیر 2 · مقصد تهران", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "بخش مسیر 3 · مقصد قزوین", exact: true })).toBeVisible();
  const cargoBranches = page.getByRole("heading", { name: "مقصد شاخه‌ای کالاها", exact: true }).locator("..");
  await expect(cargoBranches).toContainText("[P3-03-E2E] کالای مقصد تهران");
  await expect(cargoBranches).toContainText("[P3-03-E2E] کالای مقصد قزوین");
  const activatedPlan = await plan(page, draft.id);
  expect(new Set(activatedPlan.cargo_destinations.map(item => item.cargo_item_public_id))).toEqual(
    new Set([fixture.p3_route_cargo_a, fixture.p3_route_cargo_b]),
  );
  const plannedSnapshot = activatedPlan.legs.map(item => ({
    id: item.id,
    parent: item.parent_route_leg_id,
    branch: item.branch_label,
    departure: item.planned_departure,
    arrival: item.planned_arrival,
    origin: item.origin.canonical_reference,
    destination: item.destination.canonical_reference,
  }));

  await page.getByRole("button", { name: "افزودن پیمایش واقعی", exact: true }).click();
  await page.locator("#actual-planned-leg").selectOption(String(tehran.id));
  await waitForCatalogOption(page.locator("#actual-route-destination"), fixture.p3_route_places.deviation.label);
  await page.getByRole("button", { name: "اکنون", exact: true }).click();
  await page.getByLabel("یادداشت (اختیاری)").fill("انحراف واقعی بدون ایجاد خودکار استثنا");
  const actualRecorded = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith(`/route-plans/${draft.id}/actual-route`),
  );
  await page.getByRole("button", { name: "ثبت واقعیت پیمایش", exact: true }).click();
  expect((await actualRecorded).status()).toBe(201);
  await expect(page.getByText("متفاوت از برنامه", { exact: true })).toBeVisible();
  await expect(page.getByText(/تفاوت مسیر به‌تنهایی مورد استثنا ایجاد نمی‌کند/)).toBeVisible();

  const afterActual = await plan(page, draft.id);
  expect(afterActual.legs.map(item => ({
    id: item.id,
    parent: item.parent_route_leg_id,
    branch: item.branch_label,
    departure: item.planned_departure,
    arrival: item.planned_arrival,
    origin: item.origin.canonical_reference,
    destination: item.destination.canonical_reference,
  }))).toEqual(plannedSnapshot);
  expect(afterActual.actual_route).toEqual([
    expect.objectContaining({ is_deviation: true, notes: "انحراف واقعی بدون ایجاد خودکار استثنا" }),
  ]);
  const exceptions = await page.request.get(
    `/api/operational-shipments/${fixture.p3_route_shipment}/route-exceptions?status=open`,
    { headers: await ownerHeaders(page) },
  );
  expect(exceptions.status()).toBe(200);
  expect(((await exceptions.json()) as { data: unknown[] }).data).toEqual([]);

  await page.locator("summary", { hasText: "جزئیات عملیاتی بیشتر" }).click();
  await page.getByLabel("دلیل بازبرنامه‌ریزی").fill("اصلاح برنامه آینده پس از ثبت مسیر واقعی");
  const replanned = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith(`/route-plans/${draft.id}/replan`),
  );
  await page.getByRole("button", { name: "بازبرنامه‌ریزی بخش‌های آینده", exact: true }).click();
  expect((await replanned).status()).toBe(201);
  const history = await plans(page);
  const source = history.find(item => item.id === draft.id)!;
  const current = history.find(item => item.is_active)!;
  expect(source).toMatchObject({ revision_number: 1, status: "superseded", actual_traversal_count: 1, actual_deviation_count: 1 });
  expect(current).toMatchObject({ revision_number: 2, status: "active", actual_traversal_count: 0, actual_deviation_count: 0 });
  const sourceDetail = await plan(page, source.id);
  const currentDetail = await plan(page, current.id);
  expect(sourceDetail.actual_route).toHaveLength(1);
  expect(currentDetail.actual_route).toHaveLength(0);
  expect(currentDetail.cargo_destinations).toHaveLength(2);
  expect(currentDetail.legs.map(item => item.branch_label)).toEqual(["بخش مشترک", "مقصد تهران", "مقصد قزوین"]);

  await page.reload();
  await expect(page.getByRole("heading", { name: "بخش مسیر 2 · مقصد تهران", exact: true })).toBeVisible();
  await page.locator("summary", { hasText: "جزئیات عملیاتی بیشتر" }).click();
  await expect(page.getByText("نسخه مسیر 1", { exact: true })).toBeVisible();
  await expect(page.getByText("نسخه مسیر 2", { exact: true })).toBeVisible();
  await expect(page.getByText(/واقعیت‌های پیمایش: 1 · انحراف‌های ثبت‌شده: 1/)).toBeVisible();
  expect(await page.locator("html").getAttribute("dir")).toBe("rtl");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await testInfo.attach("p3-03-branched-route-reopened", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  expect(evidence.unexpected, "unexpected API failures").toEqual([]);
  expect(evidence.failed, "unexpected failed requests").toEqual([]);
  expect(evidence.page, "unexpected page errors").toEqual([]);
  expect(evidence.console, "unexpected console errors").toEqual([]);
});
