import LocalizedDateTimeInput from "@/components/LocalizedDateTimeInput";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import OperationsNav from "@/components/OperationsNav";
import CanonicalLocationPicker, { type CanonicalEndpointRef } from "@/components/CanonicalLocationPicker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ApiError,
  createDirectOperationalShipment,
  createQuoteOperationalShipment,
  getOperationalContext,
  getShipmentCargoOptions,
  listLogisticsPoints,
  listProjectLogisticsPoints,
  searchAcceptedOperationalQuotes,
  searchOperationalCustomers,
  searchOperationalProjects,
  type OperationalCustomerSelector,
  type OperationalLocationRef,
  type OperationalProjectSelector,
  type OperationalQuoteSelector,
  type ShipmentCargoOptions,
  type LogisticsPointView,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";
import { formatUnitSymbol } from "@/lib/formatQuantity";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

type Source = "direct" | "accepted_quote";
type Side = {
  locationMode: "facility" | "geography";
  logisticsPointId: string;
  canonical: CanonicalEndpointRef | null;
  adding: boolean;
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
  | "cargoSource"
  | "cargoQuantity"
  | "cargoUom";
const initialSide: Side = {locationMode:"facility",logisticsPointId:"",canonical:null,adding:false};
const backendMessages: Record<string, string> = {
  VALIDATION_FAILED: "فیلدهای الزامی را بررسی کنید.",
  INVALID_OPERATION_SOURCE: "منبع انتخاب‌شده برای ایجاد عملیات معتبر نیست.",
  COMMERCIAL_LINEAGE_NOT_ALLOWED:
    "عملیات مستقیم نمی‌تواند سابقهٔ قیمت داشته باشد.",
  INVALID_ROUTE_TIMELINE: "زمان برنامه‌ریزی‌شدهٔ رسیدن باید پس از حرکت باشد.",
  FORBIDDEN_OPERATION: "مجوز ایجاد این عملیات را ندارید.",
  TENANT_SCOPE_VIOLATION: "سازمان عملیاتی فعال شما قابل تشخیص نیست.",
  RESOURCE_NOT_FOUND: "یکی از گزینه‌های حاکم‌شدهٔ انتخابی دیگر در دسترس نیست.",
  IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD:
    "این درخواست هنگام ارسال تغییر کرده است؛ آن را بررسی و دوباره ارسال کنید.",
  OPERATIONAL_SHIPMENT_ALREADY_EXISTS:
    "این قیمت قبلاً به پروندهٔ حمل تبدیل شده است.",
  SOURCE_CAPABILITY_NOT_APPLICABLE:
    "این قابلیت برای منبع انتخاب‌شده قابل اعمال نیست.",
  LOCATION_MAPPING_REQUIRED: "موقعیت انتخاب‌شده برای عملیات مجاز نیست.",
  LOCATION_ANCESTRY_MISMATCH: "ساختار موقعیت انتخاب‌شده ناسازگار است.",
  PROJECT_CUSTOMER_MISMATCH: "پروژهٔ انتخاب‌شده متعلق به این مشتری نیست.",
};
const errorText = (error: unknown) =>
  error instanceof ApiError
    ? backendMessages[error.code] || "ایجاد عملیات ممکن نشد."
    : error instanceof Error
      ? error.message
      : "ایجاد عملیات ممکن نشد.";

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
  const { t, direction, businessLabel, transportLabel } = useI18n();
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
  const [logisticsPoints, setLogisticsPoints] = useState<LogisticsPointView[]>(
    [],
  );
  const [preferredPointIds, setPreferredPointIds] = useState<Set<string>>(
    new Set(),
  );
  const [cargoOptions, setCargoOptions] = useState<ShipmentCargoOptions>({
    catalog: [],
    cargo_types: [],
    uoms: [],
  });
  const [cargoCatalogId, setCargoCatalogId] = useState("");
  const [requestCargoId, setRequestCargoId] = useState("");
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
  const selectedCargo = cargoOptions.catalog.find(
    (option) => option.public_id === cargoCatalogId,
  );
  const selectedQuote = quotes.find((option) => String(option.id) === quoteId);
  const quoteCargoItems = selectedQuote?.cargo_items || [];
  const selectedRequestCargo = quoteCargoItems.find(
    (option) => option.public_id === requestCargoId,
  );
  const selectableCatalog = cargoOptions.catalog.filter(
    (option) =>
      source !== "accepted_quote" ||
      !selectedRequestCargo?.cargo_type_public_id ||
      option.cargo_type_public_id === selectedRequestCargo.cargo_type_public_id,
  );

  useEffect(() => {
    getOperationalContext()
      .then((response) => setPermissions(response.data.permissions))
      .catch((caught) => setError(errorText(caught)));
    listLogisticsPoints({ active: "true", per_page: 100 })
      .then((response) =>
        setLogisticsPoints(response.items.filter((point) => point.is_active)),
      )
      .catch(() => setFacilityError("امکان دریافت نقاط عملیاتی وجود ندارد."))
      .finally(() => setFacilityLoading(false));
  }, []);
  useEffect(() => {
    getShipmentCargoOptions(projectId || undefined, cargoQuery)
      .then(setCargoOptions)
      .catch((caught) => setError(errorText(caught)));
  }, [projectId, cargoQuery]);
  useEffect(() => {
    if (source !== "accepted_quote") return;
    const items = selectedQuote?.cargo_items || [];
    setRequestCargoId((current) =>
      items.some((item) => item.public_id === current)
        ? current
        : items.length === 1
          ? items[0].public_id
          : "",
    );
  }, [source, selectedQuote?.id, selectedQuote?.cargo_items]);
  useEffect(() => {
    if (source !== "accepted_quote") return;
    setCargoQuantity(selectedRequestCargo?.quantity || "");
    setCargoUomId(selectedRequestCargo?.uom_public_id || "");
    setCargoCatalogId("");
  }, [source, selectedRequestCargo?.public_id, selectedRequestCargo?.quantity, selectedRequestCargo?.uom_public_id]);
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
      .then((response) =>
        setPreferredPointIds(
          new Set(
            response.items
              .filter((item) => item.is_active)
              .map((item) => item.logistics_point.public_id),
          ),
        ),
      )
      .catch(() => setPreferredPointIds(new Set()));
  }, [projectId]);
  const rankedLogisticsPoints = useMemo(
    () =>
      [...logisticsPoints].sort(
        (left, right) =>
          Number(preferredPointIds.has(right.public_id)) -
          Number(preferredPointIds.has(left.public_id)),
      ),
    [logisticsPoints, preferredPointIds],
  );

  const location = (side: Side): OperationalLocationRef | null =>
    (side.canonical ? {source_type:side.canonical.source_type,source_id:side.canonical.source_id} : null) || (side.locationMode === "facility" && side.logisticsPointId
      ? {source_type:"logistics_point",source_id:side.logisticsPointId} : null);
  const sideLabel = (side: Side) => {
    if (side.locationMode === "facility" && side.logisticsPointId)
      return logisticsPoints.find(point => point.public_id === side.logisticsPointId)?.fa_name || "مکان سازمان انتخاب‌شده";
    return side.canonical?.display_label || ({
      province: "استان انتخاب‌شده", city: "شهر انتخاب‌شده", international_city: "نقطه بین‌المللی انتخاب‌شده",
      iran_port: "بندر انتخاب‌شده", customs_office: "گمرک انتخاب‌شده", country: "کشور انتخاب‌شده",
      logistics_point: "مکان سازمان انتخاب‌شده",
    }[side.canonical?.source_type || "city"]);
  };
  const validate = () => {
    const next: Partial<Record<FieldError, string>> = {};
    if (source === "direct" && !customerId)
      next.customer = t("operations.validation.customer");
    if (source === "accepted_quote" && !quoteId)
      next.quote = t("operations.validation.quote");
    if (
      source === "accepted_quote" &&
      selectedQuote &&
      quoteCargoItems.length > 0 &&
      !selectedRequestCargo
    )
      next.cargoSource = "قلم کالای درخواست را انتخاب کنید.";
    if (selectedRequestCargo && !selectedRequestCargo.operationally_ready)
      next.cargoSource =
        "این قلم درخواست هنوز مقدار، واحد و نوع کالای کامل برای برنامه‌ریزی عملیاتی ندارد.";
    if (!location(origin))
      next.origin = t("operations.validation.origin");
    if (!location(destination))
      next.destination = t("operations.validation.destination");
    if (!localDateTimeInputToUtc(departure)) next.departure = t("operations.validation.departure");
    if (!localDateTimeInputToUtc(arrival)) next.arrival = t("operations.validation.arrival");
    if (departure && arrival && new Date(arrival) <= new Date(departure))
      next.timeline = t("operations.validation.timeline");
    if (
      (selectedCargo || selectedRequestCargo) &&
      (!cargoQuantity || Number(cargoQuantity) <= 0)
    )
      next.cargoQuantity = "مقدار مثبت کالا را وارد کنید.";
    if ((selectedCargo || selectedRequestCargo) && !cargoUomId)
      next.cargoUom = "واحد اندازه‌گیری را انتخاب کنید.";
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
    const cargoItems =
      source === "accepted_quote" && selectedRequestCargo
        ? [
            {
              source_request_cargo_item_public_id:
                selectedRequestCargo.public_id,
              planned_quantity: cargoQuantity,
              ...(selectedCargo
                ? { catalog_item_public_id: selectedCargo.public_id }
                : {}),
            },
          ]
        : source === "direct" && selectedCargo
          ? [
              {
                catalog_item_public_id: selectedCargo.public_id,
                cargo_type_public_id: selectedCargo.cargo_type_public_id,
                quantity: cargoQuantity,
                planned_quantity: cargoQuantity,
                uom_public_id: cargoUomId,
              },
            ]
          : [];
    const payload =
      source === "direct"
        ? {
            ...common,
            source_type: "direct" as const,
            customer_id: Number(customerId),
            ...(cargoItems.length ? { cargo_items: cargoItems } : {}),
          }
        : {
            ...common,
            accepted_quote_id: Number(quoteId),
            ...(cargoItems.length ? { cargo_items: cargoItems } : {}),
          };
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

  const sideFields = (sideName:"origin"|"destination",side:Side,setter:(side:Side)=>void) => {
    const label=t(`operations.${sideName}`);
    return <fieldset className="min-w-0 space-y-3 rounded border p-3">
      <legend className="font-semibold"><RequiredLabel required>{label}</RequiredLabel></legend>
      <label>روش تعیین مکان<select aria-label={`${label} روش تعیین مکان`} className="min-h-11 w-full rounded border px-3" value={side.locationMode}
        onChange={e=>setter({...initialSide,locationMode:e.target.value as Side["locationMode"]})}>
        <option value="facility">مکان سازمان</option><option value="geography">نقطه جغرافیایی معتبر</option>
      </select></label>
      {side.locationMode==="facility"&&<>
        {facilityLoading&&<p role="status">در حال دریافت مکان‌های سازمان…</p>}{facilityError&&<p role="alert">{facilityError}</p>}
        <label>مکان سازمان<select aria-label={`${label} operational facility`} className="min-h-11 w-full rounded border px-3" value={side.logisticsPointId} disabled={facilityLoading||!!facilityError}
          onChange={e=>setter({...side,logisticsPointId:e.target.value,canonical:null})}>
          <option value="">{facilityLoading?t("operations.loading"):facilityError?"دریافت نقاط عملیاتی ناموفق بود.":rankedLogisticsPoints.length?t("operations.select"):"مکان سازمانی ثبت نشده است"}</option>
          {rankedLogisticsPoints.map(point=><option key={point.public_id} value={point.public_id}>{preferredPointIds.has(point.public_id)?"★ ":""}{point.point_type?.fa_name||"مکان سازمان"} — {point.fa_name}{point.governance_state==="PENDING_REVIEW"?" · در انتظار بررسی":""}</option>)}
        </select></label>
        {side.logisticsPointId&&<p role="status">موقعیت جغرافیایی نقطه عملیاتی از داده مرجع سازمان تعیین می‌شود.</p>}
        <Button type="button" variant="outline" onClick={()=>setter({...side,adding:!side.adding})}>{side.adding?"بستن فرم مکان":"افزودن مکان جدید"}</Button>
      </>}
      {(side.locationMode==="geography"||side.adding)&&<CanonicalLocationPicker key={`${sideName}-${side.locationMode}`} label={label} value={side.canonical} allowAdmin1={side.locationMode==="geography"} allowPhysicalPoints={side.locationMode==="geography"}
        onChange={ref=>setter({...side,canonical:side.locationMode==="facility"&&ref?.source_type!=="logistics_point"?null:ref,logisticsPointId:ref?.source_type==="logistics_point"?String(ref.source_id):""})}
        onCreated={point=>setLogisticsPoints(rows=>[point,...rows.filter(row=>row.public_id!==point.public_id)])}/>}
      <FieldMessage id={`${sideName}-error`} message={fieldErrors[sideName]}/>
    </fieldset>;
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
                  `${project.project_code} · ${businessLabel(project.lifecycle_status)}`
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
                onChange={(value) => {
                  setQuoteId(value);
                  setRequestCargoId("");
                  setCargoCatalogId("");
                }}
                items={quotes}
                loading={loading === "quote"}
                error={selectorError}
                onSearch={loadQuotes}
                getId={(quote) => String(quote.id)}
                render={(quote) =>
                  `${direction === "rtl" ? "درخواست پذیرفته‌شده" : "Accepted request"} · ${quote.customer_label} · ${quote.route_label || "—"} · ${quote.quote_label}`
                }
                required
                fieldError={fieldErrors.quote}
              />
              {selectedQuote?.requires_location_resolution && (
                <p role="alert" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
                  {selectedQuote.location_resolution_message || "محل اعلام‌شده مشتری باید پیش از برنامه‌ریزی به نقاط عملیاتی دقیق متصل شود."}
                </p>
              )}
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader>
            <CardTitle>{t("operations.routeSchedule")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid min-w-0 gap-4 md:grid-cols-2">
              {sideFields("origin", origin, setOrigin)}
              {sideFields(
                "destination",
                destination,
                setDestination,
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
                    <option key={value} value={value}>{transportLabel(value)}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="departure">
                  <RequiredLabel required>
                    {t("operations.plannedDeparture")}
                  </RequiredLabel>
                </Label>
                <LocalizedDateTimeInput
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
                <LocalizedDateTimeInput
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
            <CardTitle>
              {direction === "rtl" ? "کالای محموله" : "Shipment cargo"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {direction === "rtl"
                ? "فهرست کالا توسط مدیر سازمان نگهداری می‌شود؛ کالای فعال را برای این محموله انتخاب کنید."
                : "The Organization Admin maintains the catalog; select an active item for this shipment."}
            </p>
            {source === "accepted_quote" && selectedQuote ? (
              <div className="space-y-2">
                <Label htmlFor="request-cargo">
                  کالای منبع در درخواست مشتری
                </Label>
                {quoteCargoItems.length ? (
                  <select
                    id="request-cargo"
                    data-field="cargoSource"
                    aria-label="کالای منبع در درخواست مشتری"
                    aria-invalid={!!fieldErrors.cargoSource}
                    className="min-h-11 w-full rounded border px-3"
                    value={requestCargoId}
                    onChange={(event) => setRequestCargoId(event.target.value)}
                  >
                    <option value="">انتخاب قلم درخواست</option>
                    {quoteCargoItems.map((item) => (
                      <option
                        key={item.public_id}
                        value={item.public_id}
                        disabled={!item.operationally_ready}
                      >
                        {item.position}.{" "}
                        {item.description || item.cargo_type_name || "کالا"}
                        {item.quantity
                          ? ` — ${Number(item.quantity).toLocaleString("fa-IR")} ${item.uom_name || item.uom_symbol || ""}`
                          : " — اطلاعات عملیاتی ناقص"}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="rounded bg-slate-50 p-3 text-sm">
                    این درخواست قلم کالای ثبت‌شده ندارد؛ ایجاد محموله بدون قلم
                    کالا ادامه می‌یابد.
                  </p>
                )}
                <FieldMessage
                  id="cargo-source-error"
                  message={fieldErrors.cargoSource}
                />
                {selectedRequestCargo ? (
                  <p className="text-sm text-slate-700">
                    درخواست‌شده:{" "}
                    {Number(selectedRequestCargo.quantity).toLocaleString(
                      "fa-IR",
                    )}{" "}
                    {selectedRequestCargo.uom_name ||
                      formatUnitSymbol(selectedRequestCargo.uom_symbol || "", direction === "rtl" ? "fa-IR" : "en-US")}{" "}
                    · نوع کالا:{" "}
                    {selectedRequestCargo.cargo_type_name || "نامشخص"}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="cargo-catalog">
                  {direction === "rtl"
                    ? "کالای استاندارد (اختیاری)"
                    : "Catalog item (optional)"}
                </Label>
                <Input
                  aria-label={
                    direction === "rtl" ? "جست‌وجوی کالا" : "Search commodities"
                  }
                  placeholder={
                    direction === "rtl"
                      ? "جست‌وجوی نام، نام جایگزین، کد، برند یا مدل"
                      : "Search name, alias, codes, brand or model"
                  }
                  value={cargoQuery}
                  onChange={(event) => setCargoQuery(event.target.value)}
                />
                <select
                  id="cargo-catalog"
                  aria-label={
                    direction === "rtl" ? "کالای استاندارد" : "Catalog item"
                  }
                  className="min-h-11 w-full rounded border px-3"
                  value={cargoCatalogId}
                  onChange={(event) => {
                    const catalogId = event.target.value;
                    const item = cargoOptions.catalog.find(
                      (option) => option.public_id === catalogId,
                    );
                    setCargoCatalogId(catalogId);
                    if (source === "direct")
                      setCargoUomId(item?.default_uom_public_id || "");
                  }}
                >
                  <option value="">
                    {direction === "rtl"
                      ? "بدون کالای استاندارد در این مرحله"
                      : "Manual cargo / no catalog item in this step"}
                  </option>
                  {selectableCatalog.some((option) => option.preferred) && (
                    <optgroup
                      label={
                        direction === "rtl"
                          ? "پیشنهادی برای این پروژه"
                          : "Preferred for this project"
                      }
                    >
                      {selectableCatalog
                        .filter((option) => option.preferred)
                        .map((option) => (
                          <option
                            key={option.public_id}
                            value={option.public_id}
                          >
                            ★ {option.code} — {option.name}
                          </option>
                        ))}
                    </optgroup>
                  )}
                  <optgroup
                    label={
                      direction === "rtl"
                        ? "سایر کالاهای سازمان"
                        : "Other organization commodities"
                    }
                  >
                    {selectableCatalog
                      .filter((option) => !option.preferred)
                      .map((option) => (
                        <option key={option.public_id} value={option.public_id}>
                          {option.code} — {option.name}
                        </option>
                      ))}
                  </optgroup>
                </select>
                <p className="text-xs text-muted-foreground">
                  {direction === "rtl"
                    ? "ترجیحات پروژه فقط ترتیب نمایش را تغییر می‌دهد؛ پس از ایجاد نیز می‌توان کالا را دستی افزود."
                    : "Project preferences change ranking only. Manual cargo can also be added after creation."}
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="cargo-quantity">
                  {direction === "rtl" ? "مقدار" : "Quantity"}
                </Label>
                <Input
                  id="cargo-quantity"
                  data-field="cargoQuantity"
                  aria-label={
                    direction === "rtl" ? "مقدار کالا" : "Cargo quantity"
                  }
                  type="number"
                  min="0.000001"
                  step="any"
                  disabled={
                    source === "accepted_quote"
                      ? !selectedRequestCargo
                      : !cargoCatalogId
                  }
                  value={cargoQuantity}
                  onChange={(event) => setCargoQuantity(event.target.value)}
                  aria-invalid={!!fieldErrors.cargoQuantity}
                />
                <FieldMessage
                  id="cargo-quantity-error"
                  message={fieldErrors.cargoQuantity}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cargo-uom">
                  {direction === "rtl" ? "واحد اندازه‌گیری" : "Unit of measure"}
                </Label>
                <select
                  id="cargo-uom"
                  data-field="cargoUom"
                  aria-label={
                    direction === "rtl" ? "واحد اندازه‌گیری" : "Unit of measure"
                  }
                  className="min-h-11 w-full rounded border px-3"
                  disabled={source === "accepted_quote" || !cargoCatalogId}
                  value={cargoUomId}
                  onChange={(event) => setCargoUomId(event.target.value)}
                  aria-invalid={!!fieldErrors.cargoUom}
                >
                  <option value="">
                    {direction === "rtl" ? "انتخاب…" : "Select…"}
                  </option>
                  {cargoOptions.uoms.map((option) => (
                    <option key={option.public_id} value={option.public_id}>
                      {direction === "rtl" ? option.name || formatUnitSymbol(option.symbol, "fa-IR") : option.name}
                    </option>
                  ))}
                </select>
                <FieldMessage
                  id="cargo-uom-error"
                  message={fieldErrors.cargoUom}
                />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("operations.review")}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-3 sm:grid-cols-2">
            <div><dt className="text-sm text-slate-500">{t("operations.source")}</dt><dd className="font-medium">
              {source === "direct"
                ? t("operations.source.direct")
                : t("operations.source.quote")}
            </dd></div>
            {source === "direct" && (
              <div><dt className="text-sm text-slate-500">{t("operations.customer")}</dt><dd className="font-medium">
                {customers.find(
                  (customer) => String(customer.id) === customerId,
                )?.label || "—"}
              </dd></div>
            )}
            <div><dt className="text-sm text-slate-500">مبدأ</dt><dd className="font-medium">{sideLabel(origin)}</dd></div>
            <div><dt className="text-sm text-slate-500">مقصد</dt><dd className="font-medium">{sideLabel(destination)}</dd></div>
            <div><dt className="text-sm text-slate-500">روش حمل</dt><dd className="font-medium">{transportLabel(mode)}</dd></div>
            <div><dt className="text-sm text-slate-500">حرکت برنامه‌ریزی‌شده</dt><dd className="font-medium">{localDateTimeInputToUtc(departure)?formatDualCalendarInstant(localDateTimeInputToUtc(departure)!,"fa-IR"):"—"}</dd></div>
            <div><dt className="text-sm text-slate-500">رسیدن برنامه‌ریزی‌شده</dt><dd className="font-medium">{localDateTimeInputToUtc(arrival)?formatDualCalendarInstant(localDateTimeInputToUtc(arrival)!,"fa-IR"):"—"}</dd></div>
            {selectedCargo && (
              <div role="status"><dt className="text-sm text-slate-500">{direction === "rtl" ? "کالا و مقدار" : "Cargo and quantity"}</dt><dd className="font-medium">{selectedCargo.code} —{" "}
                {selectedCargo.name} ·{" "}
                {cargoQuantity || "—"} {formatUnitSymbol(cargoOptions.uoms.find(item=>item.public_id===cargoUomId)?.symbol||"","fa-IR")}
              </dd></div>
            )}
            {selectedRequestCargo && (
              <div role="status" className="sm:col-span-2"><dt className="text-sm text-slate-500">کالا و مقدار منبع</dt><dd className="font-medium">درخواست پذیرفته‌شده، قلم{" "}
                {selectedRequestCargo.position} · درخواست‌شده{" "}
                {Number(selectedRequestCargo.quantity).toLocaleString("fa-IR")}{" "}
                {selectedRequestCargo.uom_name ||
                  formatUnitSymbol(selectedRequestCargo.uom_symbol || "", direction === "rtl" ? "fa-IR" : "en-US")}{" "}
                · برنامه {Number(cargoQuantity || 0).toLocaleString("fa-IR")}{" "}
                {selectedRequestCargo.uom_name ||
                  formatUnitSymbol(selectedRequestCargo.uom_symbol || "", direction === "rtl" ? "fa-IR" : "en-US")}
              </dd></div>
            )}
            </dl>
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
