import { beforeEach, describe, expect, it, vi } from "vitest";
import { request } from "@/lib/api";
import {
  getControlTowerPage,
  normalizeControlTowerPage,
  type ControlTowerApiPage,
} from "@/control-tower/api";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  request: vi.fn(),
}));

const rawPage: ControlTowerApiPage = {
  evaluatedAt: "2026-09-20T12:00:00Z",
  state: "complete",
  notice: null,
  emptyMessage: null,
  summary: {
    total: 31,
    attentionCounts: { urgent: 12, followUp: 10, review: 9 },
  },
  page: { limit: 25, offset: 0, returned: 1, hasMore: true, nextCursor: "opaque+/cursor==" },
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
    expect(page.summary).toEqual({
      total: 31,
      attentionCounts: { urgent: 12, follow_up: 10, review: 9 },
    });
    expect(page.page).toMatchObject({ limit: 25, offset: 0, returned: 1, hasMore: true });
    expect(page.page.nextCursor).toBe("opaque+/cursor==");
  });

  it("maps supported attention and search and passes the cursor without parsing it", async () => {
    vi.mocked(request).mockResolvedValue({ data: rawPage });
    await getControlTowerPage("follow_up", "opaque+/cursor==", "REQ-42 سارا");
    expect(request).toHaveBeenCalledWith(
      "/api/control-tower/shipments?page_size=25&attention=follow_up&search=REQ-42+%D8%B3%D8%A7%D8%B1%D8%A7&cursor=opaque%2B%2Fcursor%3D%3D",
    );
  });

  it("requests the bounded default page without optional filters", async () => {
    vi.mocked(request).mockResolvedValue({ data: rawPage });
    await getControlTowerPage();
    expect(request).toHaveBeenCalledWith("/api/control-tower/shipments?page_size=25");
  });
});
