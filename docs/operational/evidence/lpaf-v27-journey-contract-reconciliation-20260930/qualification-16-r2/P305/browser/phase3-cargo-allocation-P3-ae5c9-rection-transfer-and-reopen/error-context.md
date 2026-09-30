# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phase3-cargo-allocation.spec.ts >> P3-05 — normal Chrome Cargo plan, actual, correction, transfer and reopen
- Location: e2e\phase3-cargo-allocation.spec.ts:39:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('details').filter({ has: locator('summary').filter({ hasText: 'تخصیص و مسیر هر کالا' }) }).first().getByRole('heading', { name: 'تخصیص و مسیر هر کالا' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" locator('details').filter({ has: locator('summary').filter({ hasText: 'تخصیص و مسیر هر کالا' }) }).first().getByRole('heading', { name: 'تخصیص و مسیر هر کالا' }) with timeout 5000ms
  - waiting for locator('details').filter({ has: locator('summary').filter({ hasText: 'تخصیص و مسیر هر کالا' }) }).first().getByRole('heading', { name: 'تخصیص و مسیر هر کالا' })

```

```yaml
- region "Notifications (F8)":
  - list
- region "Notifications alt+T"
- navigation "ناوبری برنامه":
  - button "بازگشت":
    - img
    - text: بازگشت
  - button "خانه":
    - img
    - text: خانه
- main:
  - link "پرش به محتوای پرونده حمل":
    - /url: "#shipment-overview"
  - link "← بازگشت به فضای کار امروز":
    - /url: /operations
  - link "→ بازگشت":
    - /url: /operations/shipments
  - paragraph: فضای کار عملیاتی محموله
  - heading "خلاصه محموله" [level=1]
  - paragraph: "شناسه محموله: 7aebf82b-caf1-4d4c-acd3-cb01fb9a572f"
  - text: برنامه‌ریزی‌شده
  - paragraph: مشتری و پروژه
  - paragraph: "[SHARED-E2E] Customer A"
  - link "مشاهده پروژه مرتبط":
    - /url: /operations/projects/e0146370-6b0e-44c0-9d57-82d7f4e181d1/units
  - paragraph: مسئول فعلی پرونده
  - paragraph: "[SHARED-E2E] restricted"
  - paragraph: مالکیت از خود محموله خوانده می‌شود.
  - paragraph: مسیر فعال
  - paragraph: چین آزمایشی ← آکتائو آزمایشی
  - paragraph: نسخه 1
  - paragraph: مسیر حمل
  - paragraph: جاده‌ای ← ریلی
  - paragraph: آخرین رخداد عملیاتی
  - paragraph: هنوز رخدادی ثبت نشده
  - paragraph: مرحله فعلی و تازگی پرونده
  - paragraph: مرحله جاری ثبت نشده
  - paragraph: "آخرین تغییر پرونده: ۳۰ سپتامبر ۲۰۲۶ (۸ مهر ۱۴۰۵) · ۱۰:۳۹ (‎+۳:۳۰ گرینویچ)"
  - paragraph: موارد باز
  - paragraph: 0 مورد پیگیری · 0 استثنا
  - paragraph: عملیات مستقیم
  - navigation "عملیات حمل":
    - link "فضای کار امروز":
      - /url: /operations
    - link "درخواست‌ها و قیمت‌ها":
      - /url: /expert
    - link "پرونده‌های عملیاتی حمل":
      - /url: /operations/shipments
    - link "برج کنترل عملیات":
      - /url: /operations/control-tower
    - link "عملیات جدید":
      - /url: /operations/shipments/new
      - img
      - text: عملیات جدید
    - region "اطلاعات سامانه":
      - paragraph: Forwarder 1.10.0
  - navigation "بخش‌های پرونده حمل":
    - link "خلاصه":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/summary
    - link "مسیر و اجرا":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/route
    - link "کالا و تخصیص":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/cargo
    - link "اسناد":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/documents
    - link "پیگیری و ETA":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/tracking
    - link "تحویل":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/delivery
    - link "تکمیل و بستن":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/closure
    - link "تاریخچه":
      - /url: /operations/shipments/7aebf82b-caf1-4d4c-acd3-cb01fb9a572f/history
  - region "کالا و تخصیص":
    - paragraph: فضای کار محموله
    - heading "کالا و تخصیص" [level=2]
    - group: تخصیص و مسیر هر کالا
  - group:
    - text: جزئیات کالا، وسیله حمل و پیگیری
    - heading "کالا، مشتری و درخواست منبع" [level=3]
    - group: افزودن ردیف کالا
    - article:
      - strong: قطعات موتور
      - text: ردیف 1
      - paragraph:
        - text: "نوع ثبت‌شده:"
        - strong: قطعات موتور
      - paragraph:
        - text: "مشتری کالا:"
        - strong: "[SHARED-E2E] Customer A"
      - paragraph:
        - text: "منبع:"
        - strong: ثبت مستقیم
      - paragraph:
        - text: درخواستی
        - strong: نامشخص
      - paragraph:
        - text: برنامه‌ریزی‌شده
        - strong: 100 کارتن
      - paragraph:
        - text: واقعی
        - strong: 95 کارتن
      - paragraph: "بسته‌بندی: نامشخص · HS: نامشخص"
      - paragraph: "وزن ناخالص: نامشخص · حجم: نامشخص"
      - paragraph: "اطلاعات قابل تکمیل: HS، نوع بسته‌بندی، وزن، حجم"
      - group: تکمیل یا اصلاح اطلاعات
      - button "تاریخچه برنامه و مقدار واقعی"
    - heading "وضعیت و پیگیری حمل" [level=3]
    - paragraph: پیگیری حمل هنوز فعال نشده است.
    - button "فعال‌سازی پیگیری حمل"
```

# Test source

```ts
  1   | import { expect, test, type Locator, type Page } from "@playwright/test";
  2   | import { readFileSync } from "node:fs";
  3   | import { openShipmentSection } from "./helpers/shipment-workspace";
  4   | 
  5   | const password = process.env.FORWARDER_E2E_PASSWORD;
  6   | const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
  7   | if (!password || !fixturePath) throw new Error("P3-05 browser test requires an owned synthetic fixture.");
  8   | const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  9   |   p304_shipment: string; p305_cargo: string; p305_first: string; p305_second: string; p305_third: string; tenant_b_cargo: string;
  10  | };
  11  | test.setTimeout(180_000);
  12  | 
  13  | async function openShipment(page: Page) {
  14  |   await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  15  |   await page.locator(`a[href="/operations/shipments/${fixture.p304_shipment}"]`).click();
  16  |   await expect(page.getByRole("heading", { name: "خلاصه محموله" })).toBeVisible();
  17  |   await openShipmentSection(page, "cargo", fixture.p304_shipment);
  18  | }
  19  | 
  20  | async function openTrace(page: Page): Promise<Locator> {
  21  |   const details = page.locator("details").filter({ has: page.locator("summary", { hasText: "تخصیص و مسیر هر کالا" }) }).first();
  22  |   if (!(await details.getAttribute("open"))) await details.locator("summary").click();
> 23  |   await expect(details.getByRole("heading", { name: "تخصیص و مسیر هر کالا" })).toBeVisible();
      |                                                                                ^ Error: expect(locator).toBeVisible() failed
  24  |   await expect(details.getByLabel("کالا برای ردگیری")).toHaveValue(fixture.p305_cargo);
  25  |   return details;
  26  | }
  27  | 
  28  | async function save(page: Page, trace: Locator, stage: string, dimension: "PLANNED" | "ACTUAL", quantity: string, reason = "") {
  29  |   await trace.getByLabel("اجرای حمل برای تخصیص").selectOption(stage);
  30  |   await trace.getByLabel("نوع تخصیص").selectOption(dimension);
  31  |   await trace.getByLabel("مقدار تخصیص مرحله").fill(quantity);
  32  |   await trace.getByLabel("دلیل اصلاح تخصیص").fill(reason);
  33  |   const response = page.waitForResponse(item => item.request().method() === "PUT" && item.url().includes(`/stage-executions/${stage}/allocation`));
  34  |   await trace.getByRole("button", { name: "ذخیره تخصیص" }).click();
  35  |   expect((await response).status()).toBe(201);
  36  |   await expect(trace.getByText(/تخصیص ثبت شد؛ اختلاف‌ها فقط هشدار هستند/)).toBeVisible();
  37  | }
  38  | 
  39  | test("P3-05 — normal Chrome Cargo plan, actual, correction, transfer and reopen", async ({ page }) => {
  40  |   await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  41  |   await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  42  |   const errors: string[] = [];
  43  |   page.on("pageerror", error => errors.push(error.message));
  44  |   page.on("console", item => { if (item.type() === "error" && !item.text().includes("favicon")) errors.push(item.text()); });
  45  |   await page.goto("/");
  46  |   await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  47  |   await page.getByLabel("نام کاربری").fill("shared_transport_e2e_restricted");
  48  |   await page.getByLabel("رمز عبور").fill(password!);
  49  |   await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  50  |   await openShipment(page);
  51  |   let trace = await openTrace(page);
  52  |   await save(page, trace, fixture.p305_first, "PLANNED", "60");
  53  |   await save(page, trace, fixture.p305_second, "PLANNED", "40");
  54  |   await expect(trace.getByText(/جمع برنامه:.*100/).first()).toBeVisible();
  55  |   await openShipment(page);
  56  |   trace = await openTrace(page);
  57  |   await expect(trace.getByText(/جمع برنامه:.*100/).first()).toBeVisible();
  58  | 
  59  |   await save(page, trace, fixture.p305_second, "PLANNED", "30", "برنامه تازه");
  60  |   await expect(trace.getByText(/10 کارتن در برنامه این بخش هنوز تخصیص ندارد/)).toBeVisible();
  61  |   await save(page, trace, fixture.p305_second, "PLANNED", "50", "بار اضافی برنامه");
  62  |   await expect(trace.getByText(/10 کارتن بالاتر از مقدار برنامه‌ریزی‌شده تخصیص داده شده است/)).toBeVisible();
  63  |   await save(page, trace, fixture.p305_first, "ACTUAL", "55");
  64  |   await save(page, trace, fixture.p305_second, "ACTUAL", "40");
  65  |   await expect(trace.getByText(/جمع واقعی:.*95/).first()).toBeVisible();
  66  |   await save(page, trace, fixture.p305_first, "ACTUAL", "50", "بازشماری");
  67  |   await save(page, trace, fixture.p305_first, "ACTUAL", "48", "مقدار تأییدشده");
  68  |   await expect(trace.getByText(/جمع واقعی:.*88/).first()).toBeVisible();
  69  |   await trace.locator("summary", { hasText: "تاریخچه تخصیص و انتقال" }).click();
  70  |   await expect(trace.getByText("مقدار تأییدشده")).toBeVisible();
  71  |   await expect(trace.getByText(/50 ← 48/)).toBeVisible();
  72  | 
  73  |   await trace.getByLabel("اجرای مبدأ انتقال").selectOption(fixture.p305_first);
  74  |   await trace.getByLabel("اجرای مقصد انتقال").selectOption(fixture.p305_second);
  75  |   await trace.getByLabel("مقدار انتقال").fill("20");
  76  |   await trace.getByLabel("محل یا زمینه انتقال").fill("خورگوس");
  77  |   const transferResponse = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith("/allocation-transfers"));
  78  |   await trace.getByRole("button", { name: "ثبت انتقال کالا" }).click();
  79  |   expect((await transferResponse).status()).toBe(201);
  80  |   await expect(trace.getByText(/جمع واقعی:.*88/).first()).toBeVisible();
  81  |   await save(page, trace, fixture.p305_third, "ACTUAL", "95");
  82  |   await expect(trace.getByText(/جمع واقعی:.*95/).last()).toBeVisible();
  83  |   await expect(trace.getByText(/از بخش قبل هنوز در این بخش ثبت نشده است|بیشتر از بخش قبل در این بخش ثبت شده است/)).toBeVisible();
  84  | 
  85  |   const cargoDetails = page.locator("details").filter({ has: page.locator("summary", { hasText: "جزئیات کالا، وسیله حمل و پیگیری" }) }).first();
  86  |   const cargoArticle = cargoDetails.locator("article").filter({ hasText: "قطعات موتور" }).first();
  87  |   await cargoArticle.locator("summary", { hasText: "تکمیل یا اصلاح اطلاعات" }).click();
  88  |   await cargoArticle.getByLabel("Edit planned quantity line 1").fill("95");
  89  |   await cargoArticle.getByLabel("Edit cargo reason line 1").fill("مشتری مقدار برنامه را کم کرد");
  90  |   const planRevision = page.waitForResponse(item => item.request().method() === "PATCH" && item.url().endsWith(`/cargo-items/${fixture.p305_cargo}`));
  91  |   await cargoArticle.getByRole("button", { name: "ذخیره اطلاعات کالا" }).click();
  92  |   expect((await planRevision).status()).toBe(200);
  93  |   await cargoArticle.getByRole("button", { name: "تاریخچه برنامه و مقدار واقعی" }).click();
  94  |   await expect(cargoArticle.getByText(/برنامه: 100.*95/)).toBeVisible();
  95  |   await expect(cargoArticle.getByText(/مشتری مقدار برنامه را کم کرد/)).toBeVisible();
  96  |   await cargoArticle.getByLabel("Edit actual quantity line 1").fill("115");
  97  |   await cargoArticle.getByLabel("Edit cargo reason line 1").fill("بازشماری کل کالا");
  98  |   const actualCorrection = page.waitForResponse(item => item.request().method() === "PATCH" && item.url().endsWith(`/cargo-items/${fixture.p305_cargo}`));
  99  |   await cargoArticle.getByRole("button", { name: "ذخیره اطلاعات کالا" }).click();
  100 |   expect((await actualCorrection).status()).toBe(200);
  101 |   await cargoArticle.getByRole("button", { name: "تاریخچه برنامه و مقدار واقعی" }).click();
  102 |   await expect(cargoArticle.getByText(/مقدار واقعی: 95.*115/)).toBeVisible();
  103 |   await expect(cargoArticle.getByText(/بازشماری کل کالا/)).toBeVisible();
  104 |   await trace.getByRole("button", { name: "تازه‌سازی" }).click();
  105 |   await expect(trace.getByText(/مقدار واقعی شناخته‌شده:.*115/)).toBeVisible();
  106 |   await save(page, trace, fixture.p305_third, "ACTUAL", "105", "ثبت واقعی بیش از برنامه");
  107 |   await expect(trace.getByText(/جمع واقعی:.*105/).last()).toBeVisible();
  108 |   await expect(trace.getByText(/مقدار واقعی این بخش 10 کارتن بیشتر از برنامه است/).last()).toBeVisible();
  109 |   const ownerToken = await page.evaluate(() => localStorage.getItem("expert_token"));
  110 |   const ownerHeaders = { Authorization: `Bearer ${ownerToken}`, "Content-Type": "application/json" };
  111 |   const exceptions = await page.request.get(`/api/operational-shipments/${fixture.p304_shipment}/route-exceptions?status=open`, { headers: ownerHeaders });
  112 |   expect(exceptions.status()).toBe(200);
  113 |   expect(((await exceptions.json()) as { data: unknown[] }).data).toEqual([]);
  114 |   const foreignCargo = await page.request.get(`/api/internal/operational-shipments/${fixture.p304_shipment}/cargo-items/${fixture.tenant_b_cargo}/allocation-trace`, { headers: ownerHeaders });
  115 |   expect(foreignCargo.status()).toBe(404);
  116 |   for (const persona of ["admin", "foreign"]) {
  117 |     const login = await page.request.post("/api/expert/auth/login", { data: { username: `shared_transport_e2e_${persona}`, password } });
  118 |     expect(login.status()).toBe(200);
  119 |     const token = ((await login.json()) as { tokens: { access_token: string } }).tokens.access_token;
  120 |     const denied = await page.request.put(`/api/internal/operational-shipments/${fixture.p304_shipment}/cargo-items/${fixture.p305_cargo}/stage-executions/${fixture.p305_first}/allocation`, { headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": `p305-browser-denied-${persona}` }, data: { dimension: "PLANNED", quantity: "1", expected_version: 1 } });
  121 |     expect([403, 404]).toContain(denied.status());
  122 |   }
  123 |   const guessed = await page.request.put(`/api/internal/operational-shipments/${fixture.p304_shipment}/cargo-items/${fixture.p305_cargo}/stage-executions/00000000-0000-4000-8000-000000000000/allocation`, { headers: { ...ownerHeaders, "Idempotency-Key": "p305-browser-guessed" }, data: { dimension: "PLANNED", quantity: "1", expected_version: 0 } });
```