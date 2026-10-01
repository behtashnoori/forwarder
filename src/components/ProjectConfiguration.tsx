import { useCallback, useEffect, useMemo, useState } from "react";
import ProjectLogisticsNetwork from "@/components/ProjectLogisticsNetwork";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  createProjectConfiguration,
  getShipmentCargoOptions,
  listMilestoneTypes,
  listProjectConfiguration,
  listProjectDocumentDefinitions,
  listProjectLogisticsPointSelectors,
  listProjectServiceTypes,
  reorderProjectMilestones,
  setProjectConfigurationActive,
  updateProjectConfiguration,
  type ProjectConfigurationItem,
  type ProjectConfigurationResource,
} from "@/lib/api";

type Locale = "fa" | "en";
type Props = { projectId: string; canManage?: boolean; locale?: Locale };
type Ref = { public_id: string; label: string };
const numberOrNull = (value: string) => (value === "" ? null : Number(value));

function Panel({
  projectId,
  resource,
  canManage,
  locale,
}: {
  projectId: string;
  resource: ProjectConfigurationResource;
  canManage: boolean;
  locale: Locale;
}) {
  const fa = locale === "fa";
  const label = (faText: string, enText: string) => (fa ? faText : enText);
  const [rows, setRows] = useState<ProjectConfigurationItem[]>([]);
  const [refs, setRefs] = useState<Ref[]>([]);
  const [points, setPoints] = useState<Ref[]>([]);
  const [selected, setSelected] = useState("");
  const [editing, setEditing] = useState<ProjectConfigurationItem | null>(null);
  const [form, setForm] = useState<Record<string, string | boolean>>({
    requirement_level: "REQUIRED",
    duration_unit: "HOUR",
    display_order: "0",
    sequence: "1",
    is_primary: false,
    is_required: false,
  });
  const [loading, setLoading] = useState(true);
  const [selectorLoading, setSelectorLoading] = useState(true);
  const [error, setError] = useState("");
  const active = useMemo(() => rows.filter((item) => item.is_active), [rows]);
  const titles: Record<ProjectConfigurationResource, string> = fa
    ? {
        services: "خدمات پروژه",
        "document-requirements": "اسناد موردنیاز",
        commodities: "کالاهای ترجیحی",
        "milestone-definitions": "مراحل پروژه",
      }
    : {
        services: "Services",
        "document-requirements": "Documents",
        commodities: "Commodities",
        "milestone-definitions": "Milestones",
      };
  const title = titles[resource];

  const load = useCallback(async () => {
    setLoading(true);
    setSelectorLoading(true);
    setError("");
    try {
      const listed = await listProjectConfiguration(projectId, resource, {
        page: 1,
        per_page: 100,
      });
      setRows(listed.items);
      if (resource === "services") {
        const response = await listProjectServiceTypes({
          page: 1,
          per_page: 100,
        });
        setRefs(
          response.items.map((item) => ({
            public_id: item.public_id,
            label: item.fa_name || item.en_name,
          })),
        );
      } else if (resource === "document-requirements") {
        const response = await listProjectDocumentDefinitions({
          page: 1,
          per_page: 100,
        });
        setRefs(
          response.items.map((item) => ({
            public_id: item.public_id,
            label: item.title,
          })),
        );
      } else if (resource === "commodities") {
        const response = await getShipmentCargoOptions();
        setRefs(
          response.catalog.map((item) => ({
            public_id: item.public_id,
            label: item.name,
          })),
        );
      } else {
        const [types, locations] = await Promise.all([
          listMilestoneTypes({ page: 1, per_page: 100 }),
          listProjectLogisticsPointSelectors(projectId, {
            page: 1,
            per_page: 100,
          }),
        ]);
        setRefs(
          types.items.map((item) => ({
            public_id: item.public_id,
            label: item.fa_name || item.en_name,
          })),
        );
        setPoints(
          locations.items.map((item) => ({
            public_id: item.public_id,
            label:
              item.display_label ||
              (fa ? "نقطه لجستیکی پروژه" : "Project logistics point"),
          })),
        );
      }
    } catch {
      setError(
        fa
          ? "بارگذاری پیکربندی پروژه انجام نشد."
          : "Project configuration could not be loaded.",
      );
    } finally {
      setLoading(false);
      setSelectorLoading(false);
    }
  }, [projectId, resource, fa]);
  useEffect(() => {
    void load();
  }, [load]);

  const field = (key: string) => String(form[key] ?? "");
  const checked = (key: string) => form[key] === true;
  const change = (key: string, value: string | boolean) =>
    setForm((current) => ({ ...current, [key]: value }));
  const payload = () =>
    resource === "services"
      ? {
          service_type_public_id: selected,
          is_primary: checked("is_primary"),
          is_required: checked("is_required"),
          display_order: Number(field("display_order") || 0),
          display_label: field("display_label") || null,
          notes: field("notes") || null,
        }
      : resource === "document-requirements"
        ? {
            document_definition_public_id: selected,
            requirement_level: field("requirement_level"),
            conditional_description:
              field("requirement_level") === "CONDITIONAL"
                ? field("conditional_description")
                : null,
            display_order: Number(field("display_order") || 0),
            notes: field("notes") || null,
          }
        : resource === "commodities"
          ? {
              cargo_catalog_item_public_id: selected,
              display_order: Number(field("display_order") || 0),
            }
          : {
              milestone_type_public_id: selected,
              sequence: Number(field("sequence")),
              is_required: checked("is_required"),
              project_logistics_point_public_id:
                field("project_logistics_point_public_id") || null,
              display_label: field("display_label") || null,
              target_duration_value: numberOrNull(
                field("target_duration_value"),
              ),
              warning_duration_value: numberOrNull(
                field("warning_duration_value"),
              ),
              duration_unit:
                field("target_duration_value") ||
                field("warning_duration_value")
                  ? field("duration_unit")
                  : null,
              notes: field("notes") || null,
            };
  const validate = () => {
    if (resource !== "milestone-definitions") return "";
    const target = numberOrNull(field("target_duration_value"));
    const warning = numberOrNull(field("warning_duration_value"));
    if ((target !== null && target < 1) || (warning !== null && warning < 1))
      return label(
        "مدت‌ها باید عددی مثبت باشند.",
        "Durations must be positive",
      );
    if (target !== null && warning !== null && warning < target)
      return label(
        "مدت هشدار باید بزرگ‌تر یا مساوی مدت هدف باشد.",
        "Warning duration must be greater than or equal to target",
      );
    return "";
  };
  const save = async () => {
    const invalid = validate();
    if (invalid) {
      setError(invalid);
      return;
    }
    try {
      setError("");
      const data: Record<string, unknown> = payload();
      if (editing) {
        delete data.service_type_public_id;
        delete data.document_definition_public_id;
        delete data.milestone_type_public_id;
        delete data.cargo_catalog_item_public_id;
        await updateProjectConfiguration(projectId, resource, editing, data);
      } else await createProjectConfiguration(projectId, resource, data);
      setEditing(null);
      setSelected("");
      await load();
    } catch {
      setError(
        label(
          "ذخیره پیکربندی انجام نشد. فهرست را تازه‌سازی کنید.",
          "Configuration could not be saved. Refresh the list.",
        ),
      );
    }
  };
  const edit = (item: ProjectConfigurationItem) => {
    setEditing(item);
    setSelected(
      item.service_type_public_id ||
        item.document_definition_public_id ||
        item.milestone_type_public_id ||
        item.cargo_catalog_item_public_id ||
        "",
    );
    setForm({
      is_primary: !!item.is_primary,
      is_required: !!item.is_required,
      display_order: String(item.display_order ?? 0),
      display_label: item.display_label || "",
      notes: item.notes || "",
      requirement_level: item.requirement_level || "REQUIRED",
      conditional_description: item.conditional_description || "",
      sequence: String(item.sequence ?? 1),
      project_logistics_point_public_id:
        item.project_logistics_point_public_id || "",
      target_duration_value: String(item.target_duration_value ?? ""),
      warning_duration_value: String(item.warning_duration_value ?? ""),
      duration_unit: item.duration_unit || "HOUR",
    });
  };
  const move = async (item: ProjectConfigurationItem, delta: number) => {
    const index = active.indexOf(item),
      target = index + delta;
    if (target < 0 || target >= active.length) return;
    const ordered = [...active];
    [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
    try {
      await reorderProjectMilestones(projectId, ordered);
      await load();
    } catch {
      setError(
        label(
          "تغییر ترتیب مراحل انجام نشد.",
          "Milestone order could not be changed.",
        ),
      );
    }
  };
  const rowLabel = (item: ProjectConfigurationItem) =>
    item.display_label ||
    item.document_definition_title ||
    item.cargo_catalog_item_name ||
    label("مورد پیکربندی‌شده", "Configured item");

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {resource === "milestone-definitions" && (
          <p>
            {label(
              "پیکربندی پروژه به‌تنهایی مرحله عملیاتی ایجاد نمی‌کند.",
              "Project configuration does not create operational milestones.",
            )}
          </p>
        )}
      </CardHeader>
      <CardContent className="min-w-0 space-y-3 overflow-x-hidden">
        {error && (
          <div role="alert">
            {error}
            <Button variant="link" onClick={() => void load()}>
              {label("تازه‌سازی", "Refresh")}
            </Button>
          </div>
        )}
        {loading && (
          <p role="status">
            {label("در حال بارگذاری پیکربندی…", "Loading configuration…")}
          </p>
        )}
        {!loading && rows.length === 0 && (
          <p>
            {label("هنوز موردی پیکربندی نشده است.", "No configured items.")}
          </p>
        )}
        {canManage ? (
          <fieldset className="grid min-w-0 gap-2 sm:grid-cols-2">
            <legend>
              {editing
                ? label(`ویرایش ${title}`, `Edit ${title}`)
                : label(`افزودن به ${title}`, `Add ${title}`)}
            </legend>
            <label>
              {label("نوع تعریف‌شده", "Governed type")}
              <select
                aria-label={label("نوع تعریف‌شده", "Governed type")}
                disabled={!!editing || selectorLoading}
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
              >
                <option value="">
                  {selectorLoading
                    ? label("در حال بارگذاری گزینه‌ها…", "Loading options…")
                    : refs.length
                      ? label("یک گزینه انتخاب کنید", "Select an option")
                      : label("گزینه فعالی وجود ندارد", "No active options")}
                </option>
                {refs.map((item) => (
                  <option key={item.public_id} value={item.public_id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            {resource === "services" && (
              <>
                <label>
                  <input
                    type="checkbox"
                    checked={checked("is_primary")}
                    onChange={(event) =>
                      change("is_primary", event.target.checked)
                    }
                  />{" "}
                  {label("خدمت اصلی", "Primary")}
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={checked("is_required")}
                    onChange={(event) =>
                      change("is_required", event.target.checked)
                    }
                  />{" "}
                  {label("الزامی", "Required")}
                </label>
                <label>
                  {label("ترتیب نمایش", "Display order")}
                  <Input
                    type="number"
                    min="0"
                    value={field("display_order")}
                    onChange={(event) =>
                      change("display_order", event.target.value)
                    }
                  />
                </label>
              </>
            )}
            {resource === "document-requirements" && (
              <>
                <label>
                  {label("سطح نیازمندی", "Requirement level")}
                  <select
                    aria-label={label("سطح نیازمندی", "Requirement level")}
                    value={field("requirement_level")}
                    onChange={(event) =>
                      change("requirement_level", event.target.value)
                    }
                  >
                    <option value="REQUIRED">
                      {label("الزامی", "Required")}
                    </option>
                    <option value="OPTIONAL">
                      {label("اختیاری", "Optional")}
                    </option>
                    <option value="CONDITIONAL">
                      {label("مشروط", "Conditional")}
                    </option>
                  </select>
                </label>
                {field("requirement_level") === "CONDITIONAL" && (
                  <label>
                    {label("شرح شرط", "Conditional description")}
                    <Input
                      value={field("conditional_description")}
                      onChange={(event) =>
                        change("conditional_description", event.target.value)
                      }
                    />
                  </label>
                )}
                <label>
                  {label("ترتیب نمایش", "Display order")}
                  <Input
                    type="number"
                    min="0"
                    value={field("display_order")}
                    onChange={(event) =>
                      change("display_order", event.target.value)
                    }
                  />
                </label>
              </>
            )}
            {resource === "commodities" && (
              <>
                <p className="text-sm text-muted-foreground sm:col-span-2">
                  {label(
                    "کالاهای پروژه فقط ترجیح نمایشی هستند؛ همه کالاهای فعال سازمان همچنان قابل انتخاب‌اند.",
                    "Project commodities are preferences only; every active organization commodity remains selectable.",
                  )}
                </p>
                <label>
                  {label("ترتیب نمایش کالا", "Commodity display order")}
                  <Input
                    aria-label={label(
                      "ترتیب نمایش کالا",
                      "Commodity display order",
                    )}
                    type="number"
                    min="0"
                    value={field("display_order")}
                    onChange={(event) =>
                      change("display_order", event.target.value)
                    }
                  />
                </label>
              </>
            )}
            {resource === "milestone-definitions" && (
              <>
                <label>
                  {label("ترتیب مرحله", "Sequence")}
                  <Input
                    type="number"
                    min="1"
                    value={field("sequence")}
                    onChange={(event) => change("sequence", event.target.value)}
                  />
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={checked("is_required")}
                    onChange={(event) =>
                      change("is_required", event.target.checked)
                    }
                  />{" "}
                  {label("الزامی", "Required")}
                </label>
                <label>
                  {label("نقطه لجستیکی پروژه", "Project logistics point")}
                  <select
                    aria-label={label(
                      "نقطه لجستیکی پروژه",
                      "Project logistics point",
                    )}
                    value={field("project_logistics_point_public_id")}
                    onChange={(event) =>
                      change(
                        "project_logistics_point_public_id",
                        event.target.value,
                      )
                    }
                  >
                    <option value="">{label("بدون نقطه", "None")}</option>
                    {points.map((item) => (
                      <option key={item.public_id} value={item.public_id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {label("مدت هدف", "Target duration")}
                  <Input
                    type="number"
                    min="1"
                    value={field("target_duration_value")}
                    onChange={(event) =>
                      change("target_duration_value", event.target.value)
                    }
                  />
                </label>
                <label>
                  {label("مدت هشدار", "Warning duration")}
                  <Input
                    type="number"
                    min="1"
                    value={field("warning_duration_value")}
                    onChange={(event) =>
                      change("warning_duration_value", event.target.value)
                    }
                  />
                </label>
                <label>
                  {label("واحد مدت", "Duration unit")}
                  <select
                    aria-label={label("واحد مدت", "Duration unit")}
                    value={field("duration_unit")}
                    onChange={(event) =>
                      change("duration_unit", event.target.value)
                    }
                  >
                    <option value="MINUTE">{label("دقیقه", "Minute")}</option>
                    <option value="HOUR">{label("ساعت", "Hour")}</option>
                    <option value="DAY">{label("روز", "Day")}</option>
                  </select>
                </label>
              </>
            )}
            {resource !== "document-requirements" &&
              resource !== "commodities" && (
                <label>
                  {label("برچسب نمایشی", "Display label")}
                  <Input
                    value={field("display_label")}
                    onChange={(event) =>
                      change("display_label", event.target.value)
                    }
                  />
                </label>
              )}
            {resource !== "commodities" && (
              <label>
                {label("یادداشت", "Notes")}
                <Input
                  value={field("notes")}
                  onChange={(event) => change("notes", event.target.value)}
                />
              </label>
            )}
            <Button
              disabled={!selected || selectorLoading}
              onClick={() => void save()}
            >
              {editing
                ? label("ذخیره تغییرات", "Save changes")
                : label("افزودن", "Add")}
            </Button>
            {editing && (
              <Button variant="outline" onClick={() => setEditing(null)}>
                {label("انصراف", "Cancel")}
              </Button>
            )}
          </fieldset>
        ) : (
          <p>{label("دسترسی فقط خواندنی", "Read-only access")}</p>
        )}
        <div>
          {rows.map((item) => (
            <div
              key={item.public_id}
              className="flex min-w-0 flex-wrap items-center gap-2 rounded border p-3"
            >
              <span>{rowLabel(item)}</span>
              <span>
                {item.is_active
                  ? label("فعال", "Active")
                  : label("غیرفعال", "Inactive")}
              </span>
              {item.cargo_catalog_item_code && (
                <details className="text-xs text-muted-foreground">
                  <summary>
                    {label("شناسه فنی", "Technical identifier")}
                  </summary>
                  <bdi>{item.cargo_catalog_item_code}</bdi>
                </details>
              )}
              {canManage && (
                <>
                  <Button
                    aria-label={label(
                      `ویرایش مورد ${title}`,
                      `Edit ${title} item`,
                    )}
                    variant="outline"
                    onClick={() => edit(item)}
                  >
                    {label("ویرایش", "Edit")}
                  </Button>
                  {resource === "milestone-definitions" && item.is_active && (
                    <>
                      <Button
                        aria-label={label(
                          "انتقال مرحله به بالا",
                          "Move milestone up",
                        )}
                        onClick={() => void move(item, -1)}
                      >
                        ↑
                      </Button>
                      <Button
                        aria-label={label(
                          "انتقال مرحله به پایین",
                          "Move milestone down",
                        )}
                        onClick={() => void move(item, 1)}
                      >
                        ↓
                      </Button>
                    </>
                  )}
                  <Button
                    onClick={async () => {
                      try {
                        await setProjectConfigurationActive(
                          projectId,
                          resource,
                          item,
                          !item.is_active,
                        );
                        await load();
                      } catch {
                        setError(
                          label(
                            "تغییر وضعیت انجام نشد.",
                            "Lifecycle change failed.",
                          ),
                        );
                      }
                    }}
                  >
                    {item.is_active
                      ? label("غیرفعال‌سازی", "Deactivate")
                      : label("فعال‌سازی", "Activate")}
                  </Button>
                </>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function ProjectConfiguration({
  projectId,
  canManage = true,
  locale = "fa",
}: Props) {
  const fa = locale === "fa";
  return (
    <section
      dir={fa ? "rtl" : "ltr"}
      lang={locale}
      className="min-w-0 space-y-3 overflow-x-hidden"
    >
      <h2>{fa ? "پیکربندی پروژه" : "Project Configuration"}</h2>
      <Tabs defaultValue="services">
        <TabsList className="flex h-auto flex-wrap">
          <TabsTrigger value="services">
            {fa ? "خدمات" : "Services"}
          </TabsTrigger>
          <TabsTrigger value="network">
            {fa ? "شبکه لجستیکی" : "Network"}
          </TabsTrigger>
          <TabsTrigger value="commodities">
            {fa ? "کالاها" : "Commodities"}
          </TabsTrigger>
          <TabsTrigger value="documents">
            {fa ? "اسناد" : "Documents"}
          </TabsTrigger>
          <TabsTrigger value="milestones">
            {fa ? "مراحل" : "Milestones"}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="services">
          <Panel
            projectId={projectId}
            resource="services"
            canManage={canManage}
            locale={locale}
          />
        </TabsContent>
        <TabsContent value="network">
          <ProjectLogisticsNetwork projectId={projectId} />
        </TabsContent>
        <TabsContent value="commodities">
          <Panel
            projectId={projectId}
            resource="commodities"
            canManage={canManage}
            locale={locale}
          />
        </TabsContent>
        <TabsContent value="documents">
          <Panel
            projectId={projectId}
            resource="document-requirements"
            canManage={canManage}
            locale={locale}
          />
        </TabsContent>
        <TabsContent value="milestones">
          <Panel
            projectId={projectId}
            resource="milestone-definitions"
            canManage={canManage}
            locale={locale}
          />
        </TabsContent>
      </Tabs>
    </section>
  );
}
