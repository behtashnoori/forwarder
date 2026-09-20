export interface ExistingRequestTransport {
  shipping_type?: string | null;
  transport_method?: string | null;
  international_transport_method?: string | null;
  domestic_transport_method?: string | null;
  transport_method_preference?: string | null;
}

export interface ExistingRouteTransportLeg {
  sequence_number?: number | null;
  transport_mode?: string | null;
}

const present = (value: string | null | undefined): string | null => {
  const trimmed = typeof value === "string" ? value.trim() : "";
  return trimmed || null;
};

/** Select the request's stored mode without deriving it from route or cargo data. */
export const getRequestTransportMethod = (
  request: ExistingRequestTransport | null | undefined,
): string | null => {
  if (!request) return null;

  if (request.shipping_type === "domestic") {
    return present(request.domestic_transport_method) ?? present(request.transport_method);
  }
  if (request.shipping_type === "international") {
    return present(request.international_transport_method) ?? present(request.transport_method);
  }

  const legacy = present(request.transport_method);
  if (legacy) return legacy;

  const domestic = present(request.domestic_transport_method);
  const international = present(request.international_transport_method);
  if (domestic && international && domestic.localeCompare(international, undefined, { sensitivity: "accent" }) === 0) {
    return domestic;
  }
  if (domestic && international) return null;
  return domestic ?? international;
};

/** Return actual leg modes in deterministic route order, preserving repetitions. */
export const getOrderedRouteTransportModes = (
  legs: readonly ExistingRouteTransportLeg[] | null | undefined,
): string[] => (legs ?? [])
  .map((leg, index) => ({
    mode: present(leg.transport_mode),
    sequence: Number.isFinite(leg.sequence_number) ? Number(leg.sequence_number) : index + 1,
    index,
  }))
  .filter((item): item is { mode: string; sequence: number; index: number } => item.mode !== null)
  .sort((left, right) => left.sequence - right.sequence || left.index - right.index)
  .map((item) => item.mode);

export const formatRouteTransportModes = (
  legs: readonly ExistingRouteTransportLeg[] | null | undefined,
  label: (mode: string) => string,
  direction: "ltr" | "rtl" = "rtl",
): string | null => {
  const modes = getOrderedRouteTransportModes(legs);
  if (!modes.length) return null;
  return modes.map(label).join(direction === "rtl" ? " ← " : " → ");
};
