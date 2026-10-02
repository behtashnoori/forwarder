import {expect, test} from "@playwright/test";
import {readFileSync} from "node:fs";
import {openShipmentSection} from "./helpers/shipment-workspace";

const fixture=JSON.parse(readFileSync(process.env.FORWARDER_E2E_FIXTURE_PATH!,"utf8"));
if (!(process.env.E2E_DATABASE_URL || "").includes("127.0.0.1") || !fixture.handoff) throw new Error("Owned consolidated fixture required");
test.setTimeout(180000);

test("H1-H6 exact Request reuse, parent filters, deliberate variance and date-only Quote",async({page},info)=>{
  await page.goto("/"); await page.getByRole("button",{name:"ورود به سامانه"}).first().click();
  await page.getByLabel("نام کاربری").fill(fixture.username);
  await page.getByLabel("رمز عبور").fill(process.env.FORWARDER_E2E_PASSWORD!);
  await page.getByRole("dialog").getByRole("button",{name:"ورود",exact:true}).click();
  await expect(page).not.toHaveURL(/\/$/);
  for (const [index,item] of fixture.handoff.entries()) {
    await page.goto(`/expert/requests/${item.request}`);
    await expect(page.getByText("نام درخواست‌دهنده ثبت نشده").first()).toBeVisible();
    await expect(page.getByText("مشتری سازمانی مرتبط",{exact:true})).toBeVisible();
    await expect(page.getByText(fixture.crm_customer_name,{exact:true}).first()).toBeVisible();
    await page.reload();
    await expect(page.getByText("نام درخواست‌دهنده ثبت نشده").first()).toBeVisible();
    await page.getByRole("link",{name:"ایجاد پرونده عملیاتی",exact:true}).first().click();
    await page.getByRole("button",{name:"استفاده از محل درخواستی مشتری · مبدأ",exact:true}).click();
    await page.getByRole("button",{name:"استفاده از محل درخواستی مشتری · مقصد",exact:true}).click();
    const comparison=page.getByRole("region",{name:"مقایسه محل درخواستی و برنامه عملیاتی"});
    await expect(comparison).toContainText("شاوشنگ");
    if (index===1) {
      await page.locator("summary",{hasText:/شاوشنگ.*مشاهده یا تغییر/}).click();
      await page.getByLabel("مبدأ کشور",{exact:true}).selectOption(String(fixture.geo.country));
      await page.getByLabel("مبدأ استان",{exact:true}).selectOption(String(fixture.geo.parent));
      await page.getByLabel("مبدأ جست‌وجوی شهر",{exact:true}).fill("Shaoxing");
      const field=page.locator("fieldset").filter({has:page.getByLabel("مبدأ جست‌وجوی شهر",{exact:true})}).last();
      await field.getByRole("button",{name:"جست‌وجو",exact:true}).first().click();
      await expect(page.getByLabel("مبدأ شهر",{exact:true}).locator('option[value="1795855"]')).toHaveCount(1);
      await page.getByLabel("مبدأ شهر",{exact:true}).selectOption("1795855");
      await page.locator("summary",{hasText:/شاوشنگ.*مشاهده یا تغییر/}).click();
      await page.getByLabel("مبدأ استان",{exact:true}).selectOption(String(fixture.geo.other_parent));
      await expect(page.getByLabel("مبدأ شهر",{exact:true})).toHaveValue("");
      await page.getByLabel("مبدأ جست‌وجوی شهر",{exact:true}).fill("Sanxing");
      await field.getByRole("button",{name:"جست‌وجو",exact:true}).first().click();
      await page.getByLabel("مبدأ شهر",{exact:true}).selectOption("1796562");
      await expect(comparison).toContainText("مبدأ برنامه عملیاتی با محل درخواستی مشتری متفاوت است.");
    }
    await page.locator('#departure').fill("2026-10-03T08:00");
    await page.locator('#arrival').fill("2026-10-04T08:00");
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await comparison.screenshot({path:info.outputPath(`handoff-review-${index}.png`)});
    const saved=page.waitForResponse(r=>r.request().method()==="POST"&&r.url().includes("/operational-shipments")&&!r.url().includes("eta"));
    await page.getByRole("button",{name:"ایجاد پرونده عملیاتی",exact:true}).click();
    const response=await saved; expect(response.status()).toBe(201);
    const body=await response.json();
    const shipment=body.data.public_id;
    await openShipmentSection(page,"route",shipment);
    const source=page.getByRole("region",{name:"مقایسه محل درخواستی و برنامه عملیاتی"});
    await expect(source).toContainText("شاوشنگ");
    if(index===1) await expect(source).toContainText("مبدأ برنامه عملیاتی با محل درخواستی مشتری متفاوت است.");
    await page.setViewportSize({width:1280,height:900});
    await source.screenshot({path:info.outputPath(`handoff-persisted-${index}.png`)});
  }
  // The existing Quote creation/revision dialog persists a date, with no timezone suffix.
  await page.goto(`/expert/requests/${fixture.journeys.discussion.request_public_id}`);
  await page.getByRole("button",{name:/ارسال پیشنهاد|صدور پیشنهاد/}).first().click();
  const dialog=page.getByRole("dialog",{name:"ارسال پیشنهاد"});
  await dialog.getByLabel("مبلغ (الزامی)").fill("1500000");
  await expect(dialog.getByLabel("تاریخ اعتبار")).toHaveValue("");
  await dialog.getByRole("button",{name:/انتخاب تاریخ/}).click();
  await dialog.getByRole("button",{name:"میلادی",exact:true}).click();
  await dialog.getByLabel("تاریخ اعتبار سال").selectOption("2026");
  await dialog.getByLabel("تاریخ اعتبار ماه").selectOption("10");
  await dialog.getByLabel("تاریخ اعتبار روز").selectOption("4");
  await dialog.getByRole("button",{name:"شمسی",exact:true}).click();
  await expect(dialog.getByLabel("تاریخ اعتبار")).toHaveValue("2026-10-04");
  const quote=page.waitForResponse(r=>r.request().method()==="POST"&&r.url().includes("quote"));
  await dialog.getByRole("button",{name:"ارسال پیشنهاد",exact:true}).click();
  const quoted=await quote; expect(quoted.ok()).toBe(true);
  expect(quoted.request().postDataJSON().valid_until).toBe("2026-10-04");
  await page.reload();
  await page.screenshot({path:info.outputPath("quote-date-reopened.png"),fullPage:true});
});
