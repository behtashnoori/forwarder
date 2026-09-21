import fs from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const fixturePath = process.env.MT3_E2E_FIXTURE_PATH;
if (!fixturePath) throw new Error("MT3_E2E_FIXTURE_PATH is required.");

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8")) as {
  capability_a: string;
  capability_b: string;
  request_a_id: number;
  request_b_id: number;
  shipment_a_id: number;
  shipment_b_id: number;
};

type BrowserEvidence = {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  unexpectedResponses: string[];
};

function observe(page: Page, expectedStatuses: number[] = []): BrowserEvidence {
  const evidence: BrowserEvidence = {
    consoleErrors: [],
    pageErrors: [],
    failedRequests: [],
    unexpectedResponses: [],
  };
  page.on("console", message => {
    const text = message.text();
    const expectedNotFoundNoise = expectedStatuses.includes(404) && text.includes("status of 404");
    if (message.type() === "error" && !expectedNotFoundNoise) evidence.consoleErrors.push(text);
  });
  page.on("pageerror", error => evidence.pageErrors.push(error.message));
  page.on("requestfailed", request => {
    evidence.failedRequests.push(`${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`);
  });
  page.on("response", response => {
    if (response.url().includes("/api/") && response.status() >= 400 && !expectedStatuses.includes(response.status())) {
      evidence.unexpectedResponses.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  return evidence;
}

function expectClean(evidence: BrowserEvidence) {
  expect(evidence.pageErrors, "uncaught page errors").toEqual([]);
  expect(evidence.failedRequests, "failed browser requests").toEqual([]);
  expect(evidence.unexpectedResponses, "unexpected API responses").toEqual([]);
  expect(evidence.consoleErrors.filter(item => !item.includes("favicon")), "console errors").toEqual([]);
}

async function expectSafeUnavailable(page: Page, value: number) {
  await page.goto(`/customer/track/${value}`);
  await expect(page.getByRole("heading", { name: "درخواست یافت نشد" })).toBeVisible();
  await expect(page.getByText("Private Browser", { exact: false })).toHaveCount(0);
}

test.describe.serial("MT-3 public tracking identity and authorization", () => {
  test("A — valid opaque capability renders the minimized desktop RTL tracking journey", async ({ page }, testInfo) => {
    const evidence = observe(page);
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await page.locator("#command-tracking").fill(fixture.capability_a);
    await page.locator("#command-tracking").press("Enter");
    await expect(page).toHaveURL(new RegExp(`/customer/track/${fixture.capability_a}$`));
    await expect(page.getByRole("heading", { name: fixture.capability_a })).toBeVisible();
    await expect(page.getByText("Shanghai، China", { exact: true })).toBeVisible();
    await expect(page.getByText("Tehran، Iran", { exact: true })).toBeVisible();
    await expect(page.getByText("MT3-CNTR-001", { exact: false })).toBeVisible();
    await expect(page.getByText("در مسیر مقصد", { exact: false })).toBeVisible();
    await expect(page.getByText("حمل ترکیبی", { exact: true })).toBeVisible();
    await expect(page.locator("body")).toContainText(/۲۰۲۶.*۱۴۰۵/);

    const response = await page.request.get(
      `/api/public/track/${fixture.capability_a}?tenant_id=999999&request_id=${fixture.request_b_id}`,
    );
    expect(response.status()).toBe(200);
    expect(response.headers()["cache-control"]).toContain("no-store");
    expect(response.headers()["referrer-policy"]).toBe("no-referrer");
    expect(response.headers()["x-robots-tag"]).toBe("noindex, nofollow");
    const body = await response.json();
    expect(Object.keys(body).sort()).toEqual([
      "assigned_at",
      "created_at",
      "domestic_transport_method",
      "international_transport_method",
      "route",
      "shipping_type",
      "status",
      "tracking_number",
      "transport_method",
      "transport_method_preference",
      "unit_tracking",
      "workflow_steps_simple",
    ]);
    const serialized = JSON.stringify(body);
    for (const forbidden of [
      '"id"',
      '"organization_id"',
      "09124444444",
      "Private Browser",
      "private-browser-expert@example.invalid",
      "Private browser origin address",
      "Private browser destination address",
      "Private browser cargo",
      "Private browser quote",
      "Private browser document",
      "private/mt3",
      "Private browser internal tracking note",
      "Private later internal note",
    ]) expect(serialized).not.toContain(forbidden);
    await page.screenshot({ path: testInfo.outputPath("valid-opaque-desktop-rtl.png"), fullPage: true });
    expectClean(evidence);
  });

  test("B/D — guessed same-tenant and foreign numeric identities disclose nothing on mobile RTL", async ({ page }, testInfo) => {
    const evidence = observe(page, [404]);
    await page.setViewportSize({ width: 390, height: 844 });
    await expectSafeUnavailable(page, fixture.request_a_id);
    await expectSafeUnavailable(page, fixture.request_b_id);
    await expectSafeUnavailable(page, fixture.shipment_b_id);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath("numeric-foreign-mobile-rtl.png"), fullPage: true });
    expectClean(evidence);
  });

  test("C — adjacent numeric enumeration has zero successes and one error contract", async ({ page }) => {
    const probes = new Set([
      1,
      2,
      3,
      10,
      100,
      9999,
      fixture.request_a_id - 1,
      fixture.request_a_id,
      fixture.request_a_id + 1,
      fixture.request_b_id,
      fixture.shipment_a_id,
      fixture.shipment_b_id,
    ]);
    let successes = 0;
    for (const probe of probes) {
      const response = await page.request.get(`/api/public/track/${probe}`);
      if (response.status() === 200) successes += 1;
      expect(response.status()).toBe(404);
      expect(await response.json()).toEqual({ message: "درخواست یافت نشد" });
    }
    expect(successes).toBe(0);
  });

  test("E — product-generated capability is opaque and opens successfully", async ({ page }, testInfo) => {
    const evidence = observe(page);
    const created = await page.request.post("/api/shipment-request", {
      data: {
        shipping_type: "international",
        origin_country: "China",
        origin_city_international: "Shenzhen",
        dest_country: "Turkey",
        dest_city_international: "Istanbul",
        contact_phone: "09126666666",
        international_transport_method: "Combined Transport",
        transport_method_preference: "customer_choice",
        cargo_items: [],
      },
    });
    expect(created.status()).toBe(201);
    const payload = await created.json();
    expect(payload.tracking_code).toMatch(/^SR2-[A-Za-z0-9_-]{22}$/);
    expect(payload.tracking_code).not.toContain(String(payload.id));

    const generatedRoute = `/customer/track/${payload.tracking_code}`;
    await page.goto(generatedRoute);
    await expect(page).toHaveURL(new RegExp(`${payload.tracking_code}$`));
    await expect(page.getByRole("heading", { name: payload.tracking_code })).toBeVisible();
    await expect(page.getByText("Shenzhen", { exact: false })).toBeVisible();
    await expect(page.getByText("Istanbul", { exact: false })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("product-generated-opaque-link.png"), fullPage: true });
    expectClean(evidence);
  });
});
