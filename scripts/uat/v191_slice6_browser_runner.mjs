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
  page.on("console", m => { if (m.type()==="error" && !/favicon|status of 403/i.test(m.text())) consoleErrors.push(m.text()); });
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
  await page.getByText("Source: Direct", {exact:true}).waitFor({timeout:20000});
  check("direct-detail-source", true, "visible locator reached");
  const directId=page.url().split("/").pop(); const directResponse=await authFetch(sessions.direct_only.tokens.access_token,`/api/operational-shipments/${directId}`); const directBody=await directResponse.json();
  check("direct-no-commercial-lineage", directBody.data.source.shipment_request_id===null&&directBody.data.source.accepted_quote_id===null);
  await page.goto(`${base}/operations/work-queue`,{waitUntil:"networkidle"}); check("work-queue-continuity",page.url().endsWith("/operations/work-queue"));
  await context.close();

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
