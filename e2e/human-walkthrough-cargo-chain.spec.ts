import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
const apiBase = process.env.VITE_BACKEND_URL || "http://127.0.0.1:5001";
if (!password || !fixturePath) throw new Error("Cargo chain proof requires its owned disposable runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  hw_chain_quote_id: number;
  hw_chain_request: string;
  hw_chain_request_tracking: string;
  hw_chain_request_cargo: string;
  hw_chain_catalog: string;
  hw_chain_catalog_label: string;
  hw_chain_origin: string;
  hw_chain_origin_label: string;
  hw_chain_destination: string;
  hw_chain_destination_label: string;
  p304_truck: string;
  p304_trailer: string;
  p304_carrier_a: number;
};
test.setTimeout(180_000);

type Evidence = { console: string[]; page: string[]; failed: string[]; unexpected: string[] };

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

async function headers(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("expert_token"));
  expect(token).toBeTruthy();
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

test("Accepted Request Cargo stays continuous through route, execution, allocation, and ETA", async ({ page }, testInfo) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  const evidence = observe(page);
  await login(page);

  await page.goto(`/operations/shipments/new?source=accepted_quote&accepted_quote_id=${fixture.hw_chain_quote_id}&request_ref=${fixture.hw_chain_request_tracking}`);
  await expect(page.getByLabel("کالای منبع در درخواست مشتری")).toHaveValue(fixture.hw_chain_request_cargo);
  await expect(page.getByText(/درخواست‌شده:.*۱۰۰.*عدد/)).toBeVisible();
  await page.getByLabel("مبدأ روش تعیین مکان").selectOption("facility");
  await page.getByLabel("مقصد روش تعیین مکان").selectOption("facility");
  await page.getByLabel("مبدأ operational facility").selectOption(fixture.hw_chain_origin);
  await page.getByLabel("مقصد operational facility").selectOption(fixture.hw_chain_destination);
  await page.getByLabel("Catalog item").selectOption(fixture.hw_chain_catalog);
  await page.getByLabel("Cargo quantity").fill("100");
  const now = new Date();
  const departure = new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
  const arrival = new Date(now.getTime() + 36 * 60 * 60 * 1000).toISOString().slice(0, 16);
  await page.getByLabel("زمان برنامه‌ریزی‌شده حرکت").fill(departure);
  await page.getByLabel("زمان برنامه‌ریزی‌شده رسیدن").fill(arrival);

  const creation = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith("/api/operational-shipments/from-accepted-quote"),
  );
  await page.getByRole("button", { name: "ایجاد پرونده عملیاتی", exact: true }).click();
  const creationResponse = await creation;
  expect(creationResponse.status()).toBe(201);
  const created = (await creationResponse.json()) as { data: { public_id: string } };
  const shipment = created.data.public_id;
  await expect(page).toHaveURL(new RegExp(`/operations/shipments/${shipment}$`));
  await expect(page.getByRole("heading", { name: "خلاصه محموله" })).toBeVisible();

  const cargoDetails = page.locator("details").filter({ has: page.locator("summary", { hasText: "جزئیات کالا، وسیله حمل و پیگیری" }) }).first();
  await cargoDetails.locator("summary").first().click();
  const cargoArticle = cargoDetails.getByRole("article").filter({ hasText: fixture.hw_chain_catalog_label }).first();
  await expect(cargoArticle).toContainText(`درخواست مشتری ${fixture.hw_chain_request_tracking}`);
  await expect(cargoArticle).toContainText("درخواستی100 عدد");
  await expect(cargoArticle).toContainText("برنامه‌ریزی‌شده100 عدد");
  await expect(cargoArticle).toContainText("واقعیهنوز ثبت نشده");

  const auth = await headers(page);
  const cargoResponse = await page.request.get(
    `${apiBase}/api/internal/operational-shipments/${shipment}/cargo-items`,
    { headers: auth },
  );
  expect(cargoResponse.status()).toBe(200);
  const cargoBody = (await cargoResponse.json()) as { items: Array<{ public_id: string; source_lineage: { request_public_id: string; request_cargo_item_public_id: string }; quantities: { requested: string; planned: string; actual: string | null }; uom_display: string }> };
  expect(cargoBody.items).toHaveLength(1);
  const cargo = cargoBody.items[0];
  expect(cargo.source_lineage).toMatchObject({
    request_public_id: fixture.hw_chain_request,
    request_cargo_item_public_id: fixture.hw_chain_request_cargo,
  });
  expect(cargo.quantities).toMatchObject({ requested: "100.000000", planned: "100.000000", actual: null });
  expect(cargo.uom_display).toBe("عدد");

  const plansResponse = await page.request.get(`${apiBase}/api/operational-shipments/${shipment}/route-plans`, { headers: auth });
  expect(plansResponse.status()).toBe(200);
  const plans = (await plansResponse.json()) as { data: Array<{ id: number; is_active: boolean }> };
  const planId = plans.data.find(plan => plan.is_active)?.id;
  expect(planId).toBeTruthy();
  const planResponse = await page.request.get(`${apiBase}/api/operational-shipments/${shipment}/route-plans/${planId}`, { headers: auth });
  expect(planResponse.status()).toBe(200);
  const plan = (await planResponse.json()) as { data: { legs: Array<{ id: number }>; cargo_destinations: Array<{ cargo_item_public_id: string; destination_route_leg_id: number }> } };
  expect(plan.data.legs).toHaveLength(1);
  expect(plan.data.cargo_destinations).toEqual([
    expect.objectContaining({ cargo_item_public_id: cargo.public_id, destination_route_leg_id: plan.data.legs[0].id }),
  ]);

  const executionResponse = await page.request.post(
    `${apiBase}/api/operational-shipments/${shipment}/route-plans/${planId}/legs/${plan.data.legs[0].id}/transport-executions`,
    {
      headers: { ...auth, "Idempotency-Key": "hw-cargo-chain-execution" },
      data: {
        transport_means_type_public_id: fixture.p304_truck,
        carrier_customer_id: fixture.p304_carrier_a,
        means_identifier: "HW-CHAIN-TRUCK-01",
        means_details: null,
        driver_name: null,
        driver_contact: null,
        equipment: [{ type_public_id: fixture.p304_trailer, identifier: "HW-CHAIN-TRAILER-01", details: null }],
      },
    },
  );
  expect(executionResponse.status()).toBe(201);
  const execution = (await executionResponse.json()) as { data: { public_id: string; execution_public_id: string } };
  const stageExecution = execution.data.public_id;

  const traceDetails = page.locator("details").filter({ has: page.locator("summary", { hasText: "تخصیص و مسیر هر کالا" }) }).first();
  await traceDetails.locator("summary").click();
  await traceDetails.getByRole("button", { name: "تازه‌سازی" }).click();
  await expect(traceDetails.getByLabel("اجرای حمل برای تخصیص")).toHaveValue("");
  await expect(traceDetails.getByLabel("اجرای حمل برای تخصیص").locator(`option[value="${stageExecution}"]`)).toHaveCount(1);
  await traceDetails.getByLabel("اجرای حمل برای تخصیص").selectOption(stageExecution);
  await traceDetails.getByLabel("نوع تخصیص").selectOption("PLANNED");
  await traceDetails.getByLabel("مقدار تخصیص مرحله").fill("100");
  const allocation = page.waitForResponse(response =>
    response.request().method() === "PUT" && response.url().includes(`/stage-executions/${stageExecution}/allocation`),
  );
  await traceDetails.getByRole("button", { name: "ذخیره تخصیص" }).click();
  expect((await allocation).status()).toBe(201);
  await expect(traceDetails.getByText(/جمع برنامه:.*100/).first()).toBeVisible();

  await traceDetails.getByLabel("اجرای حمل برای تخصیص").selectOption(stageExecution);
  await traceDetails.getByLabel("نوع تخصیص").selectOption("ACTUAL");
  await traceDetails.getByLabel("مقدار تخصیص مرحله").fill("95");
  const actualAllocation = page.waitForResponse(response =>
    response.request().method() === "PUT" && response.url().includes(`/stage-executions/${stageExecution}/allocation`),
  );
  await traceDetails.getByRole("button", { name: "ذخیره تخصیص" }).click();
  expect((await actualAllocation).status()).toBe(201);
  await expect(traceDetails.getByText(/جمع واقعی:.*95/).first()).toBeVisible();
  await expect(traceDetails.getByText(/مقدار واقعی این بخش.*5 عدد کمتر از برنامه است/)).toBeVisible();
  await traceDetails.locator("summary", { hasText: "تاریخچه تخصیص و انتقال" }).click();
  await expect(traceDetails.getByText(/0 ← 95 عدد/)).toBeVisible();

  const etaResponse = await page.request.post(
    `${apiBase}/api/operational-shipments/${shipment}/cargo/${cargo.public_id}/eta/ensure`,
    { headers: auth, data: {} },
  );
  expect(etaResponse.status()).toBe(200);
  const eta = (await etaResponse.json()) as { next: { reason: string }; final: { reason: string }; provenance: { mapping: unknown; legs: unknown[] } };
  expect(eta.next.reason).not.toBe("ROUTE_UNDEFINED");
  expect(eta.final.reason).not.toBe("ROUTE_UNDEFINED");
  expect(eta.next.reason).toBe("PROGRESS_UNDEFINED");
  expect(eta.provenance.mapping).toBeTruthy();
  expect(eta.provenance.legs).toHaveLength(1);

  await testInfo.attach("accepted-request-cargo-route-allocation-eta", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  expect(evidence.unexpected).toEqual([]);
  expect(evidence.failed).toEqual([]);
  expect(evidence.page).toEqual([]);
  expect(evidence.console).toEqual([]);
});
