import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ControlTowerOperationalView from "@/control-tower/ControlTowerOperationalView";
import { ApiError } from "@/lib/api";
import {
  getControlTowerPage,
  type ControlTowerItem,
  type ControlTowerPage,
} from "@/control-tower/api";

vi.mock("@/components/OperationsNav", () => ({ default: () => <nav>ناوبری عملیات</nav> }));
vi.mock("@/control-tower/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/control-tower/api")>(),
  getControlTowerPage: vi.fn(),
}));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    locale: "fa-IR",
    businessLabel: (value: string) => ({ in_progress: "در حال اجرا", arrived: "رسیده" } as Record<string, string>)[value] ?? `عنوان: ${value}`,
    shippingTypeLabel: (value: string) => ({ international: "بین‌المللی" } as Record<string, string>)[value] ?? value,
    transportLabel: (value: string) => ({ sea: "دریایی", road: "جاده‌ای", rail: "ریلی" } as Record<string, string>)[value] ?? value,
  }),
}));

const item: ControlTowerItem = {
  key: "shipment-1",
  shipmentReference: "shipment-1",
  routeLabel: "تهران → آنکارا",
  transportLabel: "ترکیبی",
  actualRouteModes: ["road", "rail", "road"],
  operationalStatus: "in_progress",
  source: { type: "accepted_quote", requestPublicId: "request-1" },
  requestTransport: {
    shippingType: "international",
    transportMethod: null,
    internationalTransportMethod: "sea",
    domesticTransportMethod: null,
    transportMethodPreference: "sea",
  },
  progress: {
    currentLocation: "وان",
    locationState: "AVAILABLE",
    unitCount: 2,
    latestEventOccurredAt: "2026-09-20T08:00:00Z",
    latestEventRecordedAt: "2026-09-20T09:30:00Z",
    latestEventType: "arrived",
    source: "operational_event",
    projectionState: "available",
  },
  workSummary: { reasonCount: 2, openAttention: true },
  attention: "urgent",
  attentionLabel: "اقدام فوری",
  ownerName: "سارا محمدی",
  primaryReason: {
    semantic: "delay_open",
    title: "تأخیر باز",
    explanation: "زمان برنامه عبور کرده است.",
    time: [{ label: "شروع تأخیر", at: "2026-09-20T07:00:00Z" }],
  },
  additionalReasons: [{ semantic: "document", title: "مدرک آماده نیست", explanation: "سند لازم ثبت نشده است.", time: [] }],
  destination: "/operations/shipments/shipment-1",
};

const page = (
  items: ControlTowerItem[] = [item],
  nextCursor: string | null = null,
  offset = 0,
  total = items.length,
): ControlTowerPage => ({
  evaluatedAt: "2026-09-20T12:00:00Z",
  state: "complete",
  notice: null,
  emptyMessage: items.length ? null : "در حال حاضر موردی برای پیگیری در برج کنترل نمایش داده نمی‌شود.",
  summary: {
    total,
    attentionCounts: { urgent: total, follow_up: 0, review: 0 },
  },
  page: { limit: 25, offset, returned: items.length, hasMore: nextCursor !== null, nextCursor },
  items,
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((ok, fail) => { resolve = ok; reject = fail; });
  return { promise, resolve, reject };
}

function mount() {
  return render(<MemoryRouter><Routes>
    <Route path="/" element={<ControlTowerOperationalView />} />
    <Route path="/operations/shipments/:id" element={<p>جزئیات موجود محموله</p>} />
  </Routes></MemoryRouter>);
}

describe("Golden Control Tower operational view", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("expert_user", "{\"id\":1}");
    localStorage.setItem("expert_token", "token-one");
    vi.mocked(getControlTowerPage).mockResolvedValue(page());
  });

  it("renders the operational D1 facts without collapsing source-of-truth distinctions", async () => {
    mount();
    expect(await screen.findByText("shipment-1")).toBeVisible();
    expect(screen.getByText("در حال اجرا")).toBeVisible();
    expect(screen.getByText("مسئول فعلی: سارا محمدی")).toBeVisible();
    expect(screen.getByText("مکان فعلی: وان")).toBeVisible();
    const transports = screen.getByRole("region", { name: "حمل درخواستی و مسیر واقعی" });
    expect(within(transports).getAllByText("دریایی").length).toBeGreaterThan(0);
    expect(within(transports).getByText("جاده‌ای ← ریلی ← جاده‌ای")).toBeVisible();
    expect(within(transports).getByText("تهران → آنکارا")).toBeVisible();
    expect(screen.getByText("زمان وقوع آخرین رخداد:", { exact: false })).toBeVisible();
    expect(screen.getByText("زمان ثبت آخرین رخداد:", { exact: false })).toBeVisible();
    expect(document.body).toHaveTextContent("۲۰ سپتامبر ۲۰۲۶ (۲۹ شهریور ۱۴۰۵)");
    expect(screen.getByText("۲ مورد باز")).toBeVisible();
    expect(screen.getByText("تأخیر باز")).toBeVisible();
    expect(document.body.textContent).not.toMatch(/notification|provider|recipient/i);
  });

  it("opens the provided existing Shipment Detail destination", async () => {
    mount();
    const link = await screen.findByRole("link", { name: "مشاهده جزئیات محموله" });
    expect(link).toHaveAttribute("href", item.destination);
    fireEvent.click(link);
    expect(await screen.findByText("جزئیات موجود محموله")).toBeVisible();
  });

  it("requests server-side attention and text filters and resets to the first page", async () => {
    mount();
    await screen.findByText("shipment-1");
    fireEvent.click(screen.getByRole("button", { name: /پیگیری/ }));
    await waitFor(() => expect(getControlTowerPage).toHaveBeenLastCalledWith("follow_up", undefined, undefined));
    fireEvent.change(screen.getByRole("textbox", { name: "جست‌وجوی برج کنترل" }), { target: { value: "shipment-42" } });
    fireEvent.click(screen.getByRole("button", { name: "جست‌وجو" }));
    await waitFor(() => expect(getControlTowerPage).toHaveBeenLastCalledWith("follow_up", undefined, "shipment-42"));
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("passes through the opaque cursor and replaces the bounded page", async () => {
    const next = deferred<ControlTowerPage>();
    vi.mocked(getControlTowerPage).mockResolvedValueOnce(page([item], "opaque+/cursor==", 0, 2)).mockReturnValueOnce(next.promise);
    mount();
    fireEvent.click(await screen.findByRole("button", { name: "صفحه بعدی" }));
    const second = { ...item, key: "shipment-2", shipmentReference: "shipment-2" };
    await act(async () => next.resolve(page([second], null, 1, 2)));
    expect(getControlTowerPage).toHaveBeenLastCalledWith(undefined, "opaque+/cursor==", undefined);
    expect(screen.queryByText("shipment-1")).not.toBeInTheDocument();
    expect(screen.getByText("shipment-2")).toBeVisible();
    expect(screen.getByText("نمایش ۲ تا ۲ از ۲")).toBeVisible();
    expect(screen.getByRole("button", { name: "صفحه قبلی" })).toBeEnabled();
  });

  it("does not let an older slower response overwrite newer filter results", async () => {
    const older = deferred<ControlTowerPage>();
    const newerItem = { ...item, key: "shipment-newer", shipmentReference: "shipment-newer" };
    vi.mocked(getControlTowerPage)
      .mockReturnValueOnce(older.promise)
      .mockResolvedValueOnce(page([newerItem]));
    mount();
    fireEvent.click(screen.getByRole("button", { name: /پیگیری/ }));
    expect(await screen.findByText("shipment-newer")).toBeVisible();
    await act(async () => older.resolve(page([item])));
    expect(screen.getByText("shipment-newer")).toBeVisible();
    expect(screen.queryByText("shipment-1")).not.toBeInTheDocument();
  });

  it("shows explicit loading and empty states", async () => {
    vi.mocked(getControlTowerPage).mockReturnValueOnce(new Promise(() => {}));
    const first = mount();
    expect(screen.getByRole("status", { name: "در حال دریافت برج کنترل" })).toBeVisible();
    first.unmount();
    vi.mocked(getControlTowerPage).mockResolvedValueOnce(page([]));
    mount();
    expect(await screen.findByText(/موردی برای پیگیری در برج کنترل/)).toBeVisible();
  });

  it("fails closed on 503 without Semantic Analytics fallback or stale partial cards", async () => {
    vi.mocked(getControlTowerPage)
      .mockResolvedValueOnce(page([item], "next"))
      .mockRejectedValueOnce(new ApiError(503, "EVALUATION_UNAVAILABLE", "private backend detail"));
    mount();
    fireEvent.click(await screen.findByRole("button", { name: "صفحه بعدی" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("هیچ فهرستی نمایش داده نمی‌شود");
    expect(screen.queryByText("shipment-1")).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/Semantic|private backend detail/i);
  });

  it.each([
    [401, "AUTHENTICATION_REQUIRED", "نشست شما"],
    [403, "FORBIDDEN_OPERATION", "مجوز مشاهده"],
  ])("keeps HTTP %s distinct from an empty result", async (status, code, message) => {
    vi.mocked(getControlTowerPage).mockRejectedValueOnce(new ApiError(status, code, "private"));
    mount();
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByText(/موردی برای پیگیری در برج کنترل/)).not.toBeInTheDocument();
  });

  it("represents missing facts as missing instead of fabricating values", async () => {
    vi.mocked(getControlTowerPage).mockResolvedValueOnce(page([{ ...item, ownerName: null, routeLabel: null, actualRouteModes: [], requestTransport: null, progress: { ...item.progress, currentLocation: null, latestEventOccurredAt: null, latestEventRecordedAt: null, latestEventType: null } }]));
    mount();
    expect(await screen.findByText("مسئول فعلی: ثبت نشده")).toBeVisible();
    expect(screen.getByText("مکان فعلی: ثبت نشده")).toBeVisible();
    expect(screen.getByText("در درخواست ثبت نشده است.")).toBeVisible();
    expect(screen.getByText("مسیر فعال ثبت نشده است.")).toBeVisible();
  });

  it("keeps core content reachable with the existing responsive stacking pattern", async () => {
    mount();
    await screen.findByText("shipment-1");
    expect(screen.getByRole("main")).toHaveAttribute("dir", "rtl");
    expect(screen.getByRole("link", { name: "مشاهده جزئیات محموله" })).toHaveClass("w-full", "sm:w-auto");
    expect(screen.getByRole("region", { name: "حمل درخواستی و مسیر واقعی" })).toHaveClass("md:grid-cols-2");
  });
});
