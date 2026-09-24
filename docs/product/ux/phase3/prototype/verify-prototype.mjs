import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const playwrightModule = process.env.PHASE3_PLAYWRIGHT_MODULE || "@playwright/test";
const { chromium } = await import(playwrightModule);

const baseUrl = process.env.PHASE3_PROTOTYPE_URL || "http://127.0.0.1:4179/";
const evidenceDir = path.resolve("docs/product/ux/phase3/evidence/browser");
await mkdir(evidenceDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  ...(process.env.PHASE3_BROWSER_EXECUTABLE
    ? { executablePath: process.env.PHASE3_BROWSER_EXECUTABLE }
    : {}),
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const consoleErrors = [];
const pageErrors = [];
const networkViolations = [];
const checks = [];

page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("request", (request) => {
  const url = new URL(request.url());
  if (url.hostname !== "127.0.0.1") networkViolations.push(request.url());
});

const check = async (name, action) => {
  try {
    await action();
    checks.push({ name, result: "PASS" });
  } catch (error) {
    checks.push({ name, result: "FAIL", error: error instanceof Error ? error.message : String(error) });
    throw error;
  }
};

const shot = async (name) => {
  await page.screenshot({ path: path.join(evidenceDir, name), fullPage: true });
};

try {
  await check("local prototype loads", async () => {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "پرونده حمل S-100" }).waitFor();
  });
  await shot("A-expert-shipment-overview-desktop.png");

  await check("all expert sections are reachable", async () => {
    const sections = ["مشتری‌ها و درخواست‌ها", "کالاها", "مسیر", "اجرای حمل", "تخصیص کالا", "اسناد", "اجرا و Timeline", "مشکلات و پیگیری‌ها", "تحویل‌ها", "تکمیل و بستن", "نمای کلی"];
    for (const label of sections) {
      await page.getByRole("button", { name: new RegExp(label) }).first().click();
    }
  });

  await page.getByRole("button", { name: /تخصیص کالا/ }).first().click();
  await shot("B-cargo-allocation-multi-customer.png");
  await check("over-allocation blocks while valid allocation succeeds", async () => {
    await page.getByRole("button", { name: "ثبت تخصیص" }).first().click();
    const quantity = page.getByLabel("مقدار (کارتن)");
    await quantity.fill("11");
    await quantity.press("Enter");
    await page.getByText(/over-allocation مسدود است/).waitFor();
    await quantity.fill("10");
    await quantity.press("Enter");
    await page.getByText(/10 کارتن تخصیص یافت/).waitFor();
    await page.waitForTimeout(3300);
  });

  await page.getByRole("button", { name: /^مسیر/ }).click();
  await shot("C1-planned-and-branched-route.png");
  await page.getByRole("button", { name: /اجرای حمل/ }).first().click();
  await shot("C2-route-stage-transport-execution.png");

  await page.getByRole("button", { name: /اجرا و Timeline/ }).click();
  await shot("D-timeline-reported-location-correction.png");
  await page.getByRole("button", { name: /مشکلات و پیگیری‌ها/ }).click();
  await shot("E-exception-customer-safe-explanation.png");
  await page.getByRole("button", { name: /تحویل‌ها/ }).click();
  await shot("F-partial-delivery.png");
  await page.getByRole("button", { name: /تکمیل و بستن/ }).click();
  await shot("G-closure-blocker.png");

  await page.locator('[data-role="customer"]').click();
  await check("customer projection excludes other customer identities", async () => {
    const visibleText = await page.locator("body").innerText();
    if (visibleText.includes("آرمان تجهیز شرق") || visibleText.includes("راهکار پلیمر سپهر")) {
      throw new Error("Another customer identity is visible in Customer A projection");
    }
  });
  await shot("H1-customer-shared-shipment-desktop.png");

  await page.setViewportSize({ width: 390, height: 844 });
  await check("customer 390px layout has no horizontal page overflow", async () => {
    const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
    if (dimensions.scrollWidth > dimensions.width) throw new Error(`horizontal overflow ${dimensions.scrollWidth} > ${dimensions.width}`);
  });
  await shot("H2-customer-shared-shipment-mobile-390.png");

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator('[data-role="admin"]').click();
  await shot("I-admin-reference-configuration.png");
  await check("admin can activate an organization definition concept", async () => {
    await page.locator('[data-toggle-catalog="reeferWagon"]').last().click();
    await page.getByText(/تعریف برای سازمان فعال شد/).waitFor();
    await page.waitForTimeout(3300);
  });

  await check("stale scenario is explicit and not falsely healthy", async () => {
    await page.getByText("حالت‌های رابط", { exact: true }).click();
    await page.getByRole("button", { name: /قدیمی \/ degraded/ }).click();
    await page.getByText("اطلاعات پایش به‌روز نیست").waitFor();
    await page.getByText(/نبود هشدار در این وضعیت به معنی سلامت عملیات نیست/).waitFor();
  });
  await shot("J-stale-degraded-state.png");

  await check("no production or external network dependency", async () => {
    if (networkViolations.length) throw new Error(networkViolations.join(", "));
  });
  await check("no browser console or page errors", async () => {
    if (consoleErrors.length || pageErrors.length) throw new Error([...consoleErrors, ...pageErrors].join(" | "));
  });
} finally {
  const result = {
    prototype: "TARGET_PHASE3_UX",
    url: baseUrl,
    testedAt: new Date().toISOString(),
    browser: "Chromium via Playwright",
    desktopViewport: "1440x900",
    mobileViewport: "390x844",
    syntheticDataOnly: true,
    externalNetworkRequests: networkViolations,
    consoleErrors,
    pageErrors,
    checks,
    result: checks.every((item) => item.result === "PASS") ? "PASS" : "FAIL",
  };
  await writeFile(path.join(evidenceDir, "result.json"), `${JSON.stringify(result, null, 2)}\n`, "utf8");
  await browser.close();
}

if (!checks.every((item) => item.result === "PASS")) process.exitCode = 1;
