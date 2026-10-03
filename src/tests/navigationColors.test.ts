import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const source = (path: string) => readFileSync(join(process.cwd(), path), "utf8");
const css = source("src/index.css");

const hsl = (name: string) => {
  const match = css.match(new RegExp(`--nav-${name}:\\s*([\\d.]+) ([\\d.]+)% ([\\d.]+)%`));
  if (!match) throw new Error(`missing nav token ${name}`);
  return match.slice(1).map(Number) as [number, number, number];
};
const rgb = ([h, s, l]: [number, number, number]) => {
  s /= 100; l /= 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs((h / 60) % 2 - 1));
  const m = l - c / 2;
  const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return [r + m, g + m, b + m];
};
const luminance = (color: [number, number, number]) => rgb(color)
  .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
  .reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
const contrast = (foreground: string, background: string) => {
  const values = [luminance(hsl(foreground)), luminance(hsl(background))];
  return (Math.max(...values) + 0.05) / (Math.min(...values) + 0.05);
};

describe("semantic navigation colors", () => {
  it.each([
    ["text", "surface", 11.15],
    ["text-muted", "surface", 6.61],
    ["active-text", "active-surface", 9.32],
    ["hover-text", "hover-surface", 9.14],
    ["disabled-text", "surface", 5.24],
  ])("keeps %s on %s at WCAG AA contrast", (foreground, background, expected) => {
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(foreground, background)).toBeCloseTo(expected, 1);
  });

  it("defines shared active, hover, focus-visible and disabled states", () => {
    expect(css).toContain('.navigation-item[aria-current="page"]');
    expect(css).toContain('.navigation-tab[data-state="active"]');
    expect(css).toContain(".navigation-item:hover");
    expect(css).toContain(".navigation-item:focus-visible");
    expect(css).toContain(".navigation-tab:disabled");
    expect(css).toContain("inset 0 -2px 0 hsl(var(--nav-active-indicator))");
    const navRules = css.slice(css.indexOf(".navigation-surface"), css.indexOf(".shipment-workspace {"));
    expect(navRules).not.toMatch(/--(?:warning|secondary|destructive)/);
  });

  it("applies the shared roles to representative navigation surfaces", () => {
    expect(source("src/components/OperationsNav.tsx")).toContain("navigation-item");
    expect(source("src/pages/OperationalShipmentDetail.tsx")).toContain("navigation-item");
    expect(source("src/components/CustomerPortalLayout.tsx")).toContain("navigation-item");
    expect(source("src/components/ui/tabs.tsx")).toContain("navigation-tab");
  });
});
