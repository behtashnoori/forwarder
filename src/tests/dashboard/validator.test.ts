import { describe, expect, it } from "vitest";
import { operationsControlTower } from "@/dashboard/control-tower";
import { validateDashboardDefinition } from "@/dashboard/validator";
import type { AnalyticsSemanticRegistry } from "@/lib/api";

const metric = (key:string, dimensions:string[] = []) => ({ metric_key:key,business_name:key,grain:"fact",unit:"count",readiness:"READY" as const,supported_dimensions:dimensions,supported_filters:["TIME","CUSTOMER","PROJECT"],supported_time_dimensions:[key === "DELAY_CASE_COUNT" ? "started" : "created"],supported_time_grains:["day"],drilldown_type:"shipment_list",drilldown_supported:true,semantic_version:"analytics-semantic-v1" });
const registry: AnalyticsSemanticRegistry = { semantic_version:"analytics-semantic-v1", metrics:[metric("ACTIVE_SHIPMENT_COUNT"),metric("OPEN_EXCEPTION_COUNT"),metric("OPEN_WORK_ITEM_COUNT"),metric("DOCUMENT_READINESS_COVERAGE"),metric("SHIPMENT_COUNT",["SHIPMENT_STATUS"]),metric("ROUTE_LEG_COUNT",["LEG_STATUS","TRANSPORT_MODE"]),metric("DELAY_CASE_COUNT",["TIME"])], dimensions:["TIME","CUSTOMER","PROJECT","SHIPMENT_STATUS","LEG_STATUS","TRANSPORT_MODE"].map((dimension_key) => ({dimension_key,business_name:dimension_key,identity_source:"test",history_policy:"test",readiness:"READY" as const,nullable:true,semantic_version:"analytics-semantic-v1"})), relationships:[],coverage:{},null_semantics:["VALUE","ZERO","NULL_UNKNOWN","NOT_APPLICABLE","NOT_READY","OUT_OF_SCOPE"] };
describe("Dashboard definition validator", () => {
  it("accepts the governed system Control Tower definition", () => expect(validateDashboardDefinition(operationsControlTower, registry)).toEqual([]));
  it("keeps the uncertified Delay Trend time-segment drilldown disabled", () => {
    const delayTrend = operationsControlTower.widgets.find((widget) => widget.widget_id === "delay-cases");
    expect(delayTrend?.query).toMatchObject({ metric_keys:["DELAY_CASE_COUNT"], dimension_keys:["TIME"], time_dimension:"started", time_grain:"day" });
    expect(delayTrend?.drilldown.enabled).toBe(false);
  });
  it("rejects a non-executable or incompatible metric definition", () => { const invalid = structuredClone(operationsControlTower); invalid.widgets[0].query.metric_keys = ["ON_TIME_SHIPMENT_PERCENT"]; invalid.widgets[0].query.dimension_keys = ["SHIPMENT_STATUS"]; const issues = validateDashboardDefinition(invalid, registry); expect(issues.some((item) => item.message.includes("Unknown metric"))).toBe(true); });
  it("rejects a semantic-version mismatch", () => { expect(validateDashboardDefinition(operationsControlTower, {...registry,semantic_version:"analytics-semantic-v2"})).not.toEqual([]); });
});
