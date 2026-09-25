import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OrganizationReferenceCatalogTab from "@/components/OrganizationReferenceCatalogTab";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchOrganizationReferenceCatalog: vi.fn(),
    setOrganizationReferenceCatalogActive: vi.fn(),
  };
});

const inactiveItem: api.OrganizationReferenceCatalogItem = {
  public_id: "cargo-type-1",
  code: "CARGO_GENERAL",
  fa_name: "کالای عمومی",
  en_name: "General cargo",
  description: "تعریف مرکزی کنترل‌شده",
  display_order: 10,
  central_active: true,
  organization_active: false,
  selectable: false,
  activation_public_id: null,
  activation_version: null,
  origin: "CENTRAL_SYSTEM",
  created_at: "2026-09-25T08:00:00Z",
  updated_at: "2026-09-25T08:00:00Z",
};

describe("OrganizationReferenceCatalogTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchOrganizationReferenceCatalog).mockResolvedValue({ items: [inactiveItem], page: 1, pages: 1 });
  });

  it("activates and deactivates with the refreshed activation version", async () => {
    const activeItem = {
      ...inactiveItem,
      organization_active: true,
      selectable: true,
      activation_public_id: "activation-1",
      activation_version: 7,
    };
    vi.mocked(api.setOrganizationReferenceCatalogActive)
      .mockResolvedValueOnce({ item: activeItem })
      .mockResolvedValueOnce({ item: { ...activeItem, organization_active: false, selectable: false, activation_version: 8 } });

    render(<OrganizationReferenceCatalogTab />);
    fireEvent.click(await screen.findByRole("button", { name: "فعال‌سازی برای سازمان" }));
    await waitFor(() => expect(api.setOrganizationReferenceCatalogActive).toHaveBeenCalledWith("cargo-types", inactiveItem, true));

    fireEvent.click(await screen.findByRole("button", { name: "غیرفعال‌سازی برای سازمان" }));
    await waitFor(() => expect(api.setOrganizationReferenceCatalogActive).toHaveBeenLastCalledWith("cargo-types", activeItem, false));
    expect((await screen.findAllByText("غیرفعال برای سازمان")).length).toBeGreaterThan(0);
  });

  it("keeps a centrally inactive definition read-only", async () => {
    vi.mocked(api.fetchOrganizationReferenceCatalog).mockResolvedValue({
      items: [{ ...inactiveItem, central_active: false, organization_active: true, activation_public_id: "activation-1", activation_version: 3 }],
    });
    render(<OrganizationReferenceCatalogTab />);
    expect(await screen.findByText("فقط برای خواندن سابقه")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /فعال‌سازی برای سازمان|غیرفعال‌سازی برای سازمان/ })).not.toBeInTheDocument();
  });

  it("selects a family and exposes a stable organization-definition search", async () => {
    const user = userEvent.setup();
    render(<OrganizationReferenceCatalogTab />);
    await screen.findByText("CARGO_GENERAL");
    await user.click(screen.getByRole("tab", { name: "انواع بسته‌بندی" }));
    await waitFor(() => expect(api.fetchOrganizationReferenceCatalog).toHaveBeenCalledWith("packaging-types", expect.objectContaining({ page: 1 })));
    fireEvent.change(screen.getByLabelText("جست‌وجوی تعاریف سازمان"), { target: { value: "پالت" } });
    await waitFor(() => expect(api.fetchOrganizationReferenceCatalog).toHaveBeenCalledWith("packaging-types", expect.objectContaining({ q: "پالت" })));
  });

  it("renders loading, empty, error, and denied states distinctly", async () => {
    vi.mocked(api.fetchOrganizationReferenceCatalog).mockImplementationOnce(() => new Promise(() => undefined));
    const loadingView = render(<OrganizationReferenceCatalogTab />);
    expect(screen.getByRole("status")).toHaveTextContent("در حال دریافت تعاریف قابل استفاده سازمان");
    loadingView.unmount();

    vi.mocked(api.fetchOrganizationReferenceCatalog).mockResolvedValueOnce({ items: [] });
    const emptyView = render(<OrganizationReferenceCatalogTab />);
    expect(await screen.findByText("در این گروه هنوز تعریف مرکزی تأییدشده‌ای برای انتخاب سازمان وجود ندارد.")).toBeInTheDocument();
    emptyView.unmount();

    vi.mocked(api.fetchOrganizationReferenceCatalog).mockRejectedValueOnce(new Error("offline"));
    const errorView = render(<OrganizationReferenceCatalogTab />);
    expect(await screen.findByRole("alert")).toHaveTextContent("دریافت تعاریف سازمان انجام نشد");
    errorView.unmount();

    vi.mocked(api.fetchOrganizationReferenceCatalog).mockRejectedValueOnce(new api.ApiError(403, "FORBIDDEN", "forbidden"));
    render(<OrganizationReferenceCatalogTab />);
    expect(await screen.findByRole("alert")).toHaveTextContent("فقط برای مدیر سازمان");
  });
});
