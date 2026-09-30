# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phase3-cargo-delivery.spec.ts >> P3-08 normal Chrome partial delivery, correction, exact evidence, excess and reopen
- Location: e2e\phase3-cargo-delivery.spec.ts:17:1

# Error details

```
Test timeout of 180000ms exceeded.
```

```
Error: locator.fill: Test timeout of 180000ms exceeded.
Call log:
  - waiting for getByRole('region', { name: 'تحویل کالاها' }).getByLabel('مقصد تحویل', { exact: true })

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - region "Notifications (F8)":
    - list
  - region "Notifications alt+T"
  - navigation "ناوبری برنامه" [ref=e3]:
    - button "بازگشت" [ref=e4] [cursor=pointer]
    - button "خانه" [ref=e5] [cursor=pointer]
  - main [ref=e6]:
    - link "پرش به محتوای پرونده حمل" [ref=e7] [cursor=pointer]:
      - /url: "#shipment-overview"
    - generic [ref=e8]:
      - generic [ref=e9]:
        - link "← بازگشت به فضای کار امروز" [ref=e10] [cursor=pointer]:
          - /url: /operations
        - link "→ بازگشت" [ref=e11] [cursor=pointer]:
          - /url: /operations/shipments
      - generic [ref=e12]:
        - generic [ref=e13]:
          - generic [ref=e14]:
            - paragraph [ref=e15]: فضای کار عملیاتی محموله
            - heading "خلاصه محموله" [level=1] [ref=e16]
            - paragraph [ref=e17]: "شناسه محموله: a84c5dfc-6b4b-47cd-8891-60dc851f05fa"
          - generic [ref=e18]: برنامه‌ریزی‌شده
        - generic [ref=e19]:
          - generic [ref=e20]:
            - paragraph [ref=e21]: مشتری و پروژه
            - paragraph [ref=e22]: "[SHARED-E2E] Customer A"
            - link "مشاهده پروژه مرتبط" [ref=e23] [cursor=pointer]:
              - /url: /operations/projects/ce7e010c-672a-4873-a86c-6c8e55b06c48/units
          - generic [ref=e24]:
            - paragraph [ref=e25]: مسئول فعلی پرونده
            - paragraph [ref=e26]: "[SHARED-E2E] restricted"
            - paragraph [ref=e27]: مالکیت از خود محموله خوانده می‌شود.
          - generic [ref=e28]:
            - paragraph [ref=e29]: مسیر فعال
            - paragraph [ref=e30]: چین آزمایشی ← آکتائو آزمایشی
            - paragraph [ref=e31]: نسخه 1
          - generic [ref=e32]:
            - paragraph [ref=e33]: مسیر حمل
            - paragraph [ref=e34]: جاده‌ای ← ریلی
          - generic [ref=e35]:
            - paragraph [ref=e36]: آخرین رخداد عملیاتی
            - paragraph [ref=e37]: هنوز رخدادی ثبت نشده
          - generic [ref=e38]:
            - paragraph [ref=e39]: مرحله فعلی و تازگی پرونده
            - paragraph [ref=e40]: مرحله جاری ثبت نشده
            - paragraph [ref=e41]: "آخرین تغییر پرونده: ۳۰ سپتامبر ۲۰۲۶ (۸ مهر ۱۴۰۵) · ۱۰:۵۲ (‎+۳:۳۰ گرینویچ)"
          - generic [ref=e42]:
            - paragraph [ref=e43]: موارد باز
            - paragraph [ref=e44]: 0 مورد پیگیری · 0 استثنا
            - paragraph [ref=e45]: عملیات مستقیم
      - navigation "عملیات حمل" [ref=e46]:
        - link "فضای کار امروز" [ref=e47] [cursor=pointer]:
          - /url: /operations
        - link "درخواست‌ها و قیمت‌ها" [ref=e48] [cursor=pointer]:
          - /url: /expert
        - link "پرونده‌های عملیاتی حمل" [ref=e49] [cursor=pointer]:
          - /url: /operations/shipments
        - link "برج کنترل عملیات" [ref=e50] [cursor=pointer]:
          - /url: /operations/control-tower
        - link "عملیات جدید" [ref=e51] [cursor=pointer]:
          - /url: /operations/shipments/new
        - region "اطلاعات سامانه" [ref=e53]:
          - paragraph [ref=e54]: Forwarder 1.10.0
      - navigation "بخش‌های پرونده حمل" [ref=e55]:
        - generic [ref=e56]:
          - link "خلاصه" [ref=e57] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/summary
          - link "مسیر و اجرا" [ref=e58] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/route
          - link "کالا و تخصیص" [ref=e59] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/cargo
          - link "اسناد" [ref=e60] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/documents
          - link "پیگیری و ETA" [ref=e61] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/tracking
          - link "تحویل" [ref=e62] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/delivery
          - link "تکمیل و بستن" [ref=e63] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/closure
          - link "تاریخچه" [ref=e64] [cursor=pointer]:
            - /url: /operations/shipments/a84c5dfc-6b4b-47cd-8891-60dc851f05fa/history
      - region [ref=e65]:
        - generic [ref=e66]:
          - paragraph [ref=e67]: فضای کار محموله
          - heading "تحویل" [level=2] [ref=e68]
        - group [ref=e69]:
          - generic "تحویل کالاها" [ref=e70] [cursor=pointer]
          - region "تحویل کالاها" [ref=e72]:
            - paragraph [ref=e73]: هر تحویل برای یک کالا ثبت می‌شود. تحویل یک مشتری، کالاهای دیگر یا پرونده حمل را خودکار نمی‌بندد.
            - generic [ref=e74]:
              - article [ref=e75]:
                - heading "قطعات موتور · [SHARED-E2E] Customer A" [level=4] [ref=e76]
                - generic [ref=e77]:
                  - generic [ref=e78]:
                    - term [ref=e79]: واقعی شناخته‌شده
                    - definition [ref=e80]: ۱۰۰ کارتن
                  - generic [ref=e81]:
                    - term [ref=e82]: تحویل‌شده
                    - definition [ref=e83]: ۰ کارتن
                  - generic [ref=e84]:
                    - term [ref=e85]: مانده
                    - definition [ref=e86]: ۱۰۰ کارتن
                - paragraph [ref=e87]: هنوز تحویلی ثبت نشده است.
                - button "تحویل تازه برای قطعات موتور" [ref=e88] [cursor=pointer]
              - article [ref=e89]:
                - heading "کالای مشتری دوم · مشتری دوم آزمایشی" [level=4] [ref=e90]
                - generic [ref=e91]:
                  - generic [ref=e92]:
                    - term [ref=e93]: واقعی شناخته‌شده
                    - definition [ref=e94]: ۲۵ کارتن
                  - generic [ref=e95]:
                    - term [ref=e96]: تحویل‌شده
                    - definition [ref=e97]: ۰ کارتن
                  - generic [ref=e98]:
                    - term [ref=e99]: مانده
                    - definition [ref=e100]: ۲۵ کارتن
                - paragraph [ref=e101]: هنوز تحویلی ثبت نشده است.
                - button "تحویل تازه برای کالای مشتری دوم" [ref=e102] [cursor=pointer]
            - form "ثبت تحویل" [ref=e103]:
              - group "تحویل تازه · قطعات موتور · [SHARED-E2E] Customer A" [ref=e104]:
                - generic [ref=e106]:
                  - text: مقدار تحویل (کارتن)
                  - spinbutton "مقدار تحویل" [active] [ref=e107]: "60"
                - group "مقصد تحویل" [ref=e109]:
                  - generic [ref=e111]:
                    - text: کشور
                    - textbox "مقصد تحویل جست‌وجوی کشور" [ref=e112]:
                      - /placeholder: جست‌وجوی کشور
                    - combobox "مقصد تحویل کشور" [ref=e113]:
                      - option "انتخاب کشور" [selected]
                      - option "AFGHANISTAN · AF"
                      - option "ARMENIA · AM"
                      - option "AZERBAIJAN · AZ"
                      - option "CHINA · CN"
                      - option "GEORGIA · GE"
                      - option "KAZAKHSTAN · KZ"
                      - option "KYRGYZSTAN · KG"
                      - option "PAKISTAN · PK"
                      - option "RUSSIAN FEDERATION (THE) · RU"
                      - option "TAJIKISTAN · TJ"
                      - option "TÜRKIYE · TR"
                      - option "UZBEKISTAN · UZ"
                      - option "ایران · IR"
                      - option "ترکمنستان · TM"
                  - generic [ref=e114]:
                    - text: استان / ایالت
                    - textbox "مقصد تحویل جست‌وجوی استان" [disabled] [ref=e115]:
                      - /placeholder: جست‌وجوی استان / ایالت
                    - combobox "مقصد تحویل استان" [disabled] [ref=e116]:
                      - option "انتخاب استان / ایالت" [selected]
                  - generic [ref=e117]:
                    - text: شهر
                    - generic [ref=e118]:
                      - textbox "مقصد تحویل جست‌وجوی شهر" [disabled] [ref=e119]:
                        - /placeholder: جست‌وجوی شهر
                      - button "جست‌وجو" [disabled]
                    - combobox "مقصد تحویل شهر" [disabled] [ref=e120]:
                      - option "انتخاب شهر" [selected]
                  - generic [ref=e121]:
                    - text: مکان سازمان (اختیاری)
                    - generic [ref=e122]:
                      - textbox "مقصد تحویل جست‌وجوی مکان سازمان" [disabled] [ref=e123]:
                        - /placeholder: کارخانه، انبار، پایانه…
                      - button "جست‌وجو" [disabled]
                    - combobox "مقصد تحویل مکان سازمان" [disabled] [ref=e124]:
                      - option "بدون مکان سازمانی؛ خود شهر" [selected]
                - generic [ref=e125]:
                  - text: یادداشت مقصد (اختیاری)
                  - textbox "یادداشت مقصد تحویل" [ref=e126]
                - generic [ref=e127]:
                  - text: زمان وقوع تحویل
                  - textbox "زمان وقوع تحویل" [ref=e128]
                  - text: زمان محلی شما؛ ثبت دیرهنگام مجاز است.
                - paragraph [ref=e129]: مقدار واقعی گزارش‌شده را ثبت کنید. اختلاف با مقدار شناخته‌شده مانع ثبت نیست و مقدار کالا را تغییر نمی‌دهد.
                - generic [ref=e130]:
                  - button "ثبت تحویل" [disabled]
                  - button "انصراف" [ref=e131] [cursor=pointer]
            - heading "تحویل‌های جاری" [level=4] [ref=e132]
            - paragraph [ref=e133]: هنوز تحویلی ثبت نشده است.
```

# Test source

```ts
  1  | import { expect, test, type Page } from "@playwright/test";
  2  | import { readFileSync } from "node:fs";
  3  | import { openShipmentSection } from "./helpers/shipment-workspace";
  4  | const password = process.env.FORWARDER_E2E_PASSWORD;
  5  | const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
  6  | if (!password || !fixturePath) throw new Error("P3-08 requires an owned synthetic fixture");
  7  | const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as { p304_shipment: string; p305_cargo: string; p308_cargo_b: string; p308_status: string };
  8  | test.setTimeout(180_000);
  9  | 
  10 | async function openDeliveries(page: Page) {
  11 |   await page.getByRole("link", { name: "پرونده‌های عملیاتی حمل", exact: true }).click();
  12 |   await page.locator(`a[href="/operations/shipments/${fixture.p304_shipment}"]`).click();
  13 |   await openShipmentSection(page, "delivery", fixture.p304_shipment);
  14 |   return page.getByRole("region", { name: "تحویل کالاها" });
  15 | }
  16 | 
  17 | test("P3-08 normal Chrome partial delivery, correction, exact evidence, excess and reopen", async ({ page }) => {
  18 |   await page.route("https://fonts.googleapis.com/**", route => route.fulfill({ status: 200, contentType: "text/css", body: "" }));
  19 |   await page.route("https://fonts.gstatic.com/**", route => route.fulfill({ status: 204, body: "" }));
  20 |   const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  21 |   await page.goto("/");
  22 |   await page.getByRole("button", { name: "ورود به سامانه" }).first().click();
  23 |   await page.getByLabel("نام کاربری").fill("shared_transport_e2e_restricted");
  24 |   await page.getByLabel("رمز عبور").fill(password!);
  25 |   await page.getByRole("dialog").getByRole("button", { name: "ورود", exact: true }).click();
  26 |   let delivery = await openDeliveries(page);
  27 |   const token = await page.evaluate(() => localStorage.getItem("expert_token"));
  28 |   const headers = { Authorization: `Bearer ${token}` };
  29 |   const before = await page.request.get(`/api/operational-shipments/${fixture.p304_shipment}`, { headers });
  30 |   expect(before.status()).toBe(200);
  31 |   const beforeShipment = (await before.json()).data;
  32 |   let firstId = "";
  33 |   for (const quantity of ["60", "35"]) {
  34 |     await delivery.getByRole("button", { name: "تحویل تازه برای قطعات موتور", exact: true }).click();
  35 |     await delivery.getByLabel("مقدار تحویل", { exact: true }).fill(quantity);
> 36 |     await delivery.getByLabel("مقصد تحویل", { exact: true }).fill("انبار مشتری اول");
     |                                                              ^ Error: locator.fill: Test timeout of 180000ms exceeded.
  37 |     await delivery.getByLabel("زمان وقوع تحویل").fill("2026-09-21T10:30");
  38 |     const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/deliveries"));
  39 |     await delivery.getByRole("button", { name: "ثبت تحویل", exact: true }).click();
  40 |     const response = await saved; expect(response.status()).toBe(201);
  41 |     if (!firstId) firstId = (await response.json()).public_id;
  42 |     await expect(delivery.getByRole("status")).toHaveText("تحویل ثبت شد؛ وضعیت پرونده حمل تغییری نکرد.");
  43 |   }
  44 |   await expect(delivery.locator(`[data-delivery-cargo="${fixture.p305_cargo}"]`)).toContainText("۹۵ کارتن");
  45 |   await expect(delivery.getByText(/۵ کارتن هنوز تحویل ثبت‌شده ندارد/)).toBeVisible();
  46 |   await expect(delivery.locator(`[data-delivery-cargo="${fixture.p308_cargo_b}"]`)).toContainText("هنوز تحویلی ثبت نشده است.");
  47 |   await delivery.locator(`[data-delivery-id="${firstId}"]`).getByRole("button", { name: "اصلاح تحویل", exact: true }).click();
  48 |   await delivery.getByLabel("مقدار تحویل", { exact: true }).fill("58");
  49 |   await delivery.getByLabel("دلیل اصلاح تحویل").fill("بازشماری رسید");
  50 |   const corrected = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/deliveries"));
  51 |   await delivery.getByRole("button", { name: "ثبت اصلاح تحویل", exact: true }).click();
  52 |   const correctionResponse = await corrected; expect(correctionResponse.status()).toBe(201);
  53 |   const correctedId = (await correctionResponse.json()).public_id;
  54 |   await expect(delivery.getByText(/۷ کارتن هنوز تحویل ثبت‌شده ندارد/)).toBeVisible();
  55 |   let current = delivery.locator(`[data-delivery-id="${correctedId}"]`);
  56 |   await current.locator("summary", { hasText: "افزودن مدرک تحویل" }).click();
  57 |   const bytes = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF");
  58 |   await current.getByLabel("فایل مدرک تحویل").setInputFiles({ name: "delivery-receipt.pdf", mimeType: "application/pdf", buffer: bytes });
  59 |   const uploaded = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/documents"));
  60 |   await current.getByRole("button", { name: "ثبت مدرک تحویل", exact: true }).click();
  61 |   const uploadResponse = await uploaded; expect(uploadResponse.status()).toBe(201);
  62 |   const document = (await uploadResponse.json()).data;
  63 |   expect(document.context.type).toBe("DELIVERY"); expect(document.context.target_public_id).toBe(correctedId);
  64 |   expect(document.version).toBe(1); expect(document.context.visibility).toBe("INTERNAL");
  65 |   await expect(current.getByRole("button", { name: "دریافت مدرک" })).toBeVisible();
  66 |   const downloaded = page.waitForEvent("download");
  67 |   await current.getByRole("button", { name: "دریافت مدرک" }).click();
  68 |   const download = await downloaded; expect(download.suggestedFilename()).toBe("delivery-receipt.pdf");
  69 |   expect(readFileSync((await download.path())!)).toEqual(bytes);
  70 |   await delivery.getByRole("button", { name: "تحویل تازه برای قطعات موتور", exact: true }).click();
  71 |   await delivery.getByLabel("مقدار تحویل", { exact: true }).fill("9");
  72 |   await delivery.getByLabel("مقصد تحویل", { exact: true }).fill("انبار مشتری اول");
  73 |   await delivery.getByLabel("زمان وقوع تحویل").fill("2026-09-22T10:30");
  74 |   await delivery.getByRole("button", { name: "ثبت تحویل", exact: true }).click();
  75 |   await expect(delivery.getByRole("alert")).toContainText("۲ کارتن بیش از مقدار واقعی شناخته‌شده");
  76 |   delivery = await openDeliveries(page);
  77 |   await expect(delivery.getByRole("alert")).toContainText("۲ کارتن بیش از مقدار واقعی شناخته‌شده");
  78 |   await delivery.locator("summary", { hasText: "سابقه تحویل‌های اصلاح‌شده" }).click();
  79 |   await expect(delivery.locator(`[data-delivery-id="${firstId}"]`)).toContainText("۶۰ کارتن");
  80 |   current = delivery.locator(`[data-delivery-id="${correctedId}"]`);
  81 |   await expect(current).toContainText("۵۸ کارتن"); await expect(current).toContainText("دلیل اصلاح: بازشماری رسید");
  82 |   await expect(current.getByRole("button", { name: "دریافت مدرک" })).toBeVisible();
  83 |   await expect(delivery.locator(`[data-delivery-cargo="${fixture.p308_cargo_b}"]`)).toContainText("۲۵ کارتن");
  84 |   const response = await page.request.get(`/api/operational-shipments/${fixture.p304_shipment}`, { headers });
  85 |   expect(response.status()).toBe(200);
  86 |   const shipment = await response.json();
  87 |   expect(shipment.data.status).toBe(beforeShipment.status);
  88 |   expect(shipment.data.version).toBe(beforeShipment.version);
  89 |   await delivery.evaluate(node => node.scrollIntoView({ block: "start" })); await page.evaluate(() => window.scrollBy(0, -180));
  90 |   await page.screenshot({ path: test.info().outputPath("cargo-delivery-desktop.png") });
  91 |   await page.setViewportSize({ width: 390, height: 844 });
  92 |   expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  93 |   await delivery.evaluate(node => node.scrollIntoView({ block: "start" })); await page.evaluate(() => window.scrollBy(0, -180));
  94 |   await page.screenshot({ path: test.info().outputPath("cargo-delivery-mobile.png") });
  95 |   expect(errors).toEqual([]);
  96 | });
  97 | 
```