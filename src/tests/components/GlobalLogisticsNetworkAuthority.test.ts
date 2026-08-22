import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

describe("Global Logistics Network authority", () => {
  const source = readFileSync(join(process.cwd(), "src/pages/AdminPanel.tsx"), "utf8");
  it("gates both navigation and content on PLATFORM_ADMIN authority", () => {
    expect(source).toContain('{isPlatformAdmin && <TabsTrigger value="global-logistics-network"');
    expect(source).toContain('{isPlatformAdmin && <TabsContent value="global-logistics-network"');
    expect(source).not.toMatch(/isOrganizationAdmin[^\n]+global-logistics-network/);
  });
});
