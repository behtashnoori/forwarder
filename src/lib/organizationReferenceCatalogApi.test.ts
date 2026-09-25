import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchOrganizationReferenceCatalog,
  setOrganizationReferenceCatalogActive,
  type OrganizationReferenceCatalogItem,
} from "./api";

const item: OrganizationReferenceCatalogItem = {
  public_id: "cargo-type-1",
  code: "CARGO_GENERAL",
  fa_name: "کالای عمومی",
  en_name: "General cargo",
  description: null,
  display_order: 0,
  central_active: true,
  organization_active: false,
  selectable: false,
  activation_public_id: null,
  activation_version: null,
  origin: "CENTRAL_SYSTEM",
  created_at: "2026-09-25T08:00:00Z",
  updated_at: "2026-09-25T08:00:00Z",
};

const response = (body: unknown) => new Response(JSON.stringify(body), {
  status: 200,
  headers: { "Content-Type": "application/json" },
});

describe("organization reference catalog API", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("uses the bounded family endpoint and omits version for a new activation", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ item: { ...item, organization_active: true, activation_version: 1 } }));
    vi.stubGlobal("fetch", fetchMock);

    await setOrganizationReferenceCatalogActive("cargo-types", item, true);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/admin/organization-reference-catalog/cargo-types/cargo-type-1/activate"),
      expect.objectContaining({ method: "POST", body: "{}" }),
    );
  });

  it("sends the latest activation version and preserves list pagination", async () => {
    const activeItem = { ...item, organization_active: true, activation_public_id: "activation-1", activation_version: 7 };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ items: [activeItem], page: 2, pages: 3 }))
      .mockResolvedValueOnce(response({ item: { ...activeItem, organization_active: false, activation_version: 8 } }));
    vi.stubGlobal("fetch", fetchMock);

    const page = await fetchOrganizationReferenceCatalog("cargo-types", { page: 2, per_page: 20 });
    expect(page.pages).toBe(3);
    expect(String(fetchMock.mock.calls[0][0])).toContain("page=2");

    await setOrganizationReferenceCatalogActive("cargo-types", activeItem, false);
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ version: 7 }),
    }));
  });
});
