import { execFileSync } from "node:child_process";
import { describe, expect, it } from "vitest";
import manifest from "../../../contracts/dashboard/system/operations-control-tower.v1.json";
import { operationsControlTower } from "@/dashboard/control-tower";

describe("canonical system dashboard manifest", () => {
  it("FROZEN_CONTROL_TOWER_PARITY=PASS", () => {
    const source = execFileSync("git", ["show", "a5519feb76a56057b709f6874cc4a2102b81123c:src/dashboard/control-tower.ts"], { encoding: "utf8" })
      .replace(/^import[^\n]+\n/, "").replace("export const operationsControlTower: DashboardDefinition = ", "return ");
    const frozen = new Function(source)();
    expect(manifest.definition).toEqual(frozen);
  });

  it("SYSTEM_DASHBOARD_SINGLE_SOURCE_OF_TRUTH=PASS", () => {
    expect(operationsControlTower).toBe(manifest.definition);
    expect(manifest.system_dashboard_id).toBe("operations-control-tower");
    expect(manifest.definition.widgets.find((item) => item.widget_id === "delay-cases")?.drilldown.enabled).toBe(false);
  });
});
