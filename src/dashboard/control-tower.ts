import type { DashboardDefinition } from "./types";
import manifest from "../../contracts/dashboard/system/operations-control-tower.v1.json";

type SystemDashboardManifest = { definition: DashboardDefinition; system_dashboard_id: string; system_version: number; semantic_version: string; dashboard_schema_version: string };
const systemManifest = manifest as unknown as SystemDashboardManifest;
if (systemManifest.definition.semantic_version !== systemManifest.semantic_version) throw new Error("Invalid canonical Control Tower manifest.");
export const operationsControlTower: DashboardDefinition = systemManifest.definition;
export const operationsControlTowerManifest = systemManifest;
