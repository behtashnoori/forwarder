import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { openShipmentSection } from "./helpers/shipment-workspace";
const password=process.env.FORWARDER_E2E_PASSWORD;
const fixturePath=process.env.FORWARDER_E2E_FIXTURE_PATH;
if(!password||!fixturePath)throw new Error("Use the owned P3-10 qualification runner.");
const fixture=JSON.parse(readFileSync(fixturePath,"utf8")) as {p310_old_shipment:string;p310_new_shipment:string;p310_points:Record<string,string>;p310_geography:Record<string,{country_id:number;admin1_geoname_id:number;city_geoname_id:number}>;p310_foreign_reference:string};
test.setTimeout(180_000);
function local(date:Date){const pad=(n:number)=>String(n).padStart(2,"0");return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;}
async function login(page:Page,persona:string){
  await page.goto("/");await page.getByRole("button",{name:"ورود به سامانه"}).first().click();
  await page.getByLabel("نام کاربری").fill(`shared_transport_e2e_${persona}`);await page.getByLabel("رمز عبور").fill(password!);
  await page.getByRole("dialog").getByRole("button",{name:"ورود",exact:true}).click();await expect(page).not.toHaveURL(/\/$/, { timeout: 15_000 });
}
async function headers(page:Page){return {Authorization:`Bearer ${await page.evaluate(()=>localStorage.getItem("expert_token"))}`,"Idempotency-Key":crypto.randomUUID()};}
async function openShipment(page:Page,id:string){
  // Existing route-based lists omit a Shipment before its first active route.
  // Open its ordinary authenticated detail URL, as the P3-03 authoring journey does.
  await page.goto(`/operations/shipments/${id}`);
  await expect(page.locator("#shipment-overview h1")).toBeVisible();
  await openShipmentSection(page,"route",id);
}
async function draft(page:Page,mode="rail"){
  await expect(page.getByRole("button",{name:"ایجاد مسیر عملیات",exact:true})).toBeVisible();
  await page.getByRole("button",{name:"ایجاد مسیر عملیات",exact:true}).click();
  await page.getByRole("button",{name:"افزودن بخش مسیر",exact:true}).click();
  for(const side of ["origin","destination"]){const select=page.locator(`#leg-${side}-new`);await expect(select.locator(`option[value="logistics_point:${fixture.p310_points[`own_${side}`]}"]`)).toHaveCount(1,{timeout:30_000});await select.selectOption(`logistics_point:${fixture.p310_points[`own_${side}`]}`);}
  await page.locator("#leg-mode-new").selectOption(mode);
  await page.locator("#leg-departure-new").fill(local(new Date(Date.now()+10*86400_000)),{force:true});
  await page.locator("#leg-arrival-new").fill(local(new Date(Date.now()+12*86400_000)),{force:true});
  const saved=page.waitForResponse(response=>response.url().endsWith("/legs")&&response.request().method()==="POST");
  await page.getByRole("button",{name:"ذخیره بخش مسیر",exact:true}).click();expect((await saved).status()).toBe(201);
  const basis=page.locator("summary",{hasText:"زمان مرجع و مبنای برنامه"});
  if(!(await basis.locator("xpath=..").getAttribute("open")))await basis.click();
  await expect(page.getByRole("heading",{name:/مرجع قابل استفاده/})).toBeVisible({timeout:15_000});
}
test("P3-10 normal Admin reference → Expert pinned basis → future version and new plan",async({browser},testInfo)=>{
  const adminContext=await browser.newContext();const expertContext=await browser.newContext();
  const admin=await adminContext.newPage();const expert=await expertContext.newPage();
  const pageErrors:string[]=[];
  for(const page of [admin,expert]){page.on("pageerror",error=>pageErrors.push(error.message));await page.route("https://fonts.googleapis.com/**",route=>route.fulfill({status:200,contentType:"text/css",body:""}));await page.route("https://fonts.gstatic.com/**",route=>route.fulfill({status:204,body:""}));}
  await login(admin,"admin");await admin.getByRole("tab",{name:"زمان مرجع مسیر",exact:true}).click();
  await expect(admin.getByText("زمان مرجع تعریف نشده است. هیچ زمان پیش‌فرضی اعمال نمی‌شود.")).toBeVisible();
  await admin.getByRole("button",{name:"تعریف زمان مرجع تازه",exact:true}).click();
  for(const [side,label] of [["origin","مبدأ مرجع"],["destination","مقصد مرجع"]] as const){
    const geography=fixture.p310_geography[side];
    const country=admin.getByLabel(`${label} کشور`,{exact:true});
    await country.selectOption(String(geography.country_id));
    const admin1=admin.getByLabel(`${label} استان`,{exact:true});
    await expect(admin1.locator(`option[value="${geography.admin1_geoname_id}"]`)).toHaveCount(1,{timeout:30_000});
    await admin1.selectOption(String(geography.admin1_geoname_id));
    const city=admin.getByLabel(`${label} شهر`,{exact:true});
    await expect(city.locator(`option[value="${geography.city_geoname_id}"]`)).toHaveCount(1,{timeout:30_000});
    await city.selectOption(String(geography.city_geoname_id));
    const select=admin.getByLabel(`${label} مکان سازمان`,{exact:true});
    await expect(select.locator(`option[value="${fixture.p310_points[`own_${side}`]}"]`)).toHaveCount(1,{timeout:30_000});
    await select.selectOption(fixture.p310_points[`own_${side}`]);
  }
  await admin.getByLabel("روش حمل مرجع",{exact:true}).selectOption("rail");
  for(const [label,value] of [["حداقل حرکت (ساعت)","20"],["حداکثر حرکت (ساعت)","24"],["حداقل توقف (ساعت)","4"],["حداکثر توقف (ساعت)","8"]])await admin.getByLabel(label,{exact:true}).fill(value);
  const effective=admin.getByLabel("شروع اعتبار",{exact:true});
  const effectivePicker=effective.locator("xpath=..");
  await expect(effectivePicker.getByRole("button").first()).toContainText("شمسی");
  await effectivePicker.getByRole("button").first().click();
  await effectivePicker.getByRole("button",{name:"میلادی",exact:true}).click();
  await expect(effectivePicker.getByRole("button").first()).toContainText("میلادی");
  await effectivePicker.getByRole("button",{name:"شمسی",exact:true}).click();
  await effective.fill(local(new Date(Date.now()-86400_000)),{force:true});
  const created=admin.waitForResponse(response=>response.url().endsWith("/api/admin/organization-route-reference-times")&&response.request().method()==="POST");
  await admin.getByRole("button",{name:"ثبت زمان مرجع",exact:true}).click();expect((await created).status()).toBe(201);
  await expect(admin.getByText("۲۰ ساعت تا ۲۴ ساعت",{exact:true}).first()).toBeVisible();
  await admin.reload();await admin.getByRole("tab",{name:"زمان مرجع مسیر",exact:true}).click();
  await expect(admin.getByText("۴ ساعت تا ۸ ساعت",{exact:true}).first()).toBeVisible();
  await admin.screenshot({path:testInfo.outputPath("route-time-admin-desktop.png"),fullPage:true});
  await login(expert,"restricted");await openShipment(expert,fixture.p310_old_shipment);await draft(expert);
  await expert.getByRole("button",{name:"بررسی و اعتبارسنجی مسیر",exact:true}).click();
  await expect(expert.getByText("مسیر برای فعال‌سازی معتبر است.",{exact:true})).toBeVisible();
  const activated=expert.waitForResponse(response=>response.request().method()==="POST"&&response.url().endsWith("/activate"));
  await expert.getByRole("button",{name:"فعال‌سازی مسیر",exact:true}).click();expect((await activated).status()).toBe(200);
  await expect(expert.getByText("برنامه مسیر فعال",{exact:true})).toBeVisible();
  const basisSummary=expert.locator("summary",{hasText:"زمان مرجع و مبنای برنامه"});
  const basisDetails=basisSummary.locator("xpath=..");
  if(!(await basisDetails.getAttribute("open")))await basisSummary.click();
  await basisDetails.getByRole("button",{name:"بررسی دوباره مراجع",exact:true}).click();
  await expert.getByRole("button",{name:"ثبت این نسخه برای برنامه",exact:true}).click();
  await expect(expert.getByRole("status")).toContainText("با موفقیت");
  await expect(expert.getByText(/قبلاً تثبیت شده است/)).toBeVisible();
  await expect(expert.getByRole("heading",{name:"مبنای تثبیت‌شده برنامه · نسخه مرجع 1",exact:true})).toBeVisible();
  const list=await admin.request.get("/api/organization/route-reference-times",{headers:await headers(admin)});
  const reference=(await list.json()).data.items[0];
  await admin.getByRole("button",{name:"ثبت نسخه تازه",exact:true}).click();
  await admin.getByLabel("حداقل حرکت (ساعت)",{exact:true}).fill("25");await admin.getByLabel("حداکثر حرکت (ساعت)",{exact:true}).fill("30");
  await admin.getByLabel("شروع اعتبار",{exact:true}).fill(local(new Date(Date.now()+86400_000)),{force:true});
  const updated=admin.waitForResponse(response=>response.url().endsWith("/versions")&&response.request().method()==="POST");
  await admin.getByRole("button",{name:"ثبت زمان مرجع",exact:true}).click();expect((await updated).status()).toBe(201);
  await admin.locator("summary",{hasText:"تاریخچه نسخه‌ها"}).click();await expect(admin.getByText("۲۵ ساعت تا ۳۰ ساعت",{exact:true})).toBeVisible();
  await admin.evaluate(()=>window.scrollTo(0,0));await admin.screenshot({path:testInfo.outputPath("route-time-admin-history.png"),fullPage:true});
  await expert.getByRole("button",{name:"بررسی دوباره مراجع"}).click();
  await expect(expert.getByRole("heading",{name:"مرجع قابل استفاده · نسخه 2",exact:true})).toBeVisible();
  await expect(expert.getByRole("heading",{name:"مبنای تثبیت‌شده برنامه · نسخه مرجع 1",exact:true})).toBeVisible();
  await expert.evaluate(()=>window.scrollTo(0,0));await expert.screenshot({path:testInfo.outputPath("route-time-pinned-desktop.png"),fullPage:true});
  await expert.setViewportSize({width:390,height:844});await expert.evaluate(()=>window.scrollTo(0,0));await expert.screenshot({path:testInfo.outputPath("route-time-pinned-mobile.png"),fullPage:true});
  expect(await expert.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expert.setViewportSize({width:1280,height:720});await openShipment(expert,fixture.p310_new_shipment);await draft(expert,"road");
  await expect(expert.getByRole("button",{name:"ثبت این نسخه برای برنامه",exact:true})).toBeDisabled();
  await expect(expert.getByText("تعریف نشده",{exact:true}).first()).toBeVisible();
  await expert.evaluate(()=>window.scrollTo(0,0));await expert.screenshot({path:testInfo.outputPath("route-time-undefined.png"),fullPage:true});
  await expert.getByRole("button",{name:"ویرایش بخش مسیر",exact:true}).click();
  const mode=expert.locator('select[id^="leg-mode-"]');await mode.selectOption("rail");
  const edit=expert.waitForResponse(response=>response.request().method()==="PATCH"&&response.url().includes("/legs/"));
  await expert.getByRole("button",{name:"ذخیره بخش مسیر",exact:true}).click();expect((await edit).status()).toBe(200);
  await expert.getByRole("button",{name:"بررسی دوباره مراجع"}).click();
  await expect(expert.getByRole("heading",{name:"مرجع قابل استفاده · نسخه 2",exact:true})).toBeVisible();
  await expert.getByRole("button",{name:"ثبت این نسخه برای برنامه",exact:true}).click();
  await expect(expert.getByRole("heading",{name:"مبنای تثبیت‌شده برنامه · نسخه مرجع 2",exact:true})).toBeVisible();
  await openShipment(expert,fixture.p310_old_shipment);
  const historicalBasis=expert.locator("summary",{hasText:"زمان مرجع و مبنای برنامه"});
  if(!(await historicalBasis.locator("xpath=..").getAttribute("open")))await historicalBasis.click();
  await expect(expert.getByRole("heading",{name:"مبنای تثبیت‌شده برنامه · نسخه مرجع 1",exact:true})).toBeVisible();
  expect((await expert.request.post(`/api/admin/organization-route-reference-times/${reference.public_id}/versions`,{headers:await headers(expert),data:{expected_version:2}})).status()).toBe(403);
  expect((await admin.request.post(`/api/admin/organization-route-reference-times/${fixture.p310_foreign_reference}/versions`,{headers:await headers(admin),data:{expected_version:1}})).status()).toBe(404);
  const platform=await admin.request.post("/api/expert/auth/login",{data:{username:"shared_transport_e2e_platform",password}});expect(platform.status()).toBe(200);
  const token=(await platform.json()).tokens.access_token;
  expect((await admin.request.post("/api/admin/organization-route-reference-times",{headers:{Authorization:`Bearer ${token}`,"Idempotency-Key":crypto.randomUUID()},data:{}})).status()).toBe(403);
  expect(pageErrors).toEqual([]);await expertContext.close();await adminContext.close();
});
