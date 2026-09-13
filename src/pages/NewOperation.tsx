import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import OperationsNav from "@/components/OperationsNav";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ApiError,
  createDirectOperationalShipment,
  createQuoteOperationalShipment,
  createShipmentCargoItem,
  fetchCountries,
  fetchInternationalCities,
  fetchProvinces,
  getOperationalContext,
  getShipmentCargoOptions,
  listLogisticsPoints,
  listProjectLogisticsPoints,
  searchAcceptedOperationalQuotes,
  searchIranDestinations,
  searchOperationalCustomers,
  searchOperationalProjects,
  type Country,
  type InternationalCity,
  type IranDestinationOption,
  type OperationalCustomerSelector,
  type OperationalLocationRef,
  type OperationalProjectSelector,
  type OperationalQuoteSelector,
  type Province,
  type ShipmentCargoOptions,
  type LogisticsPointView,
} from "@/lib/api";
import { useI18n } from "@/i18n";

type Source = "direct" | "accepted_quote";
type Side = {
  kind: "domestic" | "international";
  locationMode: "facility" | "geography";
  countryId: string;
  provinceId: string;
  cityId: string;
  iranId: string;
  logisticsPointId: string;
};
type FieldError =
  | "customer"
  | "quote"
  | "origin"
  | "destination"
  | "departure"
  | "arrival"
  | "timeline"
  | "iranProvince"
  | "cargoQuantity"
  | "cargoUom";
const initialSide: Side = {
  kind: "domestic",
  locationMode: "facility",
  countryId: "",
  provinceId: "",
  cityId: "",
  iranId: "",
  logisticsPointId: "",
};
const backendMessages: Record<string, string> = {
  VALIDATION_FAILED: "Check the required fields.",
  INVALID_OPERATION_SOURCE: "The selected creation source is invalid.",
  COMMERCIAL_LINEAGE_NOT_ALLOWED:
    "Direct operations cannot include quote lineage.",
  INVALID_ROUTE_TIMELINE: "Planned arrival must be after departure.",
  FORBIDDEN_OPERATION: "You do not have permission to create this operation.",
  TENANT_SCOPE_VIOLATION:
    "Your active operational organization could not be resolved.",
  RESOURCE_NOT_FOUND: "A selected governed resource is no longer available.",
  IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD:
    "This submission changed after it started. Review and submit again.",
  OPERATIONAL_SHIPMENT_ALREADY_EXISTS: "This quote has already been converted.",
  SOURCE_CAPABILITY_NOT_APPLICABLE:
    "This capability does not apply to the selected source.",
  LOCATION_MAPPING_REQUIRED:
    "The selected location is not operationally eligible.",
  LOCATION_ANCESTRY_MISMATCH:
    "The selected location hierarchy is inconsistent.",
  PROJECT_CUSTOMER_MISMATCH:
    "The selected project does not belong to this customer.",
};
const errorText = (error: unknown) =>
  error instanceof ApiError
    ? backendMessages[error.code] || "The operation could not be created."
    : error instanceof Error
      ? error.message
      : "The operation could not be created.";

function RequiredLabel({
  children,
  required = false,
}: {
  children: React.ReactNode;
  required?: boolean;
}) {
  const { t } = useI18n();
  return (
    <>
      {children}
      {required && (
        <span className="ms-1 text-red-700" aria-hidden="true">
          *
        </span>
      )}
      {required && (
        <span className="sr-only"> ({t("operations.required")})</span>
      )}
    </>
  );
}

function FieldMessage({ id, message }: { id: string; message?: string }) {
  return message ? (
    <p id={id} role="alert" className="font-medium text-red-700">
      ⚠ {message}
    </p>
  ) : null;
}

function SearchSelect<T>({
  id,
  label,
  value,
  onChange,
  items,
  loading,
  error,
  onSearch,
  getId,
  render,
  required = false,
  fieldError,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  items: T[];
  loading: boolean;
  error: string;
  onSearch: (query: string) => void;
  getId: (item: T) => string;
  render: (item: T) => string;
  required?: boolean;
  fieldError?: string;
}) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const describedBy = fieldError ? `${id}-error` : undefined;
  return (
    <div className="min-w-0 space-y-2">
      <Label htmlFor={id}>
        <RequiredLabel required={required}>{label}</RequiredLabel>
      </Label>
      <div className="flex gap-2">
        <Input
          aria-label={`${label} ${t("operations.search")}`}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onSearch(query);
            }
          }}
        />
        <Button type="button" variant="outline" onClick={() => onSearch(query)}>
          {t("operations.search")}
        </Button>
      </div>
      {loading ? (
        <p role="status">{t("operations.loading")}</p>
      ) : error ? (
        <p role="alert" className="font-medium text-red-700">
          ⚠ {error}
        </p>
      ) : (
        <select
          id={id}
          aria-label={label}
          required={required}
          aria-required={required}
          aria-invalid={!!fieldError}
          aria-describedby={describedBy}
          className="min-h-11 w-full rounded-md border bg-white px-3"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">
            {items.length ? t("operations.select") : t("operations.noResults")}
          </option>
          {items.map((item) => (
            <option key={getId(item)} value={getId(item)}>
              {render(item)}
            </option>
          ))}
        </select>
      )}
      <FieldMessage id={`${id}-error`} message={fieldError} />
    </div>
  );
}

export default function NewOperation() {
  const { t, direction } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const requestedSource = params.get("source");
  const [permissions, setPermissions] = useState<string[]>([]);
  const [source, setSource] = useState<Source | "">(
    requestedSource === "direct" || requestedSource === "accepted_quote"
      ? requestedSource
      : "",
  );
  const [customers, setCustomers] = useState<OperationalCustomerSelector[]>([]);
  const [projects, setProjects] = useState<OperationalProjectSelector[]>([]);
  const [quotes, setQuotes] = useState<OperationalQuoteSelector[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [quoteId, setQuoteId] = useState(params.get("accepted_quote_id") || "");
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [originCities, setOriginCities] = useState<InternationalCity[]>([]);
  const [destinationCities, setDestinationCities] = useState<
    InternationalCity[]
  >([]);
  const [iran, setIran] = useState<IranDestinationOption[]>([]);
  const [logisticsPoints, setLogisticsPoints] = useState<LogisticsPointView[]>([]);
  const [preferredPointIds, setPreferredPointIds] = useState<Set<string>>(new Set());
  const [cargoOptions, setCargoOptions] = useState<ShipmentCargoOptions>({
    catalog: [],
    cargo_types: [],
    uoms: [],
  });
  const [cargoCatalogId, setCargoCatalogId] = useState("");
  const [cargoQuery, setCargoQuery] = useState("");
  const [cargoQuantity, setCargoQuantity] = useState("");
  const [cargoUomId, setCargoUomId] = useState("");
  const [origin, setOrigin] = useState<Side>(initialSide);
  const [destination, setDestination] = useState<Side>(initialSide);
  const [mode, setMode] = useState("road");
  const [departure, setDeparture] = useState("");
  const [arrival, setArrival] = useState("");
  const [loading, setLoading] = useState("");
  const [facilityLoading, setFacilityLoading] = useState(true);
  const [facilityError, setFacilityError] = useState("");
  const [selectorError, setSelectorError] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<FieldError, string>>
  >({});
  const [submitting, setSubmitting] = useState(false);
  const key = useRef(crypto.randomUUID());
  const payloadFingerprint = useRef("");
  const formRef = useRef<HTMLFormElement>(null);
  const canDirect = permissions.includes("operational_shipment.create_direct");
  const canQuote = permissions.some(
    (permission) =>
      permission === "operational_shipment.create_from_quote" ||
      permission === "operational_shipment.create",
  );
  const iranCountry = useMemo(
    () => countries.find((country) => country.code === "IR"),
    [countries],
  );
  const isIran = (side: Side) =>
    side.kind === "international" &&
    side.countryId === String(iranCountry?.id || "");
  const selectedIranDestination = iran.find(
    (option) =>
      `${option.identity.type}:${option.identity.id}` === destination.iranId,
  );
  const selectedCargo = cargoOptions.catalog.find(
    (option) => option.public_id === cargoCatalogId,
  );

  useEffect(() => {
    getOperationalContext()
      .then((response) => setPermissions(response.data.permissions))
      .catch((caught) => setError(errorText(caught)));
    Promise.all([fetchProvinces(), fetchCountries()])
      .then(([provinceRows, countryRows]) => {
        setProvinces(provinceRows);
        setCountries(countryRows);
      })
      .catch((caught) => setError(errorText(caught)));
    searchIranDestinations()
      .then((response) => setIran(response.data))
      .catch((caught) => setSelectorError(errorText(caught)));
    listLogisticsPoints({ active: "true", per_page: 100 })
      .then((response) => setLogisticsPoints(response.items.filter((point) => point.is_active)))
      .catch(() => setFacilityError("امکان دریافت نقاط عملیاتی وجود ندارد."))
      .finally(() => setFacilityLoading(false));
  }, []);
  useEffect(() => {
    getShipmentCargoOptions(projectId || undefined, cargoQuery)
      .then(setCargoOptions)
      .catch((caught) => setError(errorText(caught)));
  }, [projectId, cargoQuery]);
  const loadCustomers = async (query = "") => {
    setLoading("customer");
    setSelectorError("");
    try {
      setCustomers((await searchOperationalCustomers(query)).items);
    } catch (caught) {
      setSelectorError(errorText(caught));
    } finally {
      setLoading("");
    }
  };
  const loadProjects = async (query = "", selectedCustomerId = customerId) => {
    if (!selectedCustomerId) return;
    setLoading("project");
    setSelectorError("");
    try {
      setProjects(
        (await searchOperationalProjects(query, Number(selectedCustomerId)))
          .items,
      );
    } catch (caught) {
      setSelectorError(errorText(caught));
    } finally {
      setLoading("");
    }
  };
  const loadQuotes = async (query = "") => {
    setLoading("quote");
    setSelectorError("");
    try {
      const rows = (await searchAcceptedOperationalQuotes(query, 100)).items;
      setQuotes(rows);
      const linked = params.get("accepted_quote_id");
      if (linked && rows.some((row) => String(row.id) === linked))
        setQuoteId(linked);
      else if (linked) {
        setQuoteId("");
        setSelectorError(t("operations.linkedQuoteUnavailable"));
      }
    } catch (caught) {
      setSelectorError(errorText(caught));
    } finally {
      setLoading("");
    }
  };
  const loadIran = async (query = "") => {
    setLoading("iran");
    setSelectorError("");
    try {
      setIran((await searchIranDestinations(query)).data);
    } catch (caught) {
      setSelectorError(errorText(caught));
    } finally {
      setLoading("");
    }
  };
  useEffect(() => {
    if (canDirect) void loadCustomers();
    if (canQuote) void loadQuotes(params.get("request_ref") || "");
    // Selector loaders intentionally follow permission capability changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canDirect, canQuote]);
  useEffect(() => {
    if (!projectId) {
      setPreferredPointIds(new Set());
      return;
    }
    listProjectLogisticsPoints(projectId)
      .then((response) => setPreferredPointIds(new Set(response.items.filter((item) => item.is_active).map((item) => item.logistics_point.public_id))))
      .catch(() => setPreferredPointIds(new Set()));
  }, [projectId]);
  const rankedLogisticsPoints = useMemo(
    () => [...logisticsPoints].sort((left, right) => Number(preferredPointIds.has(right.public_id)) - Number(preferredPointIds.has(left.public_id))),
    [logisticsPoints, preferredPointIds],
  );

  const countryChange = async (
    sideName: "origin" | "destination",
    id: string,
  ) => {
    const setter = sideName === "origin" ? setOrigin : setDestination;
    setter((side) => ({
      ...side,
      countryId: id,
      provinceId: "",
      cityId: "",
      iranId: "",
    }));
    if (id && id !== String(iranCountry?.id)) {
      const rows = await fetchInternationalCities(Number(id));
      if (sideName === "origin") setOriginCities(rows);
      else setDestinationCities(rows);
    } else if (sideName === "destination") void loadIran();
  };
  const location = (side: Side): OperationalLocationRef | null => {
    if (side.locationMode === "facility" && side.logisticsPointId)
      return { source_type: "logistics_point", source_id: side.logisticsPointId };
    const selected = iran.find(
      (option) =>
        `${option.identity.type}:${option.identity.id}` === side.iranId,
    );
    if (selected)
      return {
        source_type:
          selected.identity.type === "port"
            ? "iran_port"
            : selected.identity.type === "customs"
              ? "customs_office"
              : selected.identity.type,
        source_id: selected.identity.id,
      };
    if (side.kind === "domestic" || (isIran(side) && side.provinceId))
      return side.provinceId
        ? { source_type: "province", source_id: Number(side.provinceId) }
        : null;
    if (isIran(side)) return null;
    return side.cityId
      ? { source_type: "international_city", source_id: Number(side.cityId) }
      : null;
  };
  const validate = () => {
    const next: Partial<Record<FieldError, string>> = {};
    if (source === "direct" && !customerId)
      next.customer = t("operations.validation.customer");
    if (source === "accepted_quote" && !quoteId)
      next.quote = t("operations.validation.quote");
    if (!location(origin))
      next.origin =
        isIran(origin) && !origin.provinceId
          ? t("operations.validation.iranProvince")
          : t("operations.validation.origin");
    if (!location(destination))
      next.destination = t("operations.validation.destination");
    if (!departure) next.departure = t("operations.validation.departure");
    if (!arrival) next.arrival = t("operations.validation.arrival");
    if (departure && arrival && new Date(arrival) <= new Date(departure))
      next.timeline = t("operations.validation.timeline");
    if (cargoCatalogId && (!cargoQuantity || Number(cargoQuantity) <= 0))
      next.cargoQuantity = "Enter a positive cargo quantity.";
    if (cargoCatalogId && !cargoUomId)
      next.cargoUom = "Select a unit of measure.";
    setFieldErrors(next);
    return next;
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    setError("");
    const invalid = validate();
    const first = Object.keys(invalid)[0];
    if (first) {
      requestAnimationFrame(() =>
        formRef.current
          ?.querySelector<HTMLElement>(`[data-field="${first}"], #${first}`)
          ?.focus(),
      );
      return;
    }
    const originRef = location(origin)!;
    const destinationRef = location(destination)!;
    const common = {
      origin: originRef,
      destination: destinationRef,
      transport_mode: mode,
      planned_departure: new Date(departure).toISOString(),
      planned_arrival: new Date(arrival).toISOString(),
      ...(projectId ? { project_public_id: projectId } : {}),
    };
    const payload =
      source === "direct"
        ? {
            ...common,
            source_type: "direct" as const,
            customer_id: Number(customerId),
          }
        : { ...common, accepted_quote_id: Number(quoteId) };
    const fingerprint = JSON.stringify(payload);
    if (
      payloadFingerprint.current &&
      payloadFingerprint.current !== fingerprint
    )
      key.current = crypto.randomUUID();
    payloadFingerprint.current = fingerprint;
    setSubmitting(true);
    try {
      const result =
        source === "direct"
          ? await createDirectOperationalShipment(
              payload as Parameters<typeof createDirectOperationalShipment>[0],
              key.current,
            )
          : await createQuoteOperationalShipment(
              payload as Parameters<typeof createQuoteOperationalShipment>[0],
              key.current,
            );
      if (selectedCargo) {
        await createShipmentCargoItem(result.data.public_id, {
          line_number: 1,
          catalog_item_public_id: selectedCargo.public_id,
          cargo_type_public_id: selectedCargo.cargo_type_public_id,
          quantity: cargoQuantity,
          uom_public_id: cargoUomId,
          ...(customerId ? { cargo_owner_customer_id: Number(customerId) } : {}),
        });
      }
      navigate(`/operations/shipments/${result.data.public_id}`);
    } catch (caught) {
      setError(errorText(caught));
      if (
        caught instanceof ApiError &&
        caught.code === "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"
      ) {
        key.current = crypto.randomUUID();
        payloadFingerprint.current = "";
      }
    } finally {
      setSubmitting(false);
    }
  };

  const sideFields = (
    sideName: "origin" | "destination",
    side: Side,
    setter: (side: Side) => void,
    cities: InternationalCity[],
  ) => {
    const label =
      sideName === "origin"
        ? t("operations.origin")
        : t("operations.destination");
    const sideError = fieldErrors[sideName];
    return (
      <fieldset className="min-w-0 space-y-3 rounded border p-3">
        <legend className="font-semibold">
          <RequiredLabel required>{label}</RequiredLabel>
        </legend>
        <Label htmlFor={`${sideName}-route-type`} className="sr-only">
          {label} {t("operations.routeType")}
        </Label>
        <select
          id={`${sideName}-route-type`}
          aria-label={`${label} ${t("operations.routeType")}`}
          className="min-h-11 w-full rounded border px-3"
          value={side.kind}
          onChange={(event) =>
            setter({ ...initialSide, kind: event.target.value as Side["kind"] })
          }
        >
          <option value="domestic">{t("operations.domesticIran")}</option>
          <option value="international">{t("operations.international")}</option>
        </select>
        <Label htmlFor={`${sideName}-location-mode`}>روش تعیین مکان</Label>
        <select
          id={`${sideName}-location-mode`}
          aria-label={`${label} روش تعیین مکان`}
          className="min-h-11 w-full rounded border px-3"
          value={side.locationMode}
          onChange={(event) => setter({ ...initialSide, kind: side.kind, locationMode: event.target.value as Side["locationMode"] })}
        >
          <option value="facility">نقطه عملیاتی</option>
          <option value="geography">فقط موقعیت جغرافیایی</option>
        </select>
        {side.locationMode === "facility" ? <>
        <Label htmlFor={`${sideName}-logistics-point`}>نقطه عملیاتی</Label>
        {facilityLoading ? <p role="status">در حال دریافت نقاط عملیاتی…</p> : null}
        {facilityError ? <p role="alert">{facilityError}</p> : null}
        <select
          id={`${sideName}-logistics-point`}
          aria-label={`${label} operational facility`}
          className="min-h-11 w-full rounded border px-3"
          value={side.logisticsPointId}
          disabled={facilityLoading || Boolean(facilityError)}
          onChange={(event) => setter({ ...side, logisticsPointId: event.target.value })}
        >
          <option value="">{facilityLoading ? "در حال دریافت نقاط عملیاتی…" : facilityError ? "دریافت نقاط عملیاتی ناموفق بود." : rankedLogisticsPoints.length ? t("operations.select") : "نقطه عملیاتی فعالی برای این سازمان ثبت نشده است."}</option>
          {rankedLogisticsPoints.map((point) => (
            <option key={point.public_id} value={point.public_id}>
              {preferredPointIds.has(point.public_id) ? "★ " : ""}{point.fa_name} — {point.point_type.fa_name}
            </option>
          ))}
        </select>
        {side.logisticsPointId ? (
          <p role="status">موقعیت جغرافیایی نقطه عملیاتی از داده مرجع سازمان تعیین می‌شود.</p>
        ) : null}
        </> : (
        <>{side.kind === "domestic" && sideName === "destination" ? (
          <SearchSelect
            id="destination"
            label={t("operations.iranDestination")}
            value={side.iranId}
            onChange={(value) => setter({ ...side, iranId: value })}
            items={iran}
            loading={loading === "iran"}
            error={selectorError}
            onSearch={loadIran}
            getId={(option) =>
              `${option.identity.type}:${option.identity.id}`
            }
            render={(option) => option.label}
            required
            fieldError={sideError}
          />
        ) : side.kind === "domestic" ? (
          <>
            <Label htmlFor={`${sideName}-province`}>
              <RequiredLabel required>{t("operations.province")}</RequiredLabel>
            </Label>
            <select
              id={`${sideName}-province`}
              aria-label={`${label} ${t("operations.province")}`}
              data-field={sideName}
              required
              aria-required="true"
              aria-invalid={!!sideError}
              aria-describedby={sideError ? `${sideName}-error` : undefined}
              className="min-h-11 w-full rounded border px-3"
              value={side.provinceId}
              onChange={(event) =>
                setter({ ...side, provinceId: event.target.value })
              }
            >
              <option value="">{t("operations.select")}</option>
              {provinces.map((province) => (
                <option key={province.id} value={province.id}>
                  {province.name}
                </option>
              ))}
            </select>
            <FieldMessage id={`${sideName}-error`} message={sideError} />
          </>
        ) : (
          <>
            <Label htmlFor={`${sideName}-country`}>
              <RequiredLabel required>{t("operations.country")}</RequiredLabel>
            </Label>
            <select
              id={`${sideName}-country`}
              aria-label={`${label} ${t("operations.country")}`}
              required
              aria-required="true"
              className="min-h-11 w-full rounded border px-3"
              value={side.countryId}
              onChange={(event) =>
                void countryChange(sideName, event.target.value)
              }
            >
              <option value="">{t("operations.select")}</option>
              {countries.map((country) => (
                <option key={country.id} value={country.id}>
                  {country.name_en || country.name}
                </option>
              ))}
            </select>
            {isIran(side) ? (
              sideName === "origin" ? (
                <>
                  <Label htmlFor="iranProvince">
                    <RequiredLabel required>
                      {t("operations.iranOriginProvince")}
                    </RequiredLabel>
                  </Label>
                  <select
                    id="iranProvince"
                    aria-label={t("operations.iranOriginProvince")}
                    data-field="origin"
                    required
                    aria-required="true"
                    aria-invalid={!!sideError}
                    aria-describedby={sideError ? "origin-error" : undefined}
                    className="min-h-11 w-full rounded border px-3"
                    value={side.provinceId}
                    onChange={(event) =>
                      setter({ ...side, provinceId: event.target.value })
                    }
                  >
                    <option value="">{t("operations.select")}</option>
                    {provinces.map((province) => (
                      <option key={province.id} value={province.id}>
                        {province.name}
                      </option>
                    ))}
                  </select>
                  <FieldMessage id="origin-error" message={sideError} />
                  {side.provinceId && (
                    <p role="status">
                      {t("operations.derivedProvince")}:{" "}
                      {
                        provinces.find(
                          (province) => String(province.id) === side.provinceId,
                        )?.name
                      }
                    </p>
                  )}
                </>
              ) : (
                <SearchSelect
                  id="destination"
                  label={t("operations.iranDestination")}
                  value={side.iranId}
                  onChange={(value) => setter({ ...side, iranId: value })}
                  items={iran}
                  loading={loading === "iran"}
                  error={selectorError}
                  onSearch={loadIran}
                  getId={(option) =>
                    `${option.identity.type}:${option.identity.id}`
                  }
                  render={(option) => option.label}
                  required
                  fieldError={sideError}
                />
              )
            ) : (
              <>
                <Label htmlFor={`${sideName}-city`}>
                  <RequiredLabel required>
                    {t("operations.internationalCity")}
                  </RequiredLabel>
                </Label>
                <select
                  id={`${sideName}-city`}
                  aria-label={`${label} ${t("operations.internationalCity")}`}
                  data-field={sideName}
                  required
                  aria-required="true"
                  aria-invalid={!!sideError}
                  aria-describedby={sideError ? `${sideName}-error` : undefined}
                  className="min-h-11 w-full rounded border px-3"
                  value={side.cityId}
                  onChange={(event) =>
                    setter({ ...side, cityId: event.target.value })
                  }
                >
                  <option value="">{t("operations.select")}</option>
                  {cities.map((city) => (
                    <option key={city.id} value={city.id}>
                      {city.name_en || city.name}
                    </option>
                  ))}
                </select>
                <FieldMessage id={`${sideName}-error`} message={sideError} />
              </>
            )}
          </>
        )}</>
        )}
      </fieldset>
    );
  };

  if (
    !source ||
    (permissions.length > 0 &&
      ((source === "direct" && !canDirect) ||
        (source === "accepted_quote" && !canQuote)))
  )
    return (
      <main className="min-h-screen bg-slate-50 p-4" dir={direction}>
        <div className="mx-auto max-w-4xl space-y-5">
          <OperationsNav />
          <h1 className="text-2xl font-bold">{t("operations.newOperation")}</h1>
          {error && <p role="alert">⚠ {error}</p>}
          <div className="grid gap-4 sm:grid-cols-2">
            {canDirect && (
              <Button
                className="h-auto min-h-28 flex-col"
                onClick={() => setSource("direct")}
              >
                <strong>{t("operations.source.direct")}</strong>
                <span>{t("operations.source.directHelp")}</span>
              </Button>
            )}
            {canQuote && (
              <Button
                className="h-auto min-h-28 flex-col"
                variant="secondary"
                onClick={() => setSource("accepted_quote")}
              >
                <strong>{t("operations.source.quote")}</strong>
                <span>{t("operations.source.quoteHelp")}</span>
              </Button>
            )}
          </div>
          {!canDirect && !canQuote && !error && (
            <p role="alert">⚠ {t("operations.noCreatePermission")}</p>
          )}
        </div>
      </main>
    );
  return (
    <main
      className="min-h-screen overflow-x-hidden bg-slate-50 p-3 sm:p-5"
      dir={direction}
    >
      <form
        ref={formRef}
        noValidate
        onSubmit={submit}
        className="mx-auto max-w-5xl space-y-5"
      >
        <OperationsNav />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-2xl font-bold">
            {t("operations.newOperation")} ·{" "}
            {source === "direct"
              ? t("operations.source.direct")
              : t("operations.source.quote")}
          </h1>
          <Button type="button" variant="outline" onClick={() => setSource("")}>
            {t("operations.changeSource")}
          </Button>
        </div>
        {source === "direct" ? (
          <Card>
            <CardHeader>
              <CardTitle>{t("operations.customerProject")}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <SearchSelect
                id="customer"
                label={t("operations.customer")}
                value={customerId}
                onChange={(value) => {
                  setCustomerId(value);
                  setProjectId("");
                  setProjects([]);
                  void loadProjects("", value);
                }}
                items={customers}
                loading={loading === "customer"}
                error={selectorError}
                onSearch={loadCustomers}
                getId={(customer) => String(customer.id)}
                render={(customer) => customer.label}
                required
                fieldError={fieldErrors.customer}
              />
              <SearchSelect
                id="project"
                label={t("operations.projectOptional")}
                value={projectId}
                onChange={setProjectId}
                items={projects}
                loading={loading === "project"}
                error={selectorError}
                onSearch={loadProjects}
                getId={(project) => project.public_id}
                render={(project) =>
                  `${project.project_code} · ${project.lifecycle_status}`
                }
              />
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>{t("operations.eligibleQuote")}</CardTitle>
            </CardHeader>
            <CardContent>
              <SearchSelect
                id="quote"
                label={t("operations.acceptedQuote")}
                value={quoteId}
                onChange={setQuoteId}
                items={quotes}
                loading={loading === "quote"}
                error={selectorError}
                onSearch={loadQuotes}
                getId={(quote) => String(quote.id)}
                render={(quote) =>
                  `${quote.request_public_id} · ${quote.customer_label} · ${quote.route_label || "—"} · ${quote.quote_label}`
                }
                required
                fieldError={fieldErrors.quote}
              />
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader>
            <CardTitle>{t("operations.routeSchedule")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid min-w-0 gap-4 md:grid-cols-2">
              {sideFields("origin", origin, setOrigin, originCities)}
              {sideFields(
                "destination",
                destination,
                setDestination,
                destinationCities,
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <Label htmlFor="transport-mode">
                  <RequiredLabel required>
                    {t("operations.transportMode")}
                  </RequiredLabel>
                </Label>
                <select
                  id="transport-mode"
                  aria-label={t("operations.transportMode")}
                  required
                  aria-required="true"
                  className="min-h-11 w-full rounded border px-3"
                  value={mode}
                  onChange={(event) => setMode(event.target.value)}
                >
                  {[
                    "road",
                    "rail",
                    "sea",
                    "air",
                    "multimodal_transfer",
                    "customs_handling",
                  ].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="departure">
                  <RequiredLabel required>
                    {t("operations.plannedDeparture")}
                  </RequiredLabel>
                </Label>
                <Input
                  id="departure"
                  aria-label={t("operations.plannedDeparture")}
                  data-field="departure"
                  required
                  aria-required="true"
                  aria-invalid={
                    !!fieldErrors.departure || !!fieldErrors.timeline
                  }
                  aria-describedby={
                    fieldErrors.departure
                      ? "departure-error"
                      : fieldErrors.timeline
                        ? "timeline-error"
                        : undefined
                  }
                  type="datetime-local"
                  value={departure}
                  onChange={(event) => setDeparture(event.target.value)}
                />
                <FieldMessage
                  id="departure-error"
                  message={fieldErrors.departure}
                />
              </div>
              <div>
                <Label htmlFor="arrival">
                  <RequiredLabel required>
                    {t("operations.plannedArrival")}
                  </RequiredLabel>
                </Label>
                <Input
                  id="arrival"
                  aria-label={t("operations.plannedArrival")}
                  data-field="arrival"
                  required
                  aria-required="true"
                  aria-invalid={!!fieldErrors.arrival || !!fieldErrors.timeline}
                  aria-describedby={
                    fieldErrors.arrival
                      ? "arrival-error"
                      : fieldErrors.timeline
                        ? "timeline-error"
                        : undefined
                  }
                  type="datetime-local"
                  value={arrival}
                  onChange={(event) => setArrival(event.target.value)}
                />
                <FieldMessage
                  id="arrival-error"
                  message={fieldErrors.arrival}
                />
                <FieldMessage
                  id="timeline-error"
                  message={fieldErrors.timeline}
                />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>کالای محموله / Shipment cargo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              کاتالوگ توسط مدیر سازمان نگهداری می‌شود؛ کالای فعال را برای این محموله انتخاب کنید.
              / Organization Admin maintains the catalog; select an active item for this shipment.
            </p>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="cargo-catalog">Catalog item (optional)</Label>
                <Input
                  aria-label="Search commodities"
                  placeholder="Search name, alias, codes, brand or model"
                  value={cargoQuery}
                  onChange={(event) => setCargoQuery(event.target.value)}
                />
                <select
                  id="cargo-catalog"
                  aria-label="Catalog item"
                  className="min-h-11 w-full rounded border px-3"
                  value={cargoCatalogId}
                  onChange={(event) => {
                    const catalogId = event.target.value;
                    const item = cargoOptions.catalog.find(
                      (option) => option.public_id === catalogId,
                    );
                    setCargoCatalogId(catalogId);
                    setCargoUomId(item?.default_uom_public_id || "");
                  }}
                >
                  <option value="">Manual cargo / no catalog item in this step</option>
                  {cargoOptions.catalog.some((option) => option.preferred) && <optgroup label="Preferred for this project">
                    {cargoOptions.catalog.filter((option) => option.preferred).map((option) => (
                      <option key={option.public_id} value={option.public_id}>★ {option.code} — {option.name}</option>
                    ))}
                  </optgroup>}
                  <optgroup label="Other organization commodities">
                    {cargoOptions.catalog.filter((option) => !option.preferred).map((option) => (
                      <option key={option.public_id} value={option.public_id}>{option.code} — {option.name}</option>
                    ))}
                  </optgroup>
                </select>
                <p className="text-xs text-muted-foreground">Project preferences change ranking only. Manual cargo can also be added after creation.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="cargo-quantity">Quantity</Label>
                <Input
                  id="cargo-quantity"
                  data-field="cargoQuantity"
                  aria-label="Cargo quantity"
                  type="number"
                  min="0.000001"
                  step="any"
                  disabled={!cargoCatalogId}
                  value={cargoQuantity}
                  onChange={(event) => setCargoQuantity(event.target.value)}
                  aria-invalid={!!fieldErrors.cargoQuantity}
                />
                <FieldMessage id="cargo-quantity-error" message={fieldErrors.cargoQuantity} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cargo-uom">Unit of measure</Label>
                <select
                  id="cargo-uom"
                  data-field="cargoUom"
                  aria-label="Unit of measure"
                  className="min-h-11 w-full rounded border px-3"
                  disabled={!cargoCatalogId}
                  value={cargoUomId}
                  onChange={(event) => setCargoUomId(event.target.value)}
                  aria-invalid={!!fieldErrors.cargoUom}
                >
                  <option value="">Select…</option>
                  {cargoOptions.uoms.map((option) => (
                    <option key={option.public_id} value={option.public_id}>
                      {option.name}{option.symbol ? ` (${option.symbol})` : ""}
                    </option>
                  ))}
                </select>
                <FieldMessage id="cargo-uom-error" message={fieldErrors.cargoUom} />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("operations.review")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p>
              {t("operations.source")}:{" "}
              {source === "direct"
                ? t("operations.source.direct")
                : t("operations.source.quote")}
            </p>
            {source === "direct" && (
              <p>
                {t("operations.customer")}:{" "}
                {customers.find(
                  (customer) => String(customer.id) === customerId,
                )?.label || "—"}
              </p>
            )}
            <p>
              {t("operations.iranOriginProvince")}:{" "}
              {isIran(origin)
                ? provinces.find(
                    (province) => String(province.id) === origin.provinceId,
                  )?.name || t("operations.required")
                : t("operations.notApplicable")}
            </p>
            {selectedIranDestination && (
              <p role="status">
                {t("operations.derivedProvince")}:{" "}
                {selectedIranDestination.province?.name || selectedIranDestination.secondary_label}
              </p>
            )}
            {selectedCargo && (
              <p role="status">
                Cargo: {selectedCargo.code} — {selectedCargo.name} · {cargoQuantity || "—"}
              </p>
            )}
          </CardContent>
        </Card>
        {error && (
          <p
            role="alert"
            className="rounded border border-red-300 bg-red-50 p-3 font-medium text-red-700"
          >
            ⚠ {error}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? t("operations.creating") : t("operations.create")}
          </Button>
          <Button asChild type="button" variant="outline">
            <Link to="/operations/shipments">{t("operations.cancel")}</Link>
          </Button>
        </div>
      </form>
    </main>
  );
}
