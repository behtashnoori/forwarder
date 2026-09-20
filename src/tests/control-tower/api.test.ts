import { beforeEach, describe, expect, it, vi } from "vitest";
import { request } from "@/lib/api";
import {
  getControlTowerPage,
  normalizeControlTowerPage,
  type ControlTowerPage,
} from "@/control-tower/api";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  request: vi.fn(),
}));

const rawPage: ControlTowerPage = {
  evaluatedAt: "2026-09-20T12:00:00Z",
  state: "complete",
  notice: null,
  emptyMessage: null,
  page: { nextCursor: "opaque+/cursor==" },
  items: [{
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
      currentLocation: null,
      locationState: "UNAVAILABLE",
      unitCount: 1,
      latestEventOccurredAt: "2026-09-20T08:00:00Z",
      latestEventRecordedAt: "2026-09-20T09:00:00Z",
      latestEventType: "arrived",
      source: "operational_event",
      projectionState: "available",
    },
    workSummary: { reasonCount: 2, openAttention: true },
    attention: "urgent",
    attentionLabel: "اقدام فوری",
    ownerName: null,
    primaryReason: { semantic: "delay", title: "تأخیر باز", explanation: "نیازمند اقدام", time: [] },
    additionalReasons: [],
    destination: "/operations/shipments/shipment-1",
  }],
};

describe("Control Tower feature adapter", () => {
  beforeEach(() => vi.clearAllMocks());

  it("preserves D1 facts, missing values, transport distinctions, timestamps, and opaque cursor", () => {
    const page = normalizeControlTowerPage({ data: rawPage });
    const item = page.items[0];
    expect(item.requestTransport?.internationalTransportMethod).toBe("sea");
    expect(item.actualRouteModes).toEqual(["road", "rail", "road"]);
    expect(item.operationalStatus).toBe("in_progress");
    expect(item.progress.latestEventOccurredAt).toBe("2026-09-20T08:00:00Z");
    expect(item.progress.latestEventRecordedAt).toBe("2026-09-20T09:00:00Z");
    expect(item.progress.currentLocation).toBeNull();
    expect(item.ownerName).toBeNull();
    expect(page.page.nextCursor).toBe("opaque+/cursor==");
  });

  it("maps only supported attention and passes the cursor without parsing it", async () => {
    vi.mocked(request).mockResolvedValue({ data: rawPage });
    await getControlTowerPage("follow_up", "opaque+/cursor==");
    expect(request).toHaveBeenCalledWith(
      "/api/control-tower/shipments?page_size=25&attention=follow_up&cursor=opaque%2B%2Fcursor%3D%3D",
    );
  });

  it("does not invent a frontend-only filter", async () => {
    vi.mocked(request).mockResolvedValue({ data: rawPage });
    await getControlTowerPage();
    expect(request).toHaveBeenCalledWith("/api/control-tower/shipments?page_size=25");
  });
});
