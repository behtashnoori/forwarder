import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const source = (path: string) => readFileSync(join(process.cwd(), path), "utf8");

describe("shared light enterprise hierarchy", () => {
  it("keeps one shared page, section, subsection, form and entity hierarchy", () => {
    const css = source("src/index.css");
    for (const role of ["page-heading", "section-heading", "subsection-heading", "form-group", "entity-card"]) {
      expect(css).toContain(`.${role}`);
    }
    expect(source("src/components/ui/card.tsx")).toContain("entity-card");
    expect(source("src/components/ui/card.tsx")).toContain("subsection-heading");
    expect(source("src/pages/OperationalShipmentDetail.tsx")).toContain("page-heading");
    expect(source("src/pages/AdminPanel.tsx")).toContain("page-heading");
    expect(source("src/pages/RequestDetail.tsx")).toContain("page-heading");
    expect(source("src/components/CommercialProgress.tsx")).toContain("page-heading");
  });

  it("keeps CTA semantics solid and preserves the established font family", () => {
    const buttons = source("src/components/ui/button.tsx");
    expect(buttons).not.toContain('primary: "bg-gradient');
    expect(buttons).not.toContain('success: "bg-gradient');
    expect(buttons).toContain('primary: "border border-primary bg-primary');
    expect(buttons).toContain('success: "border border-secondary bg-secondary');
    expect(source("src/index.css")).toContain("--font-family-ui");
    expect(source("src/main.tsx")).toContain('@fontsource-variable/vazirmatn');
  });
});
