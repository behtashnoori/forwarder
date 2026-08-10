import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const root = "C:\\Users\\pc\\AppData\\Local\\npm-cache\\_npx\\e41f203b7505f1fb\\node_modules\\playwright-core";
const executablePath = "C:\\Users\\pc\\AppData\\Local\\ms-playwright\\chromium-1200\\chrome-win64\\chrome.exe";
const { chromium } = require(root);
const base = process.env.PHASE1B_UAT_BASE_URL;
const api = process.env.PHASE1B_UAT_API_URL;
const password = process.env.PHASE1B_UAT_PASSWORD;
const evidence = process.env.PHASE1B_UAT_EVIDENCE_DIR;
if (![base, api, password, evidence].every(Boolean)) throw new Error("Slice 6 UAT environment is incomplete");
fs.mkdirSync(evidence, { recursive: true });
const checks = [];
const check = (name, ok, detail = "") => { checks.push({name,status:ok?"PASS":"FAIL",detail}); if (!ok) throw new Error(`${name}: ${detail}`); };
const login = async name => {
  const response = await fetch(`${api}/api/expert/auth/login`, {method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({username:`phase1b_uat_${name}`,password})});
  const body = await response.json(); check(`login-${name}`, response.status === 200, `status=${response.status}`); return body;
};
const authFetch = (token, route, options={}) => fetch(`${api}${route}`, {...options,headers:{"content-type":"application/json",authorization:`Bearer ${token}`,...options.headers}});
const sessions = {};
for (const name of ["direct_only","quote_only","legacy_quote","both","no_permission","admin"]) sessions[name] = await login(name);
const browser = await chromium.launch({executablePath, headless:true});
const consoleErrors = [];
const pageFor = async (name, viewport={width:1280,height:800}) => {
  const context = await browser.newContext({viewport}); const page = await context.newPage();
  page.on("console", m => { if (m.type()==="error" && !/favicon|status of (403|404|409)|ERR_CONNECTION_REFUSED|ERR_CONNECTION_RESET|ERR_FAILED/i.test(m.text())) consoleErrors.push(m.text()); });
  await page.goto(base); await page.evaluate(({token,user})=>{localStorage.setItem("expert_token",token);localStorage.setItem("expert_user",JSON.stringify(user));localStorage.setItem("forwarder.language","en");},{token:sessions[name].tokens.access_token,user:sessions[name].expert});
  return {context,page};
};
try {
  for (const [name,direct,quote] of [["direct_only",true,false],["quote_only",false,true],["legacy_quote",false,true],["both",true,true],["no_permission",false,false]]) {
    const {context,page}=await pageFor(name); await page.goto(`${base}/operations/shipments/new`,{waitUntil:"networkidle"});
    check(`${name}-direct-source`, (await page.getByText("Direct operation",{exact:true}).count()>0)===direct);
    check(`${name}-quote-source`, (await page.getByText("From accepted quote",{exact:true}).count()>0)===quote);
    if (!direct&&!quote) check(`${name}-cannot-create`, await page.getByRole("alert").getByText(/No operation creation permission/).isVisible());
    await context.close();
  }
  const {context,page}=await pageFor("direct_only"); await page.goto(`${base}/operations/shipments/new?source=direct`,{waitUntil:"networkidle"});
  await page.getByLabel("Customer", {exact:true}).selectOption({index:1}); await page.getByLabel("Origin Province", {exact:true}).selectOption({index:1}); await page.getByLabel("Destination Province", {exact:true}).selectOption({index:2});
  await page.getByLabel("Planned departure").fill("2030-03-01T10:00"); await page.getByLabel("Planned arrival").fill("2030-03-02T10:00");
  await page.getByRole("button",{name:"Create operation"}).dblclick(); await page.waitForURL(/operations\/shipments\/[0-9a-f-]+$/,{timeout:20000});
  await page.getByText("Source: Direct operation", {exact:true}).waitFor({timeout:20000});
  check("direct-detail-source", true, "visible locator reached");
  const directId=page.url().split("/").pop(); const directResponse=await authFetch(sessions.direct_only.tokens.access_token,`/api/operational-shipments/${directId}`); const directBody=await directResponse.json();
  check("direct-no-commercial-lineage", directBody.data.source.shipment_request_id===null&&directBody.data.source.accepted_quote_id===null);
  await page.goto(`${base}/operations/work-queue`,{waitUntil:"networkidle"}); check("work-queue-continuity",page.url().endsWith("/operations/work-queue"));
  await context.close();

  // Deep links are exercised as browser navigation, reload and real history entries.
  const {context:deepContext,page:deepPage}=await pageFor("direct_only");
  await deepPage.goto(`${base}/operations/shipments`,{waitUntil:"networkidle"});
  await deepPage.goto(`${base}/operations/shipments/${directId}`,{waitUntil:"networkidle"});
  check("deep-link-normal",await deepPage.getByText("Source: Direct operation",{exact:true}).isVisible());
  await deepPage.reload({waitUntil:"networkidle"});
  check("deep-link-refresh",deepPage.url().endsWith(`/operations/shipments/${directId}`)&&await deepPage.getByRole("heading",{name:"Operational shipment detail"}).isVisible());
  await deepPage.goBack({waitUntil:"networkidle"}); const historyBack=deepPage.url().endsWith("/operations/shipments");
  await deepPage.goForward({waitUntil:"networkidle"});
  check("deep-link-history",historyBack&&deepPage.url().endsWith(`/operations/shipments/${directId}`));
  await deepPage.goto(`${base}/operations/shipments/not-a-valid-identity`,{waitUntil:"networkidle"});
  check("deep-link-invalid",await deepPage.getByRole("alert").isVisible());
  await deepPage.goto(`${base}/operations/shipments/00000000-0000-4000-8000-000000000001`,{waitUntil:"networkidle"});
  check("deep-link-stale-deleted",await deepPage.getByRole("alert").isVisible());
  await deepContext.close();

  // Downstream surfaces are loaded from each actual browser-created operation.
  const {context:downstreamContext,page:downstreamPage}=await pageFor("admin");
  await downstreamPage.goto(`${base}/operations/shipments/${directId}`,{waitUntil:"networkidle"});
  await downstreamPage.locator('[aria-label="Shipment Economics"]').waitFor({timeout:20000});
  check("direct-economics",true);
  await downstreamPage.getByText("Create authorized FX fact",{exact:true}).waitFor();check("direct-fx",true);
  await downstreamPage.getByText("Operational Execution",{exact:true}).waitFor();check("direct-operational-execution",true);
  await downstreamPage.goto(`${base}/operations/work-queue`,{waitUntil:"networkidle"});await downstreamPage.getByTestId("projection-health").waitFor();const directOip=await downstreamPage.getByTestId("projection-health").innerText();check("direct-oip",/Intelligence health: (FRESH|STALE|REBUILDING|DEGRADED)/.test(directOip),directOip);
  await downstreamContext.close();

  // Actual keyboard traversal and activation, rather than component-only semantics.
  const {context:keyContext,page:keyPage}=await pageFor("direct_only");
  await keyPage.goto(`${base}/operations/shipments/new`,{waitUntil:"networkidle"});
  await keyPage.keyboard.press("Tab");
  let keyboardReached=false;
  for(let i=0;i<30;i++){const text=await keyPage.evaluate(()=>document.activeElement?.textContent||"");if(text.includes("Direct operation")){keyboardReached=true;break;}await keyPage.keyboard.press("Tab");}
  check("keyboard-traversal",keyboardReached);
  await keyPage.keyboard.press("Enter");
  check("keyboard-interaction",await keyPage.getByLabel("Customer",{exact:true}).isVisible());
  await keyContext.close();

  const locationCase=async(name,configure)=>{
    const {context:ctx,page:p}=await pageFor("admin");
    await p.goto(`${base}/operations/shipments/new?source=direct`,{waitUntil:"networkidle"});
    await p.getByLabel("Customer",{exact:true}).selectOption({index:1});
    await configure(p);
    await p.getByLabel("Planned departure").fill(`2031-01-${String(checks.length%20+1).padStart(2,"0")}T10:00`);
    await p.getByLabel("Planned arrival").fill(`2031-02-${String(checks.length%20+1).padStart(2,"0")}T10:00`);
    const request=p.waitForRequest(r=>r.url().endsWith("/api/operational-shipments")&&r.method()==="POST",{timeout:10000});
    await p.getByRole("button",{name:"Create operation"}).click();
    let sent;try{sent=await request}catch(error){const alerts=await p.getByRole("alert").allInnerTexts();throw new Error(`${name} did not submit: ${alerts.join(" | ")}`)} await p.waitForURL(/operations\/shipments\/[0-9a-f-]+$/,{timeout:20000});
    check(name,true,JSON.stringify(sent.postDataJSON()?.route||sent.postDataJSON()).slice(0,500));
    await ctx.close();
  };
  const domestic=async(p,side,index)=>p.getByLabel(`${side} Province`,{exact:true}).selectOption({index});
  const international=async(p,side,iran=false)=>{
    await p.getByLabel(`${side} Route type`,{exact:true}).selectOption("international");
    const country=p.getByLabel(`${side} Country`,{exact:true});
    const options=await country.locator("option").evaluateAll(nodes=>nodes.map(n=>({value:n.value,text:n.textContent||""})).filter(x=>x.value));
    const candidates=options.filter(x=>iran?/Iran|ایران/i.test(x.text):!/Iran|ایران/i.test(x.text));const selected=candidates[!iran&&side==="Destination"&&candidates.length>1?1:0];
    if(!selected)throw new Error(`${side} country fixture missing`); await country.selectOption(selected.value);
    if(!iran)await p.getByLabel(`${side} International city or operational point`,{exact:true}).selectOption({index:1});
  };
  const iranFixtureResponse=await authFetch(sessions.admin.tokens.access_token,"/api/locations/iran-destinations?limit=100");const iranFixtureBody=await iranFixtureResponse.json();check("location-iran-fixture-api",iranFixtureResponse.status===200&&iranFixtureBody.data?.length>=4,JSON.stringify(iranFixtureBody));
  await locationCase("location-non-iran-origin",async p=>{await international(p,"Origin");await domestic(p,"Destination",2)});
  await locationCase("location-iran-origin",async p=>{await international(p,"Origin",true);await p.getByLabel("Origin Iran province",{exact:true}).selectOption({index:1});await domestic(p,"Destination",2)});
  await locationCase("location-non-iran-destination",async p=>{await domestic(p,"Origin",1);await international(p,"Destination")});
  await locationCase("location-iran-destination",async p=>{await domestic(p,"Origin",1);await international(p,"Destination",true);const selector=p.getByLabel("Destination in Iran",{exact:true});await selector.waitFor();await selector.selectOption({index:1})});
  for(const [suffix,prefix] of [["city","city:"],["port","port:"],["customs","customs:"]])await locationCase(`location-iran-destination-${suffix}`,async p=>{await domestic(p,"Origin",1);await international(p,"Destination",true);const selector=p.getByLabel("Destination in Iran",{exact:true});await selector.waitFor();const values=await selector.locator("option").evaluateAll(nodes=>nodes.map(n=>n.value));const value=values.find(v=>v.startsWith(prefix))||"";check(`location-${suffix}-fixture`,!!value,JSON.stringify(values));await selector.selectOption(value)});
  const {context:duplicateContext,page:duplicatePage}=await pageFor("admin");
  await duplicatePage.goto(`${base}/operations/shipments/new?source=direct`,{waitUntil:"networkidle"});await international(duplicatePage,"Destination",true);
  const duplicateSelector=duplicatePage.getByLabel("Destination in Iran",{exact:true});await duplicateSelector.waitFor();const duplicateLabels=await duplicateSelector.locator("option").evaluateAll(nodes=>nodes.map(n=>n.textContent||"").filter(Boolean));
  check("location-duplicate-disambiguation",new Set(duplicateLabels).size===duplicateLabels.length&&duplicateLabels.some(x=>/city|port|customs|شهر|بندر|گمرک/i.test(x)),`options=${duplicateLabels.length}`);await duplicateContext.close();
  await locationCase("location-non-iran-international",async p=>{await international(p,"Origin");await international(p,"Destination")});

  // Release identity failure states are projected in Chromium from controlled transport outcomes.
  for(const [state,mode] of [["MISMATCH","mismatch"],["BACKEND_UNAVAILABLE","abort"],["IDENTITY_UNAVAILABLE","empty"]]){
    const {context:identityContext,page:identityPage}=await pageFor("admin");
    await identityPage.route("**/api/system/release-identity",async route=>{if(mode==="abort")return route.abort("connectionrefused");const data=mode==="mismatch"?{application_version:"1.9.0",backend_version:"1.9.0"}:{};await route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({projection:"support",data})});});
    await identityPage.goto(`${base}/operations/shipments`,{waitUntil:"networkidle"});
    await identityPage.locator(`[data-identity-state='${state}']`).waitFor();
    check(`identity-${state.toLowerCase()}`,true,"visible state attribute reached");
    await identityContext.close();
  }

  const {context:quoteContext,page:quotePage}=await pageFor("admin");
  await quotePage.goto(`${base}/operations/shipments/new?source=accepted_quote`,{waitUntil:"networkidle"});
  const quoteSelector=quotePage.getByLabel("Accepted quote",{exact:true});
  await quoteSelector.waitFor();
  const quoteOptions=await quoteSelector.locator("option").count();
  check("quote-browser-selector-populated",quoteOptions>1,`options=${quoteOptions}`);
  await quoteSelector.selectOption({index:1});
  const browserQuoteId=await quoteSelector.inputValue();
  await quotePage.getByLabel("Origin Province",{exact:true}).selectOption({index:1});
  await quotePage.getByLabel("Destination Province",{exact:true}).selectOption({index:2});
  await quotePage.getByLabel("Planned departure",{exact:true}).fill("2030-03-05T10:00");
  await quotePage.getByLabel("Planned arrival",{exact:true}).fill("2030-03-06T10:00");
  const quoteCreateResponse=quotePage.waitForResponse(response=>response.url().includes("/api/operational-shipments/from-accepted-quote")&&response.request().method()==="POST");
  await quotePage.getByRole("button",{name:"Create operational shipment"}).click();
  const quoteCreate=await quoteCreateResponse;
  check("quote-browser-submit",[200,201].includes(quoteCreate.status()),`status=${quoteCreate.status()}`);
  await quotePage.waitForURL(/operations\/shipments\/[0-9a-f-]+$/,{timeout:20000});
  await quotePage.getByText("Source: From accepted quote",{exact:true}).waitFor();
  await quotePage.getByText(/^Request:/).waitFor();
  await quotePage.getByText(/^Quote:/).waitFor();
  check("quote-browser-detail",true,"source, customer, request and quote lineage visible");
  const browserQuoteShipmentId=quotePage.url().split("/").pop();
  await quotePage.locator('[aria-label="Document Readiness"]').waitFor({timeout:20000});check("quote-documents-mdpm",true);
  await quotePage.locator('[aria-label="Shipment Economics"]').waitFor({timeout:20000});check("quote-economics",true);
  await quotePage.getByText("Create authorized FX fact",{exact:true}).waitFor();check("quote-fx",true);
  await quotePage.getByText("Operational Execution",{exact:true}).waitFor();check("quote-operational-execution",true);
  await quotePage.goto(`${base}/operations/work-queue`,{waitUntil:"networkidle"});await quotePage.getByTestId("projection-health").waitFor();const quoteOip=await quotePage.getByTestId("projection-health").innerText();check("quote-oip",/Intelligence health: (FRESH|STALE|REBUILDING|DEGRADED)/.test(quoteOip),quoteOip);
  await quotePage.goto(`${base}/operations/shipments`,{waitUntil:"networkidle"});
  check("quote-browser-list",await quotePage.locator(`a[href='/operations/shipments/${browserQuoteShipmentId}']`).count()>0);
  await quotePage.goto(`${base}/operations/shipments/new?source=accepted_quote`,{waitUntil:"networkidle"});
  check("quote-browser-ineligible-after-create",await quotePage.getByLabel("Accepted quote",{exact:true}).locator(`option[value='${browserQuoteId}']`).count()===0);
  await quotePage.screenshot({path:path.join(evidence,"slice63-quote-browser-detail.png"),fullPage:true});
  await quoteContext.close();

  const {context:rtlContext,page:rtlPage}=await pageFor("admin");
  await rtlPage.evaluate(()=>localStorage.setItem("forwarder.language","fa"));
  await rtlPage.goto(`${base}/operations/shipments/${directId}`,{waitUntil:"networkidle"});
  check("persian-rtl-direction",await rtlPage.locator("main[dir='rtl']").isVisible());
  check("persian-operations-heading",await rtlPage.getByRole("heading",{name:"جزئیات پرونده عملیاتی"}).isVisible());
  const rtlVisible=await rtlPage.locator("main").innerText();
  const forbiddenEnglish=["Shipment Economics","Timeline reconciliation","Replan and revision history","Operational Execution"];
  check("persian-visible-operations-text",forbiddenEnglish.every(value=>!rtlVisible.includes(value)),forbiddenEnglish.filter(value=>rtlVisible.includes(value)).join(", "));
  await rtlPage.screenshot({path:path.join(evidence,"slice63-persian-rtl.png"),fullPage:true});
  await rtlContext.close();

  const prepareQuote=async p=>{await p.goto(`${base}/operations/shipments/new?source=accepted_quote`,{waitUntil:"networkidle"});const selector=p.getByLabel("Accepted quote",{exact:true});await selector.selectOption({index:1});await p.getByLabel("Origin Province",{exact:true}).selectOption({index:1});await p.getByLabel("Destination Province",{exact:true}).selectOption({index:2});await p.getByLabel("Planned departure").fill("2032-03-01T10:00");await p.getByLabel("Planned arrival").fill("2032-03-02T10:00");return selector.inputValue()};
  const {context:actorAContext,page:actorA}=await pageFor("both");const {context:actorBContext,page:actorB}=await pageFor("both");
  const actorQuote=await prepareQuote(actorA);await prepareQuote(actorB);
  await actorA.getByRole("button",{name:"Create operational shipment"}).click();await actorA.waitForURL(/operations\/shipments\/[0-9a-f-]+$/,{timeout:20000});
  await actorB.getByRole("button",{name:"Create operational shipment"}).click();
  await actorB.getByRole("alert").waitFor();
  check("stale-quote-two-actor",(await actorB.getByRole("alert").innerText()).includes("already been converted"),`quote=${actorQuote}`);
  await actorAContext.close();await actorBContext.close();

  const {context:recoveryContext,page:recoveryPage}=await pageFor("both");await prepareQuote(recoveryPage);let dropped=false;
  await recoveryPage.route("**/api/operational-shipments/from-accepted-quote",async route=>{if(route.request().method()!=="POST"||dropped)return route.continue();dropped=true;await route.fetch();await route.abort("connectionreset");});
  await recoveryPage.getByRole("button",{name:"Create operational shipment"}).click();await recoveryPage.getByRole("alert").waitFor();
  await recoveryPage.getByRole("button",{name:"Create operational shipment"}).click();await recoveryPage.waitForURL(/operations\/shipments\/[0-9a-f-]+$/,{timeout:20000});
  const recoveredId=recoveryPage.url().split("/").pop();const recovered=await (await authFetch(sessions.both.tokens.access_token,`/api/operational-shipments/${recoveredId}`)).json();
  check("browser-transient-recovery",dropped&&recovered.data.public_id===recoveredId,"first response dropped; retry reached same idempotent operation");await recoveryContext.close();

  const token=sessions.both.tokens.access_token; const quotes=await (await authFetch(token,"/api/operations/selectors/accepted-quotes?limit=100")).json(); check("eligible-quote",quotes.items.length>0);
  const quoteId=quotes.items[0].id; const route={accepted_quote_id:quoteId,origin:{source_type:"province",source_id:1},destination:{source_type:"province",source_id:2},transport_mode:"road",planned_departure:"2030-04-01T10:00:00Z",planned_arrival:"2030-04-02T10:00:00Z"};
  const idem=`slice6-${Date.now()}`; const first=await authFetch(token,"/api/operational-shipments/from-accepted-quote",{method:"POST",headers:{"Idempotency-Key":idem},body:JSON.stringify(route)}); const firstBody=await first.json();
  const replay=await authFetch(token,"/api/operational-shipments/from-accepted-quote",{method:"POST",headers:{"Idempotency-Key":idem},body:JSON.stringify(route)}); const replayBody=await replay.json();
  check("quote-real-http",[200,201].includes(first.status)); check("quote-idempotent-replay",replay.status===200&&replayBody.data.public_id===firstBody.data.public_id);
  const stale=await authFetch(token,"/api/operational-shipments/from-accepted-quote",{method:"POST",headers:{"Idempotency-Key":`${idem}-stale`},body:JSON.stringify(route)}); const staleBody=await stale.json();
  check("concurrent-quote-conflict",stale.status===409&&staleBody.error.code==="OPERATIONAL_SHIPMENT_ALREADY_EXISTS");
  const changed={...route,transport_mode:"rail"}; const changedResponse=await authFetch(token,"/api/operational-shipments/from-accepted-quote",{method:"POST",headers:{"Idempotency-Key":idem},body:JSON.stringify(changed)}); const changedBody=await changedResponse.json();
  check("changed-payload-conflict",changedResponse.status===409&&changedBody.error.code==="IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD");

  for (const width of [360,390,412,768,1440]) { const {context:ctx,page:p}=await pageFor("admin",{width,height:width<500?844:900}); await p.goto(`${base}/operations/shipments`,{waitUntil:"networkidle"});
    const geometry=await p.evaluate(()=>({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})); check(`responsive-${width}`,geometry.scroll<=geometry.client+1,JSON.stringify(geometry));
    check(`version-${width}`,await p.getByText("Forwarder 1.9.1").first().isVisible()); if(width===390) await p.screenshot({path:path.join(evidence,"slice6-mobile-390.png"),fullPage:true}); await ctx.close(); }
  const normal=await (await authFetch(sessions.direct_only.tokens.access_token,"/api/system/release-identity")).json(); const admin=await (await authFetch(sessions.admin.tokens.access_token,"/api/system/release-identity")).json();
  check("identity-normal-minimal",JSON.stringify(Object.keys(normal.data))===JSON.stringify(["application_version"])); check("identity-admin-support",admin.projection==="support"&&admin.data.backend_version==="1.9.1");
  check("browser-console",consoleErrors.length===0,`count=${consoleErrors.length}; ${consoleErrors.join(" | ").slice(0,1000)}`);
} finally {
  await browser.close();
  fs.writeFileSync(path.join(evidence,"slice6-browser-result.json"),JSON.stringify({generated_at:new Date().toISOString(),playwright_version:require(path.join(root,"package.json")).version,chromium:executablePath,viewports:[360,390,412,768,1440],personas:Object.keys(sessions),checks},null,2)+"\n");
}
