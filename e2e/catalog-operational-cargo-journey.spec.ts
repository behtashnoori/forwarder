import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const password = process.env.FORWARDER_E2E_PASSWORD;
const fixturePath = process.env.FORWARDER_E2E_FIXTURE_PATH;
if (!password || !fixturePath) throw new Error("Catalog journey must use its disposable local runner.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8"));
test.setTimeout(120_000);
type Evidence = { console: string[]; page: string[]; network: string[] };
function observe(page: Page): Evidence { const e: Evidence={console:[],page:[],network:[]}; page.on("console",x=>{if(x.type()==="error"&&!x.text().includes("favicon"))e.console.push(x.text())}); page.on("pageerror",x=>e.page.push(x.message)); page.on("response",x=>{if(x.url().includes("/api/")&&x.status()>=400)e.network.push(`${x.status()} ${x.url()}`)}); return e; }
function clean(e: Evidence) { expect(e.console,"console errors").toEqual([]); expect(e.page,"page errors").toEqual([]); expect(e.network,"failed normal requests").toEqual([]); }
async function login(page: Page) { await page.goto("/"); await page.getByRole("button",{name:"ورود به سامانه"}).first().click(); await page.getByLabel("نام کاربری").fill("shared_transport_e2e_operator"); await page.getByLabel("رمز عبور").fill(password!); await page.getByRole("dialog").getByRole("button",{name:"ورود",exact:true}).click(); await expect(page).not.toHaveURL(/\/$/); }
async function headers(page: Page) { return page.evaluate(()=>({Authorization:`Bearer ${localStorage.getItem("expert_token")||""}`})); }
async function openCargoDetails(page: Page) { await page.locator("summary",{hasText:"جزئیات کالا، وسیله حمل و پیگیری"}).click(); await expect(page.getByText("کالا و وسایل حمل")).toBeVisible(); }
async function shipment(page: Page) { await page.goto(`/operations/shipments/${fixture.shipment_a}`); await openCargoDetails(page); }
async function unit(page: Page) { await page.goto(`/operations/projects/${fixture.project_a}/units`); await page.getByRole("button",{name:"مشاهده"}).first().click(); await expect(page.getByText("بارهای اجرای مشترک")).toBeVisible(); }

test("Catalog → operational cargo → Shared Transport → Tracking", async ({page}) => {
  await page.route("https://fonts.googleapis.com/**", route => route.fulfill({status:200,contentType:"text/css",body:""}));
  await page.route("https://fonts.gstatic.com/**", route => route.fulfill({status:204,body:""}));
  const e=observe(page); await login(page); await shipment(page);
  await page.locator("summary",{hasText:"افزودن کالا"}).click();
  await page.getByLabel("Cargo line number").fill("2");
  const catalog=page.getByLabel("Catalog item"); await expect(catalog.locator("option",{hasText:fixture.catalog_code})).toHaveCount(1);
  await catalog.selectOption(fixture.catalog_item);
  await page.getByLabel("Cargo quantity").fill("12.5");
  await page.getByLabel("Unit of measure").selectOption(fixture.uom);
  const owner=page.getByLabel("Cargo owner",{exact:true}); await owner.selectOption(String(fixture.owner_a_id));
  await page.getByRole("button",{name:"افزودن کالا"}).click();
  const cargo=page.getByRole("article").filter({hasText:fixture.catalog_name}).first();
  await expect(cargo).toContainText("12.5 PALLET"); await expect(cargo).toContainText("[SHARED-E2E] Customer A");
  // The rendered identity is captured from the API after UI creation only.
  const lines=await (await page.request.get(`/api/internal/operational-shipments/${fixture.shipment_a}/cargo-items`,{headers:await headers(page)})).json();
  const item=lines.items.find((x: {catalog_item_public_id:string})=>x.catalog_item_public_id===fixture.catalog_item);
  expect(item).toBeTruthy(); expect(item.public_id).not.toBe(fixture.catalog_item); expect(item.quantity).toBe("12.500000");
  await page.reload(); await openCargoDetails(page); await expect(page.getByRole("article").filter({hasText:fixture.catalog_name}).first()).toBeVisible();
  await unit(page); const eligible=page.getByLabel("انتخاب بار قابل تخصیص"); await expect(eligible.locator("option",{hasText:fixture.catalog_name})).toHaveCount(1); await eligible.selectOption(item.public_id); const allocatedResponse=page.waitForResponse(response=>response.url().includes("/allocations")&&response.request().method()==="POST"&&response.status()===201); await page.getByRole("button",{name:"تخصیص بار"}).click(); await allocatedResponse;
  const allocation=await (await page.request.get(`/api/v2/projects/${fixture.project_a}/execution-units/${fixture.unit}/shared-transport`,{headers:await headers(page)})).json();
  const allocated=allocation.data.allocations.find((x:{description:string})=>x.description===fixture.catalog_name);
  expect(allocated).toBeTruthy(); expect(allocated.public_id).not.toBe(item.public_id); expect(allocated.public_id).not.toBe(fixture.unit); expect(allocated.allocated_quantity).toBe("12.500000");
  const canonical=await page.request.get(`/api/internal/operational-shipments/${fixture.shipment_a}/canonical-transport-allocations`,{headers:await headers(page)}); const canonicalBody=await canonical.text(); expect(canonical.status(),canonicalBody).toBe(200);
  await shipment(page); await page.waitForTimeout(1_000); expect(e.network,"failed requests after allocation return").toEqual([]); await expect(page.getByText("وضعیت و پیگیری حمل")).toBeVisible(); await expect(page.getByRole("article").filter({hasText:fixture.catalog_name}).first()).toContainText("12.5 PALLET"); await expect(page.getByRole("article").filter({hasText:"SHARED-E2E-UNIT"}).last()).toContainText(fixture.catalog_name);
  await page.reload(); await openCargoDetails(page); await page.waitForTimeout(1_000); expect(e.network,"failed requests after retained-state reload").toEqual([]); await expect(page.getByRole("article").filter({hasText:"SHARED-E2E-UNIT"}).last()).toContainText(fixture.catalog_name);
  const tracking=await (await page.request.get(`/api/internal/operational-shipments/${fixture.shipment_a}/transport-tracking`,{headers:await headers(page)})).json();
  const row=tracking.tracking.units.find((x:{source:string;unit_code:string})=>x.source==="canonical_execution"&&x.unit_code==="SHARED-E2E-UNIT");
  expect(row.allocated_cargo).toEqual(expect.arrayContaining([expect.objectContaining({cargo_name:fixture.catalog_name,allocated_quantity:"12.500000",cargo_owner:"[SHARED-E2E] Customer A"})]));
  clean(e);
});
