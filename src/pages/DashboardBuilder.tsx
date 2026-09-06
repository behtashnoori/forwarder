import { useEffect, useMemo, useReducer, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import {
  ApiError,
  getAnalyticsSemanticRegistry,
  getDashboard,
  updateDashboard,
  type AnalyticsSemanticRegistry,
  type PersistedDashboard,
} from "@/lib/api";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import OperationsControlTower from "./OperationsControlTower";
import {
  assess,
  builderReducer,
  newWidget,
  normalizeWidgetOrder,
  widgetShape,
  type BuilderDraft,
  type BuilderState,
} from "@/dashboard/builder-state";
import {
  executableReadiness,
  type DashboardDefinition,
  type WidgetType,
} from "@/dashboard/types";

const semanticVersion = "analytics-semantic-v1",
  schemaVersion = "dashboard-definition-v1";
const widgetLabels: Record<WidgetType, string> = {
  KPI_CARD: "شاخص کلیدی",
  TREND: "روند",
  BAR: "نمودار میله‌ای",
  STACKED_BAR: "میله‌ای انباشته",
  STATUS_DISTRIBUTION: "توزیع وضعیت",
  TABLE: "جدول",
  ATTENTION_LIST: "فهرست توجه",
};
const supportedTypes: WidgetType[] = [
  "KPI_CARD",
  "TREND",
  "BAR",
  "STACKED_BAR",
  "STATUS_DISTRIBUTION",
  "TABLE",
];
function PageState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <main dir="rtl" className="min-h-screen bg-slate-50 p-6">
      <Alert className="mx-auto max-w-xl" role="status">
        <AlertDescription>
          {message}
          {retry && (
            <Button className="mt-3 block" variant="outline" onClick={retry}>
              تلاش دوباره
            </Button>
          )}
        </AlertDescription>
      </Alert>
    </main>
  );
}
const toDraft = (dashboard: PersistedDashboard): BuilderDraft => ({
  name: dashboard.name,
  description: dashboard.description,
  definition: structuredClone(dashboard.definition),
});

export default function DashboardBuilder() {
  const { public_id = "" } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const dashboardQuery = useQuery({
    queryKey: ["dashboard", "detail", public_id],
    queryFn: () => getDashboard(public_id),
    enabled: Boolean(public_id),
    retry: false,
  });
  const registryQuery = useQuery({
    queryKey: ["analytics", "semantic-registry"],
    queryFn: () => getAnalyticsSemanticRegistry(),
    staleTime: 300000,
    retry: false,
  });
  if (!public_id) return <PageState message="داشبورد مورد نظر پیدا نشد." />;
  if (dashboardQuery.isLoading || registryQuery.isLoading)
    return <PageState message="در حال آماده‌سازی ویرایشگر…" />;
  if (dashboardQuery.isError || registryQuery.isError)
    return (
      <PageState
        message="دریافت داشبورد یا راهنمای معنایی ممکن نیست."
        retry={() => {
          void dashboardQuery.refetch();
          void registryQuery.refetch();
        }}
      />
    );
  const dashboard = dashboardQuery.data.data;
  if (dashboard.status === "ARCHIVED")
    return (
      <PageState message="داشبورد بایگانی‌شده در این نسخه قابل ویرایش نیست." />
    );
  if (dashboard.dashboard_type !== "PERSONAL")
    return <PageState message="این داشبورد قابل ویرایش نیست." />;
  if (
    dashboard.semantic_version !== semanticVersion ||
    dashboard.dashboard_schema_version !== schemaVersion
  )
    return <PageState message="نسخهٔ این داشبورد با ویرایشگر سازگار نیست." />;
  return (
    <ReadyBuilder
      dashboard={dashboard}
      registry={registryQuery.data.data}
      onBack={() => navigate(`/dashboards/${dashboard.public_id}`)}
      client={client}
    />
  );
}

function ReadyBuilder({
  dashboard,
  registry,
  onBack,
  client,
}: {
  dashboard: PersistedDashboard;
  registry: AnalyticsSemanticRegistry;
  onBack: () => void;
  client: ReturnType<typeof useQueryClient>;
}) {
  const initial = toDraft(dashboard);
  const initialAssessment = assess(initial, initial, registry);
  const [state, dispatch] = useReducer(builderReducer, {
    persisted: initial,
    draft: initial,
    selectedWidgetId: null,
    ...initialAssessment,
  } satisfies BuilderState);
  const [panel, setPanel] = useState<"add" | "edit" | "filters" | null>(null);
  const [preview, setPreview] = useState(false);
  const dirty =
    state.status !== "READY_CLEAN" && state.status !== "SAVING"
      ? JSON.stringify(state.persisted) !== JSON.stringify(state.draft)
      : state.status === "SAVING";
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
  const mutation = useMutation({
    mutationFn: () =>
      updateDashboard(dashboard.public_id, {
        expected_version: dashboard.version,
        name: state.draft.name.trim(),
        description: state.draft.description,
        definition: state.draft.definition,
        change_reason: "dashboard builder",
      }),
    onMutate: () => dispatch({ type: "SAVING" }),
    onSuccess: ({ data }) => {
      client.setQueryData(["dashboard", "detail", dashboard.public_id], {
        data,
      });
      dispatch({ type: "SAVED", persisted: toDraft(data) });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409)
        dispatch({
          type: "CONFLICT",
          message:
            "نسخهٔ جدیدتری روی سرور ذخیره شده است. برای جلوگیری از بازنویسی، آخرین نسخه را بارگیری کنید.",
        });
      else
        dispatch({
          type: "SAVE_ERROR",
          message: error instanceof Error ? error.message : "ذخیره ناموفق بود.",
        });
    },
  });
  const leave = () => {
    if (!dirty || window.confirm("تغییرات ذخیره‌نشده کنار گذاشته شود؟"))
      onBack();
  };
  const definition = state.draft.definition;
  const selectWidget = (id: string) => {
    dispatch({ type: "SELECT_WIDGET", widgetId: id });
    setPanel("edit");
  };
  const replace = (next: DashboardDefinition) =>
    dispatch({ type: "REPLACE_DEFINITION", definition: next, registry });
  return (
    <main dir="rtl" className="min-h-screen bg-slate-50 p-3 sm:p-5 md:p-8">
      <div className="mx-auto max-w-7xl space-y-4">
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-background/95 p-3 shadow-sm">
          <div>
            <h1 className="text-xl font-bold">ویرایش داشبورد</h1>
            <p className="text-sm text-muted-foreground" role="status">
              {state.status === "READY_CLEAN"
                ? "بدون تغییر"
                : state.status === "SAVING"
                  ? "در حال ذخیره…"
                  : state.status === "CONFLICT"
                    ? "تعارض نسخه"
                    : "تغییرات ذخیره‌نشده"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" onClick={leave}>
              لغو و بازگشت
            </Button>
            <Button
              variant="outline"
              onClick={() => setPreview((value) => !value)}
            >
              {preview ? "بازگشت به ویرایش" : "پیش‌نمایش"}
            </Button>
            <Button
              onClick={() => mutation.mutate()}
              disabled={
                !(
                  ["READY_DIRTY_VALID", "SAVE_ERROR"].includes(state.status) &&
                  state.issues.length === 0
                )
              }
            >
              ذخیره
            </Button>
          </div>
        </header>
        {(state.message || state.issues.length > 0) && (
          <Alert
            variant={
              state.status === "CONFLICT" ||
              state.status === "SAVE_ERROR" ||
              state.issues.length
                ? "destructive"
                : "default"
            }
            role="alert"
          >
            <AlertDescription>
              {state.message ||
                state.issues.map((issue) => issue.message).join(" ")}
              {state.status === "CONFLICT" && (
                <Button
                  className="mt-2 block"
                  variant="outline"
                  onClick={() => window.location.reload()}
                >
                  بارگیری آخرین نسخه
                </Button>
              )}
            </AlertDescription>
          </Alert>
        )}
        {preview ? (
          <OperationsControlTower
            definition={definition}
            displayName={state.draft.name}
            displayDescription={state.draft.description}
            sourceContext="پیش‌نمایش محلی — ذخیره نشده"
            allowClone={false}
          />
        ) : (
          <>
            <section className="grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="dashboard-name">نام داشبورد</Label>
                <Input
                  id="dashboard-name"
                  value={state.draft.name}
                  maxLength={120}
                  onChange={(e) =>
                    dispatch({
                      type: "CHANGE_META",
                      field: "name",
                      value: e.target.value,
                      registry,
                    })
                  }
                />
              </div>
              <div>
                <Label htmlFor="dashboard-description">توضیح</Label>
                <Textarea
                  id="dashboard-description"
                  value={state.draft.description}
                  maxLength={1000}
                  onChange={(e) =>
                    dispatch({
                      type: "CHANGE_META",
                      field: "description",
                      value: e.target.value,
                      registry,
                    })
                  }
                />
              </div>
            </section>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => setPanel("add")}>افزودن ویجت</Button>
              <Button variant="outline" onClick={() => setPanel("filters")}>
                فیلترهای سراسری
              </Button>
            </div>
            {definition.sections.map((section) => (
              <section
                key={section.section_id}
                aria-labelledby={`builder-${section.section_id}`}
              >
                <h2
                  id={`builder-${section.section_id}`}
                  className="mb-3 text-lg font-semibold"
                >
                  {section.title}
                </h2>
                <div className="grid gap-4 md:grid-cols-2">
                  {section.widget_ids.map((id) => {
                    const widget = definition.widgets.find(
                      (item) => item.widget_id === id,
                    );
                    return (
                      widget && (
                        <article
                          key={id}
                          className="rounded-lg border bg-card p-4"
                        >
                          <h3 className="font-semibold">{widget.title}</h3>
                          <p className="text-sm text-muted-foreground">
                            {widgetLabels[widget.widget_type]}
                          </p>
                          <Button
                            className="mt-3"
                            variant="outline"
                            onClick={() => selectWidget(id)}
                          >
                            پیکربندی ویجت
                          </Button>
                        </article>
                      )
                    );
                  })}
                </div>
              </section>
            ))}
          </>
        )}
        <Sheet
          open={panel !== null}
          onOpenChange={(open) => !open && setPanel(null)}
        >
          <SheetContent
            side="left"
            className="w-full overflow-y-auto sm:max-w-md"
          >
            <SheetHeader>
              <SheetTitle>
                {panel === "add"
                  ? "افزودن ویجت"
                  : panel === "filters"
                    ? "فیلترهای سراسری"
                    : "پیکربندی ویجت"}
              </SheetTitle>
              <SheetDescription>
                گزینه‌ها بر پایهٔ راهنمای معنایی سامانه محدود شده‌اند.
              </SheetDescription>
            </SheetHeader>
            {panel === "add" && (
              <AddWidget
                registry={registry}
                onAdd={(widget) => {
                  const ids = [
                    ...definition.sections[0].widget_ids,
                    widget.widget_id,
                  ];
                  replace(
                    normalizeWidgetOrder(
                      {
                        ...definition,
                        widgets: [...definition.widgets, widget],
                      },
                      ids,
                    ),
                  );
                  setPanel(null);
                }}
              />
            )}
            {panel === "edit" && state.selectedWidgetId && (
              <EditWidget
                definition={definition}
                registry={registry}
                widgetId={state.selectedWidgetId}
                onChange={replace}
                onClose={() => setPanel(null)}
              />
            )}{" "}
            {panel === "filters" && (
              <GlobalFilters
                definition={definition}
                registry={registry}
                onChange={replace}
              />
            )}
          </SheetContent>
        </Sheet>
      </div>
    </main>
  );
}

function AddWidget({
  registry,
  onAdd,
}: {
  registry: AnalyticsSemanticRegistry;
  onAdd: (widget: ReturnType<typeof newWidget>) => void;
}) {
  const [type, setType] = useState<WidgetType>("KPI_CARD");
  const [metric, setMetric] = useState("");
  const [dimension, setDimension] = useState("");
  const [grain, setGrain] = useState<
    "day" | "week" | "month" | "quarter" | "year"
  >("day");
  const metricDef = registry.metrics.find((item) => item.metric_key === metric);
  const shape = widgetShape(type);
  const dimensions = (metricDef?.supported_dimensions || []).filter((value) =>
    shape.time ? value === "TIME" : value !== "TIME",
  );
  const valid = Boolean(
    metricDef &&
    (!shape.needsDimension || dimension) &&
    (!shape.time || metricDef.supported_time_dimensions?.[0]),
  );
  return (
    <div className="mt-5 space-y-4">
      <Field label="نوع ویجت">
        <select
          className="w-full rounded-md border p-2"
          value={type}
          onChange={(e) => {
            setType(e.target.value as WidgetType);
            setDimension("");
          }}
        >
          {supportedTypes.map((value) => (
            <option key={value} value={value}>
              {widgetLabels[value]}
            </option>
          ))}
        </select>
      </Field>
      <Field label="شاخص">
        <select
          className="w-full rounded-md border p-2"
          value={metric}
          onChange={(e) => {
            setMetric(e.target.value);
            setDimension("");
          }}
        >
          <option value="">انتخاب کنید</option>
          {registry.metrics
            .filter((item) => executableReadiness(item.readiness))
            .map((item) => (
              <option key={item.metric_key} value={item.metric_key}>
                {item.business_name}
              </option>
            ))}
        </select>
      </Field>
      {shape.needsDimension && (
        <Field label={shape.time ? "بُعد زمانی" : "بُعد"}>
          <select
            className="w-full rounded-md border p-2"
            value={dimension}
            onChange={(e) => setDimension(e.target.value)}
          >
            <option value="">انتخاب کنید</option>
            {dimensions.map((key) => (
              <option key={key} value={key}>
                {registry.dimensions.find((item) => item.dimension_key === key)
                  ?.business_name || key}
              </option>
            ))}
          </select>
        </Field>
      )}
      {shape.time && (
        <Field label="دانه‌بندی زمان">
          <select
            className="w-full rounded-md border p-2"
            value={grain}
            onChange={(e) => setGrain(e.target.value as typeof grain)}
          >
            {(metricDef?.supported_time_grains || []).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
      )}
      <Button
        disabled={!valid}
        onClick={() =>
          metricDef &&
          onAdd(
            newWidget(
              type,
              metric,
              metricDef.business_name,
              dimension || undefined,
              shape.time ? metricDef.supported_time_dimensions?.[0] : undefined,
              shape.time ? grain : undefined,
            ),
          )
        }
      >
        افزودن
      </Button>
    </div>
  );
}
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1 text-sm font-medium">
      <span>{label}</span>
      {children}
    </label>
  );
}
function EditWidget({
  definition,
  registry,
  widgetId,
  onChange,
  onClose,
}: {
  definition: DashboardDefinition;
  registry: AnalyticsSemanticRegistry;
  widgetId: string;
  onChange: (value: DashboardDefinition) => void;
  onClose: () => void;
}) {
  const widget = definition.widgets.find(
    (item) => item.widget_id === widgetId,
  )!;
  const ids = definition.sections[0].widget_ids;
  const index = ids.indexOf(widgetId);
  const metric = registry.metrics.find(
    (item) => item.metric_key === widget.query.metric_keys[0],
  );
  const shape = widgetShape(widget.widget_type);
  const dimensions = (metric?.supported_dimensions || []).filter((value) =>
    shape.time ? value === "TIME" : value !== "TIME",
  );
  const filter = widget.query.filters?.[0];
  const [filterDimension, setFilterDimension] = useState(filter?.dimension || "");
  const filterDimensions = (metric?.supported_filters || []).filter(
    (value) => value !== "TIME",
  );
  const update = (next: typeof widget) =>
    onChange({
      ...definition,
      widgets: definition.widgets.map((item) =>
        item.widget_id === widgetId ? next : item,
      ),
    });
  const changeMetric = (metricKey: string) => {
    const nextMetric = registry.metrics.find(
      (item) => item.metric_key === metricKey,
    )!;
    const dimension = shape.needsDimension
      ? nextMetric.supported_dimensions.find((value) =>
          shape.time ? value === "TIME" : value !== "TIME",
        )
      : undefined;
    update({
      ...widget,
      title: nextMetric.business_name,
      query: {
        ...widget.query,
        metric_keys: [metricKey],
        dimension_keys: dimension ? [dimension] : [],
        filters: [],
        time_dimension: shape.time
          ? nextMetric.supported_time_dimensions?.[0]
          : undefined,
        time_grain: shape.time
          ? (nextMetric
              .supported_time_grains?.[0] as typeof widget.query.time_grain)
          : undefined,
      },
      drilldown: { enabled: false },
    });
  };
  const changeFilter = (dimension: string, value: string) =>
    update({
      ...widget,
      query: {
        ...widget.query,
        filters: dimension && value ? [{ dimension, value }] : [],
      },
    });
  const move = (offset: number) => {
    const next = [...ids];
    const [item] = next.splice(index, 1);
    next.splice(index + offset, 0, item);
    onChange(normalizeWidgetOrder(definition, next));
  };
  const remove = () => {
    if (window.confirm("این ویجت از پیش‌نویس حذف شود؟")) {
      onChange({
        ...definition,
        widgets: definition.widgets.filter(
          (item) => item.widget_id !== widgetId,
        ),
        sections: definition.sections.map((section, i) =>
          i === 0
            ? {
                ...section,
                widget_ids: section.widget_ids.filter((id) => id !== widgetId),
              }
            : section,
        ),
        global_filters: definition.global_filters
          .map((filter) => ({
            ...filter,
            applicable_widget_ids: filter.applicable_widget_ids.filter(
              (id) => id !== widgetId,
            ),
          }))
          .filter((filter) => filter.applicable_widget_ids.length > 0),
      });
      onClose();
    }
  };
  return (
    <div className="mt-5 space-y-4">
      <Field label="عنوان">
        <Input
          value={widget.title}
          maxLength={120}
          onChange={(e) => update({ ...widget, title: e.target.value })}
        />
      </Field>
      <Field label="شاخص">
        <select
          className="w-full rounded-md border p-2"
          value={widget.query.metric_keys[0]}
          onChange={(e) => changeMetric(e.target.value)}
        >
          {registry.metrics
            .filter(
              (item) =>
                executableReadiness(item.readiness) &&
                (!shape.needsDimension ||
                  item.supported_dimensions.some((value) =>
                    shape.time ? value === "TIME" : value !== "TIME",
                  )),
            )
            .map((item) => (
              <option key={item.metric_key} value={item.metric_key}>
                {item.business_name}
              </option>
            ))}
        </select>
      </Field>
      {shape.needsDimension && (
        <Field label={shape.time ? "بُعد زمانی" : "بُعد"}>
          <select
            className="w-full rounded-md border p-2"
            value={widget.query.dimension_keys[0] || ""}
            onChange={(e) =>
              update({
                ...widget,
                query: { ...widget.query, dimension_keys: [e.target.value] },
              })
            }
          >
            {dimensions.map((key) => (
              <option key={key} value={key}>
                {registry.dimensions.find((item) => item.dimension_key === key)
                  ?.business_name || key}
              </option>
            ))}
          </select>
        </Field>
      )}
      {filterDimensions.length > 0 && (
        <>
          <Field label="فیلتر اختصاصی">
            <select
              className="w-full rounded-md border p-2"
              value={filterDimension}
              onChange={(e) => {
                setFilterDimension(e.target.value);
                if (!e.target.value) changeFilter("", "");
              }}
            >
              <option value="">بدون فیلتر</option>
              {filterDimensions.map((key) => (
                <option key={key} value={key}>
                  {registry.dimensions.find(
                    (item) => item.dimension_key === key,
                  )?.business_name || key}
                </option>
              ))}
            </select>
          </Field>
          {filterDimension && (
            <Field label="شناسه عمومی مقدار فیلتر">
              <Input
                value={filter?.dimension === filterDimension && typeof filter.value === "string" ? filter.value : ""}
                onChange={(e) => changeFilter(filterDimension, e.target.value)}
                placeholder="شناسه عمومی مجاز"
              />
            </Field>
          )}
        </>
      )}
      <Field label="اندازه">
        <select
          className="w-full rounded-md border p-2"
          value={widget.layout.col_span}
          onChange={(e) =>
            update({
              ...widget,
              layout: {
                ...widget.layout,
                col_span: Number(e.target.value) as 1 | 2 | 3 | 4,
              },
            })
          }
        >
          <option value="1">فشرده</option>
          <option value="2">استاندارد</option>
          <option value="4">تمام‌عرض</option>
        </select>
      </Field>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          disabled={index === 0}
          onClick={() => move(-1)}
        >
          انتقال به قبل
        </Button>
        <Button
          variant="outline"
          disabled={index === ids.length - 1}
          onClick={() => move(1)}
        >
          انتقال به بعد
        </Button>
        <Button
          variant="destructive"
          disabled={definition.widgets.length === 1}
          onClick={remove}
        >
          حذف ویجت
        </Button>
      </div>
    </div>
  );
}
function GlobalFilters({
  definition,
  registry,
  onChange,
}: {
  definition: DashboardDefinition;
  registry: AnalyticsSemanticRegistry;
  onChange: (value: DashboardDefinition) => void;
}) {
  const allowed = ["TIME", "CUSTOMER", "PROJECT"].filter((key) =>
    registry.dimensions.some(
      (item) =>
        item.dimension_key === key && executableReadiness(item.readiness),
    ),
  );
  const toggle = (key: string, checked: boolean) => {
    const applicable = definition.widgets
      .filter((widget) =>
        widget.query.metric_keys.every((metric) =>
          registry.metrics
            .find((item) => item.metric_key === metric)
            ?.supported_filters?.includes(key),
        ),
      )
      .map((widget) => widget.widget_id);
    if (checked && !applicable.length) return;
    const label =
      registry.dimensions.find((item) => item.dimension_key === key)
        ?.business_name || key;
    onChange({
      ...definition,
      global_filters: checked
        ? [
            ...definition.global_filters.filter(
              (item) => item.dimension_key !== key,
            ),
            { dimension_key: key, label, applicable_widget_ids: applicable },
          ]
        : definition.global_filters.filter(
            (item) => item.dimension_key !== key,
          ),
    });
  };
  return (
    <fieldset className="mt-5 space-y-3">
      <legend className="sr-only">فیلترهای سراسری</legend>
      {allowed.map((key) => {
        const current = definition.global_filters.find(
          (item) => item.dimension_key === key,
        );
        return (
          <label
            key={key}
            className="flex items-center justify-between gap-3 rounded border p-3"
          >
            <span>
              {registry.dimensions.find((item) => item.dimension_key === key)
                ?.business_name || key}
              {current && (
                <small className="block text-muted-foreground">
                  روی {current.applicable_widget_ids.length} از{" "}
                  {definition.widgets.length} ویجت اعمال می‌شود
                </small>
              )}
            </span>
            <input
              type="checkbox"
              checked={Boolean(current)}
              onChange={(e) => toggle(key, e.target.checked)}
            />
          </label>
        );
      })}
    </fieldset>
  );
}
