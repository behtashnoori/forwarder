import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Documents E2E environment is incomplete.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  request_public_id: string;
  definition_public_id: string;
  owner_username: string;
  peer_username: string;
  admin_username: string;
};

const pdf = (marker: string) => Buffer.from(`%PDF-1.4\n1 0 obj\n<<>>\nendobj\n${marker}\n%%EOF`);
const upload = (name: string, marker = name) => ({ name, mimeType: "application/pdf", buffer: pdf(marker) });

async function login(page: Page, username: string) {
  await page.goto("/");
  const loginButton = page.getByRole("button", { name: "ورود به سامانه" }).first();
  if (!(await loginButton.isVisible())) {
    await page.getByRole("button", { name: "منوی سامانه" }).click();
  }
  await loginButton.click();
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page).not.toHaveURL(/\/$/);
}

async function openDocumentsFromConsole(page: Page) {
  await expect(page.getByText("DOC-E2E-001")).toBeVisible();
  await page.getByRole("button", { name: "مشاهده جزئیات" }).click();
  await expect(page).toHaveURL(new RegExp(`/expert/requests/${fixture.request_public_id}$`));
  await page.getByRole("tab", { name: "مستندات پرونده" }).click();
  await expect(page.getByText("سند چندفایلی آزمون")).toBeVisible();
}

const addInput = (page: Page) => page.getByLabel("افزودن فایل‌ها برای سند چندفایلی آزمون");
const queueRow = (page: Page, name: string) => page.getByTestId(`document-queue-${name}`);

test.describe.serial("Expert-only multi-file Documents", () => {
  test("desktop owner journey: append, targeted history, partial Retry, unknown and reopen", async ({ page }, testInfo) => {
    await login(page, fixture.owner_username);
    await openDocumentsFromConsole(page);

    const postedNames: string[] = [];
    let failFOnce = true;
    let abortUnknownOnce = true;
    await page.route("**/document-requirements/**/files", async (route) => {
      const body = route.request().postDataBuffer()?.toString("latin1") || "";
      const name = ["A.pdf", "B.pdf", "C.pdf", "D.pdf", "A2.pdf", "E.pdf", "F.pdf", "G.pdf", "U.pdf"]
        .find((candidate) => body.includes(`filename="${candidate}"`));
      if (name) postedNames.push(name);
      if (name === "F.pdf" && failFOnce) {
        failFOnce = false;
        await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: "storage unavailable", code: "DOCUMENT_STORAGE_UNAVAILABLE" }) });
        return;
      }
      if (name === "U.pdf" && abortUnknownOnce) {
        abortUnknownOnce = false;
        await route.abort("timedout");
        return;
      }
      await route.continue();
    });

    await addInput(page).setInputFiles([upload("A.pdf"), upload("B.pdf"), upload("C.pdf")]);
    for (const name of ["A.pdf", "B.pdf", "C.pdf"]) await expect(queueRow(page, name)).toContainText("موفق");
    await page.getByRole("button", { name: "بازگشت به کنسول" }).first().click();
    await openDocumentsFromConsole(page);
    for (const name of ["A.pdf", "B.pdf", "C.pdf"]) await expect(page.getByText(name).first()).toBeVisible();

    await addInput(page).setInputFiles(upload("D.pdf"));
    await expect(queueRow(page, "D.pdf")).toContainText("موفق");
    for (const name of ["A.pdf", "B.pdf", "C.pdf", "D.pdf"]) await expect(page.getByText(name).first()).toBeVisible();

    await page.getByLabel("جایگزینی A.pdf").setInputFiles(upload("A2.pdf"));
    await expect(queueRow(page, "A2.pdf")).toContainText("موفق");
    const a2Card = page.locator("article").filter({ hasText: "A2.pdf" }).first();
    await expect(a2Card).toContainText("نسخه مسیر 2");
    await a2Card.locator("summary").click();
    await expect(a2Card.getByText("A.pdf", { exact: false })).toBeVisible();
    for (const name of ["B.pdf", "C.pdf", "D.pdf"]) await expect(page.getByText(name).first()).toBeVisible();

    for (const target of ["A2.pdf", "A.pdf"]) {
      const row = target === "A2.pdf" ? a2Card : a2Card.locator("details").locator("div.rounded-lg").filter({ hasText: "A.pdf" });
      const response = page.waitForResponse((candidate) => candidate.url().includes("/documents/") && candidate.url().endsWith("/download"));
      await row.getByRole("button", { name: "دریافت" }).first().click();
      expect((await response).status()).toBe(200);
    }

    await addInput(page).setInputFiles([upload("E.pdf"), upload("F.pdf"), upload("G.pdf")]);
    await expect(queueRow(page, "E.pdf")).toContainText("موفق");
    await expect(queueRow(page, "F.pdf")).toContainText("ناموفق");
    await expect(queueRow(page, "G.pdf")).toContainText("موفق");
    await queueRow(page, "F.pdf").getByRole("button", { name: /تلاش دوباره فقط همین فایل/ }).click();
    await expect(queueRow(page, "F.pdf")).toContainText("موفق");
    expect(postedNames.filter((name) => name === "E.pdf")).toHaveLength(1);
    expect(postedNames.filter((name) => name === "G.pdf")).toHaveLength(1);
    expect(postedNames.filter((name) => name === "F.pdf")).toHaveLength(2);

    await addInput(page).setInputFiles(upload("U.pdf"));
    await expect(queueRow(page, "U.pdf")).toContainText("نتیجه نامشخص");
    await expect(queueRow(page, "U.pdf").getByRole("button", { name: /تلاش دوباره/ })).toHaveCount(0);
    await queueRow(page, "U.pdf").getByRole("button", { name: "تازه‌سازی و بررسی" }).click();
    expect(postedNames.filter((name) => name === "U.pdf")).toHaveLength(1);

    await page.getByRole("button", { name: "بازگشت به کنسول" }).first().click();
    await openDocumentsFromConsole(page);
    await expect(page.getByText("A2.pdf").first()).toBeVisible();
    await expect(page.getByText("B.pdf").first()).toBeVisible();
    await expect(page.getByText("C.pdf").first()).toBeVisible();
    await expect(page.getByText("D.pdf").first()).toBeVisible();
    await testInfo.attach("documents-desktop.png", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
  });

  test("mobile RTL owner journey remains reachable and responsive", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await login(page, fixture.owner_username);
    await openDocumentsFromConsole(page);
    await expect(addInput(page)).toBeAttached();
    expect(await page.locator("html").evaluate((node) => getComputedStyle(node).direction)).toBe("rtl");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    await expect(page.getByText("A2.pdf").first()).toBeVisible();
    await testInfo.attach("documents-mobile-rtl.png", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
  });

  test("Admin keeps read access but has no mutation UI and direct mutation is denied", async ({ page }, testInfo) => {
    await login(page, fixture.admin_username);
    await page.goto(`/expert/requests/${fixture.request_public_id}`);
    await page.getByRole("tab", { name: "مستندات پرونده" }).click();
    await expect(page.getByText("A2.pdf").first()).toBeVisible();
    await expect(page.getByLabel(/افزودن فایل‌ها|جایگزینی/)).toHaveCount(0);
    await expect(page.getByText("غیرفعال‌سازی")).toHaveCount(0);

    const token = await page.evaluate(() => localStorage.getItem("expert_token"));
    const list = await page.request.get(`/api/expert/requests/${fixture.request_public_id}/documents`, { headers: { Authorization: `Bearer ${token}` } });
    const requirement = (await list.json()).requirements[0];
    const denied = await page.request.post(
      `/api/expert/requests/${fixture.request_public_id}/document-requirements/${fixture.definition_public_id}/files`,
      {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          source_definition_revision: String(requirement.source_definition_revision),
          file: upload("admin-forbidden.pdf"),
        },
      },
    );
    expect(denied.status()).toBe(403);
    expect((await denied.json()).code).toBe("DOCUMENT_MUTATION_FORBIDDEN");
    await testInfo.attach("documents-admin-read-only.png", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
  });
});
