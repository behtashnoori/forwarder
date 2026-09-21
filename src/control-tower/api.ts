import { ApiError, request } from "@/lib/api";

export type ControlTowerAttention = "urgent" | "follow_up" | "review";

export interface ControlTowerReasonTime {
  label: string;
  at: string;
}

export interface ControlTowerReason {
  semantic: string;
  title: string;
  explanation: string;
  time: ControlTowerReasonTime[];
}

export interface ControlTowerRequestTransport {
  shippingType: string | null;
  transportMethod: string | null;
  internationalTransportMethod: string | null;
  domesticTransportMethod: string | null;
  transportMethodPreference: string | null;
}

export interface ControlTowerProgress {
  currentLocation: string | null;
  locationState: string | null;
  unitCount: number;
  latestEventOccurredAt: string | null;
  latestEventRecordedAt: string | null;
  latestEventType: string | null;
  source: string | null;
  projectionState: string | null;
}

export interface ControlTowerWorkSummary {
  reasonCount: number;
  openAttention: boolean;
}

export interface ControlTowerItem {
  key: string;
  shipmentReference: string;
  routeLabel: string | null;
  transportLabel: string | null;
  actualRouteModes: string[];
  operationalStatus: string;
  source: { type: string; requestPublicId: string | null };
  requestTransport: ControlTowerRequestTransport | null;
  progress: ControlTowerProgress;
  workSummary: ControlTowerWorkSummary;
  attention: ControlTowerAttention;
  attentionLabel: string;
  ownerName: string | null;
  primaryReason: ControlTowerReason;
  additionalReasons: ControlTowerReason[];
  destination: string;
}

export interface ControlTowerPage {
  evaluatedAt: string;
  state: "complete";
  notice: string | null;
  emptyMessage: string | null;
  summary: {
    total: number;
    attentionCounts: Record<ControlTowerAttention, number>;
  };
  page: {
    limit: number;
    offset: number;
    returned: number;
    hasMore: boolean;
    nextCursor: string | null;
  };
  items: ControlTowerItem[];
}

export type ControlTowerApiPage = Omit<ControlTowerPage, "summary"> & {
  summary: {
    total: number;
    attentionCounts: { urgent: number; followUp: number; review: number };
  };
};

type ControlTowerApiResponse = { data: ControlTowerApiPage };

const nullable = (value: string | null | undefined): string | null =>
  typeof value === "string" && value.length > 0 ? value : null;

const normalizeReason = (reason: ControlTowerReason): ControlTowerReason => ({
  semantic: reason.semantic,
  title: reason.title,
  explanation: reason.explanation,
  time: reason.time.map(({ label, at }) => ({ label, at })),
});

/**
 * D1 response -> frontend-safe view model. This is intentionally presentation-only:
 * missing facts remain null, request transport stays separate from route modes, and
 * the continuation cursor is copied without inspection or reconstruction.
 */
export function normalizeControlTowerPage(response: ControlTowerApiResponse): ControlTowerPage {
  const data = response.data;
  return {
    evaluatedAt: data.evaluatedAt,
    state: data.state,
    notice: nullable(data.notice),
    emptyMessage: nullable(data.emptyMessage),
    summary: {
      total: data.summary.total,
      attentionCounts: {
        urgent: data.summary.attentionCounts.urgent,
        follow_up: data.summary.attentionCounts.followUp,
        review: data.summary.attentionCounts.review,
      },
    },
    page: {
      limit: data.page.limit,
      offset: data.page.offset,
      returned: data.page.returned,
      hasMore: data.page.hasMore,
      nextCursor: nullable(data.page.nextCursor),
    },
    items: data.items.map((item) => ({
      key: item.key,
      shipmentReference: item.shipmentReference,
      routeLabel: nullable(item.routeLabel),
      transportLabel: nullable(item.transportLabel),
      actualRouteModes: [...item.actualRouteModes],
      operationalStatus: item.operationalStatus,
      source: {
        type: item.source.type,
        requestPublicId: nullable(item.source.requestPublicId),
      },
      requestTransport: item.requestTransport
        ? {
            shippingType: nullable(item.requestTransport.shippingType),
            transportMethod: nullable(item.requestTransport.transportMethod),
            internationalTransportMethod: nullable(item.requestTransport.internationalTransportMethod),
            domesticTransportMethod: nullable(item.requestTransport.domesticTransportMethod),
            transportMethodPreference: nullable(item.requestTransport.transportMethodPreference),
          }
        : null,
      progress: {
        currentLocation: nullable(item.progress.currentLocation),
        locationState: nullable(item.progress.locationState),
        unitCount: item.progress.unitCount,
        latestEventOccurredAt: nullable(item.progress.latestEventOccurredAt),
        latestEventRecordedAt: nullable(item.progress.latestEventRecordedAt),
        latestEventType: nullable(item.progress.latestEventType),
        source: nullable(item.progress.source),
        projectionState: nullable(item.progress.projectionState),
      },
      workSummary: {
        reasonCount: item.workSummary.reasonCount,
        openAttention: item.workSummary.openAttention,
      },
      attention: item.attention,
      attentionLabel: item.attentionLabel,
      ownerName: nullable(item.ownerName),
      primaryReason: normalizeReason(item.primaryReason),
      additionalReasons: item.additionalReasons.map(normalizeReason),
      destination: item.destination,
    })),
  };
}

export async function getControlTowerPage(
  attention?: ControlTowerAttention,
  cursor?: string,
  search?: string,
  pageSize = 25,
): Promise<ControlTowerPage> {
  const query = new URLSearchParams({ page_size: String(pageSize) });
  if (attention) query.set("attention", attention);
  if (search) query.set("search", search);
  if (cursor) query.set("cursor", cursor);
  const response = await request<ControlTowerApiResponse>(
    `/api/control-tower/shipments?${query.toString()}`,
  );
  return normalizeControlTowerPage(response);
}

export type ControlTowerFailure = "unauthorized" | "forbidden" | "unavailable" | "general";

export function classifyControlTowerFailure(error: unknown): ControlTowerFailure {
  if (!(error instanceof ApiError)) return "general";
  if (error.status === 401) return "unauthorized";
  if (error.status === 403) return "forbidden";
  if (error.status === 503 && error.code === "EVALUATION_UNAVAILABLE") return "unavailable";
  return "general";
}
