import { expect, type Page } from "@playwright/test";

export type ShipmentWorkspaceSection =
  | "summary"
  | "route"
  | "stages"
  | "cargo"
  | "documents"
  | "tracking"
  | "delivery"
  | "closure"
  | "history";

const labels: Record<ShipmentWorkspaceSection, string> = {
  summary: "خلاصه",
  route: "مسیر و اجرا",
  stages: "مراحل عملیاتی",
  cargo: "کالا و تخصیص",
  documents: "اسناد",
  tracking: "پیگیری و ETA",
  delivery: "تحویل",
  closure: "تکمیل و بستن",
  history: "تاریخچه",
};

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export async function openShipmentSection(
  page: Page,
  section: ShipmentWorkspaceSection,
  expectedShipmentId?: string,
) {
  const semanticHeading = page.locator("#shipment-overview h1");
  await expect(semanticHeading).toBeVisible();
  await expect(semanticHeading).not.toHaveText("");
  const current = new URL(page.url());
  const match = current.pathname.match(/^\/operations\/shipments\/([^/]+)(?:\/[^/]+)?$/);
  expect(match, "qualified Shipment workspace URL").not.toBeNull();
  const shipmentId = decodeURIComponent(match![1]);
  if (expectedShipmentId) expect(shipmentId).toBe(expectedShipmentId);
  if (expectedShipmentId) await expect(semanticHeading).not.toHaveText(expectedShipmentId);

  const navigation = page.getByRole("navigation", { name: "بخش‌های پرونده حمل" });
  const link = navigation.getByRole("link", { name: labels[section], exact: true });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(new RegExp(`/operations/shipments/${escapeRegExp(shipmentId)}/${section}(?:[?#]|$)`));
  await expect(link).toHaveAttribute("aria-current", "page");
  await expect(semanticHeading).toBeVisible();
}
