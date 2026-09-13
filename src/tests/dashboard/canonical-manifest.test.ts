import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import manifest from "../../../contracts/dashboard/system/operations-control-tower.v1.json";
import { operationsControlTower } from "@/dashboard/control-tower";

describe("canonical system dashboard manifest", () => {
  it("FROZEN_CONTROL_TOWER_PARITY=PASS", () => {
    const canonicalize = (value: unknown): unknown => Array.isArray(value) ? value.map(canonicalize) : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, item]) => [key, canonicalize(item)])) : value;
    const normalized = JSON.stringify(canonicalize(manifest.definition));
    expect(createHash("sha256").update(normalized).digest("hex")).toBe("550a5bce4128c850ea500391177e88446f26ee88dda5e369082081cf1e9aec25");
  });

  it("SYSTEM_DASHBOARD_SINGLE_SOURCE_OF_TRUTH=PASS", () => {
    expect(operationsControlTower).toBe(manifest.definition);
    expect(manifest.system_dashboard_id).toBe("operations-control-tower");
    expect(manifest.definition.widgets.find((item) => item.widget_id === "delay-cases")?.drilldown.enabled).toBe(false);
  });
});
