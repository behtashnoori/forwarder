import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
const password=process.env.FORWARDER_E2E_PASSWORD;
const fixturePath=process.env.FORWARDER_E2E_FIXTURE_PATH;
if(!password||!fixturePath)throw new Error("Use the owned P3-12 runner");
const fixture=JSON.parse(readFileSync(fixturePath,"utf8")) as {p312_normal:string;p312_exception:string;p312_planned:string;p309_accounts:Record<string,{email:string}>};
test.setTimeout(180_000);
async function login(page:Page,persona:string){
  await page.goto("/");await page.getByRole("button",{name:"ورود به سامانه"}).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button",{name:"ورود",exact:true}).click();await expect(page).not.toHaveURL(/\/$/);
}
async function openShipment(page:Page,id:string){
  await page.goto("/operations/shipments?scope=all");
  const all=page.getByRole("button",{name:"نمایش همه وضعیت‌ها",exact:true});
  if(await all.isVisible())await all.click();
  await page.locator(`a[href="/operations/shipments/${id}"]`).click();
  await page.locator("summary",{hasText:"بررسی و بستن پرونده"}).click();
  const region=page.getByRole("region",{name:"بررسی بستن پرونده"});
  await expect(region.getByRole("button",{name:"بررسی دوباره"})).toBeVisible();return region;
}
function local(date:Date){const pad=(n:number)=>String(n).padStart(2,"0");return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;}

test("P3-12 Admin configuration → Expert close → immutable exception and private Customer status",async({browser},testInfo)=>{
  const adminContext=await browser.newContext();const expertContext=await browser.newContext();const customerContext=await browser.newContext();
  const admin=await adminContext.newPage();const expert=await expertContext.newPage();const customer=await customerContext.newPage();
  const errors:string[]=[];
  for(const page of [admin,expert,customer]){page.on("pageerror",error=>errors.push(error.message));await page.route("https://fonts.googleapis.com/**",route=>route.fulfill({status:200,contentType:"text/css",body:""}));await page.route("https://fonts.gstatic.com/**",route=>route.fulfill({status:204,body:""}));}
  await login(expert,"restricted");let region=await openShipment(expert,fixture.p312_normal);
  await expect(region.getByText(/قواعد بستن پرونده تعریف نشده است/)).toBeVisible();
  await login(admin,"admin");await admin.getByRole("tab",{name:"قواعد بستن پرونده",exact:true}).click();
  await expect(admin.getByText(/قواعد هنوز تعریف نشده است/)).toBeVisible();
  await admin.getByRole("button",{name:"تعریف نسخه تازه قواعد"}).click();await admin.getByRole("button",{name:"افزودن معیار"}).click();
  await admin.getByLabel("معیار 1",{exact:true}).selectOption("ACTUAL_QUANTITY_KNOWN");
  await admin.getByLabel("شروع اعتبار (زمان محلی)").fill(local(new Date(Date.now()-86400_000)));
  const configured=admin.waitForResponse(response=>response.url().endsWith("/closure-policy/versions")&&response.request().method()==="POST");
  await admin.getByRole("button",{name:"ثبت نسخه قواعد"}).click();expect((await configured).status()).toBe(201);
  await admin.screenshot({path:testInfo.outputPath("closure-policy-admin.png"),fullPage:true});
  await region.getByRole("button",{name:"بررسی دوباره"}).click();
  await expect(region.getByRole("button",{name:"بستن پرونده",exact:true})).toBeEnabled();
  await region.getByRole("button",{name:"بستن پرونده",exact:true}).click();
  const closed=expert.waitForResponse(response=>response.url().endsWith("/close")&&response.request().method()==="POST");
  await region.getByRole("button",{name:"تأیید نهایی بستن"}).click();expect((await closed).status()).toBe(201);
  await expect(region.getByText(/پرونده بسته شده است/)).toBeVisible();
  await expert.reload();await expert.locator("summary",{hasText:"بررسی و بستن پرونده"}).click();
  region=expert.getByRole("region",{name:"بررسی بستن پرونده"});await expect(region.getByText(/پرونده بسته شده است/)).toBeVisible();
  await expect(expert.getByText("بسته‌شده",{exact:true})).toBeVisible();
  await expect(expert.getByRole("heading",{name:"اصلاح و تکمیل سوابق"})).toBeVisible();
  await expect(region.getByRole("button",{name:"بستن پرونده",exact:true})).toHaveCount(0);
  await expert.setViewportSize({width:390,height:844});await region.scrollIntoViewIfNeeded();
  expect(await expert.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await expert.screenshot({path:testInfo.outputPath("closed-owner-mobile.png"),fullPage:true});
  await expert.setViewportSize({width:1280,height:900});
  region=await openShipment(expert,fixture.p312_exception);await expect(region.getByRole("button",{name:"بستن پرونده",exact:true})).toBeDisabled();
  await expect(region.getByRole("button",{name:"بستن با استثنای مدیر"})).toHaveCount(0);
  const exception=await openShipment(admin,fixture.p312_exception);
  await exception.getByRole("button",{name:"بستن با استثنای مدیر"}).click();await exception.getByRole("button",{name:"تأیید نهایی بستن"}).click();
  await expect(exception.getByRole("alert")).toContainText("دلیل");
  await exception.getByLabel("دلیل بستن با استثنا (الزامی)").fill("PRIVATE-CLOSURE-EXCEPTION-REASON");
  await exception.getByRole("button",{name:"تأیید نهایی بستن"}).click();await expect(exception.getByText(/پرونده بسته شده است/)).toBeVisible();
  await expect(admin.getByText("بسته‌شده",{exact:true})).toBeVisible();
  await expect(admin.getByRole("heading",{name:"اصلاح و تکمیل سوابق"})).toBeVisible();
  await exception.locator("summary",{hasText:"الزامات و کمبودهای هنگام بستن"}).click();await expect(exception.getByText("نامشخص",{exact:true})).toBeVisible();
  await admin.screenshot({path:testInfo.outputPath("exception-retained-missing.png"),fullPage:true});
  const planned=await openShipment(admin,fixture.p312_planned);await expect(planned.getByText("بستن فقط پس از تکمیل پرونده ممکن است.")).toBeVisible();
  await customer.goto("/customer");await customer.locator("#customer-email").fill(fixture.p309_accounts.a.email);await customer.locator("#customer-password").fill(password!);
  await customer.locator("form button").first().click();await expect(customer).toHaveURL(/\/customer\/requests/);
  await customer.getByRole("link",{name:"حمل‌های من",exact:true}).click();await customer.locator(`a[href="/customer/shipments/${fixture.p312_normal}"]`).click();
  await expect(customer.getByText("بسته‌شده",{exact:true})).toBeVisible();
  await expect(customer.getByText("PRIVATE-CLOSURE-EXCEPTION-REASON")).toHaveCount(0);
  await expect(customer.getByRole("button",{name:"بستن پرونده",exact:true})).toHaveCount(0);
  await customer.screenshot({path:testInfo.outputPath("closed-customer-safe.png"),fullPage:true});
  expect(errors).toEqual([]);await adminContext.close();await expertContext.close();await customerContext.close();
});
