# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phase3-closure.spec.ts >> P3-12 Admin configuration → Expert close → immutable exception and private Customer status
- Location: e2e\phase3-closure.spec.ts:25:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'اصلاح و تکمیل سوابق' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('heading', { name: 'اصلاح و تکمیل سوابق' }) with timeout 5000ms
  - waiting for getByRole('heading', { name: 'اصلاح و تکمیل سوابق' })

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
  - paragraph: "شناسه محموله: a02857b9-afc3-4132-a6e8-d329435d5b61"
  - text: بسته‌شده
  - paragraph: مشتری و پروژه
  - paragraph: "[SHARED-E2E] Customer A"
  - link "مشاهده پروژه مرتبط":
    - /url: /operations/projects/abcd65e0-4132-4e1c-b329-c89964ccdb9c/units
  - paragraph: مسئول فعلی پرونده
  - paragraph: "[SHARED-E2E] restricted"
  - paragraph: مالکیت از خود محموله خوانده می‌شود.
  - paragraph: مسیر فعال
  - paragraph: چین آزمایشی ← PRIVATE-B-SNAPSHOT
  - paragraph: نسخه 1
  - paragraph: مسیر حمل
  - paragraph: جاده‌ای ← ریلی ← ریلی
  - paragraph: آخرین رخداد عملیاتی
  - paragraph: هنوز رخدادی ثبت نشده
  - paragraph: مرحله فعلی و تازگی پرونده
  - paragraph: مرحله جاری ثبت نشده
  - paragraph: "آخرین تغییر پرونده: ۳۰ سپتامبر ۲۰۲۶ (۸ مهر ۱۴۰۵) · ۱۱:۱۳ (‎+۳:۳۰ گرینویچ)"
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
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/summary
    - link "مسیر و اجرا":
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/route
    - link "کالا و تخصیص":
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/cargo
    - link "اسناد":
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/documents
    - link "پیگیری و ETA":
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/tracking
    - link "تحویل":
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/delivery
    - link "تکمیل و بستن":
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/closure
    - link "تاریخچه":
      - /url: /operations/shipments/a02857b9-afc3-4132-a6e8-d329435d5b61/history
  - group:
    - text: بررسی و بستن پرونده
    - region "بررسی بستن پرونده":
      - heading "بررسی بستن پرونده" [level=2]
      - button "بررسی دوباره"
      - paragraph: پرونده بسته شده است · پس از تکمیل الزامات
      - paragraph: "[SHARED-E2E] restricted · ۳۰ سپتامبر ۲۰۲۶ (۸ مهر ۱۴۰۵) · ۱۱:۱۳ (‎+۳:۳۰ گرینویچ)"
      - paragraph: "نسخه قواعد هنگام بستن: 1"
      - paragraph: اصلاح سابقه، ثبت دیرهنگام واقعیت‌های قبلی و تکمیل اسناد مجاز است. عملیات تازه مجاز نیست. سابقهٔ تصمیم بستن ثابت می‌ماند.
      - group: الزامات و کمبودهای هنگام بستن
```

# Test source

```ts
  1  | import { expect, test, type Page } from "@playwright/test";
  2  | import { readFileSync } from "node:fs";
  3  | import { openShipmentSection } from "./helpers/shipment-workspace";
  4  | const password=process.env.FORWARDER_E2E_PASSWORD;
  5  | const fixturePath=process.env.FORWARDER_E2E_FIXTURE_PATH;
  6  | if(!password||!fixturePath)throw new Error("Use the owned P3-12 runner");
  7  | const fixture=JSON.parse(readFileSync(fixturePath,"utf8")) as {p312_normal:string;p312_exception:string;p312_planned:string;p309_accounts:Record<string,{email:string}>};
  8  | test.setTimeout(180_000);
  9  | async function login(page:Page,persona:string){
  10 |   await page.goto("/");await page.getByRole("button",{name:"ورود به سامانه"}).first().click();
  11 |   await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);await page.getByLabel("رمز عبور").fill(password!);
  12 |   await page.getByRole("dialog").getByRole("button",{name:"ورود",exact:true}).click();await expect(page).not.toHaveURL(/\/$/);
  13 | }
  14 | async function openShipment(page:Page,id:string){
  15 |   await page.goto("/operations/shipments?scope=all");
  16 |   const all=page.getByRole("button",{name:"نمایش همه وضعیت‌ها",exact:true});
  17 |   if(await all.isVisible())await all.click();
  18 |   await page.locator(`a[href="/operations/shipments/${id}"]`).click();
  19 |   await openShipmentSection(page,"closure",id);
  20 |   const region=page.getByRole("region",{name:"بررسی بستن پرونده"});
  21 |   await expect(region.getByRole("button",{name:"بررسی دوباره"})).toBeVisible();return region;
  22 | }
  23 | function local(date:Date){const pad=(n:number)=>String(n).padStart(2,"0");return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;}
  24 | 
  25 | test("P3-12 Admin configuration → Expert close → immutable exception and private Customer status",async({browser},testInfo)=>{
  26 |   const adminContext=await browser.newContext();const expertContext=await browser.newContext();const customerContext=await browser.newContext();
  27 |   const admin=await adminContext.newPage();const expert=await expertContext.newPage();const customer=await customerContext.newPage();
  28 |   const errors:string[]=[];
  29 |   for(const page of [admin,expert,customer]){page.on("pageerror",error=>errors.push(error.message));await page.route("https://fonts.googleapis.com/**",route=>route.fulfill({status:200,contentType:"text/css",body:""}));await page.route("https://fonts.gstatic.com/**",route=>route.fulfill({status:204,body:""}));}
  30 |   await login(expert,"restricted");let region=await openShipment(expert,fixture.p312_normal);
  31 |   await expect(region.getByText(/قواعد بستن پرونده تعریف نشده است/)).toBeVisible();
  32 |   await login(admin,"admin");await admin.getByRole("tab",{name:"قواعد بستن پرونده",exact:true}).click();
  33 |   await expect(admin.getByText(/قواعد هنوز تعریف نشده است/)).toBeVisible();
  34 |   await admin.getByRole("button",{name:"تعریف نسخه تازه قواعد"}).click();await admin.getByRole("button",{name:"افزودن معیار"}).click();
  35 |   await admin.getByLabel("معیار 1",{exact:true}).selectOption("ACTUAL_QUANTITY_KNOWN");
  36 |   await admin.getByLabel("شروع اعتبار (زمان محلی)").fill(local(new Date(Date.now()-86400_000)));
  37 |   const configured=admin.waitForResponse(response=>response.url().endsWith("/closure-policy/versions")&&response.request().method()==="POST");
  38 |   await admin.getByRole("button",{name:"ثبت نسخه قواعد"}).click();expect((await configured).status()).toBe(201);
  39 |   await admin.screenshot({path:testInfo.outputPath("closure-policy-admin.png"),fullPage:true});
  40 |   await region.getByRole("button",{name:"بررسی دوباره"}).click();
  41 |   await expect(region.getByRole("button",{name:"بستن پرونده",exact:true})).toBeEnabled();
  42 |   await region.getByRole("button",{name:"بستن پرونده",exact:true}).click();
  43 |   const closed=expert.waitForResponse(response=>response.url().endsWith("/close")&&response.request().method()==="POST");
  44 |   await region.getByRole("button",{name:"تأیید نهایی بستن"}).click();expect((await closed).status()).toBe(201);
  45 |   await expect(region.getByText(/پرونده بسته شده است/)).toBeVisible();
  46 |   await expert.reload();await openShipmentSection(expert,"closure",fixture.p312_normal);
  47 |   region=expert.getByRole("region",{name:"بررسی بستن پرونده"});await expect(region.getByText(/پرونده بسته شده است/)).toBeVisible();
  48 |   await expect(expert.getByText("بسته‌شده",{exact:true})).toBeVisible();
> 49 |   await expect(expert.getByRole("heading",{name:"اصلاح و تکمیل سوابق"})).toBeVisible();
     |                                                                          ^ Error: expect(locator).toBeVisible() failed
  50 |   await expect(region.getByRole("button",{name:"بستن پرونده",exact:true})).toHaveCount(0);
  51 |   await expert.setViewportSize({width:390,height:844});await region.scrollIntoViewIfNeeded();
  52 |   expect(await expert.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  53 |   await expert.screenshot({path:testInfo.outputPath("closed-owner-mobile.png"),fullPage:true});
  54 |   await expert.setViewportSize({width:1280,height:900});
  55 |   region=await openShipment(expert,fixture.p312_exception);await expect(region.getByRole("button",{name:"بستن پرونده",exact:true})).toBeDisabled();
  56 |   await expect(region.getByRole("button",{name:"بستن با استثنای مدیر"})).toHaveCount(0);
  57 |   const exception=await openShipment(admin,fixture.p312_exception);
  58 |   await exception.getByRole("button",{name:"بستن با استثنای مدیر"}).click();await exception.getByRole("button",{name:"تأیید نهایی بستن"}).click();
  59 |   await expect(exception.getByRole("alert")).toContainText("دلیل");
  60 |   await exception.getByLabel("دلیل بستن با استثنا (الزامی)").fill("PRIVATE-CLOSURE-EXCEPTION-REASON");
  61 |   await exception.getByRole("button",{name:"تأیید نهایی بستن"}).click();await expect(exception.getByText(/پرونده بسته شده است/)).toBeVisible();
  62 |   await expect(admin.getByText("بسته‌شده",{exact:true})).toBeVisible();
  63 |   await expect(admin.getByRole("heading",{name:"اصلاح و تکمیل سوابق"})).toBeVisible();
  64 |   await exception.locator("summary",{hasText:"الزامات و کمبودهای هنگام بستن"}).click();await expect(exception.getByText("نامشخص",{exact:true})).toBeVisible();
  65 |   await admin.screenshot({path:testInfo.outputPath("exception-retained-missing.png"),fullPage:true});
  66 |   const planned=await openShipment(admin,fixture.p312_planned);await expect(planned.getByText("بستن فقط پس از تکمیل پرونده ممکن است.")).toBeVisible();
  67 |   await customer.goto("/customer");await customer.locator("#customer-email").fill(fixture.p309_accounts.a.email);await customer.locator("#customer-password").fill(password!);
  68 |   await customer.locator("form button").first().click();await expect(customer).toHaveURL(/\/customer\/requests/);
  69 |   await customer.getByRole("link",{name:"حمل‌های من",exact:true}).click();await customer.locator(`a[href="/customer/shipments/${fixture.p312_normal}"]`).click();
  70 |   await expect(customer.getByText("بسته‌شده",{exact:true})).toBeVisible();
  71 |   await expect(customer.getByText("PRIVATE-CLOSURE-EXCEPTION-REASON")).toHaveCount(0);
  72 |   await expect(customer.getByRole("button",{name:"بستن پرونده",exact:true})).toHaveCount(0);
  73 |   await customer.screenshot({path:testInfo.outputPath("closed-customer-safe.png"),fullPage:true});
  74 |   expect(errors).toEqual([]);await adminContext.close();await expertContext.close();await customerContext.close();
  75 | });
  76 | 
```