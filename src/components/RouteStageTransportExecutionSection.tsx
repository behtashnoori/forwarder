import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  createRouteStageTransportExecution,
  getTransportExecutionOptions,
  listRouteStageTransportExecutions,
  reviseRouteStageTransportExecution,
  type RouteStageTransportExecution,
  type RouteStageTransportExecutionList,
  type TransportExecutionDraft,
  type TransportExecutionOptions,
  type TransportExecutionRevision,
} from "@/lib/api";

type EquipmentDraft = {
  type_public_id: string;
  identifier: string;
  details: string;
};

type FormState = {
  transport_means_type_public_id: string;
  carrier_customer_id: string;
  means_identifier: string;
  means_details: string;
  driver_name: string;
  driver_contact: string;
  reason: string;
  equipment: EquipmentDraft[];
};

const emptyForm = (): FormState => ({
  transport_means_type_public_id: "",
  carrier_customer_id: "",
  means_identifier: "",
  means_details: "",
  driver_name: "",
  driver_contact: "",
  reason: "",
  equipment: [],
});

const fromRevision = (revision: TransportExecutionRevision): FormState => ({
  transport_means_type_public_id: revision.means.public_id,
  carrier_customer_id: revision.carrier ? String(revision.carrier.id) : "",
  means_identifier: revision.means_identifier || "",
  means_details: revision.means_details || "",
  driver_name: revision.driver.name || "",
  driver_contact: revision.driver.contact || "",
  reason: "",
  equipment: revision.equipment.map((item) => ({
    type_public_id: item.type.public_id,
    identifier: item.identifier || "",
    details: item.details || "",
  })),
});

const toPayload = (form: FormState, expectedVersion?: number): TransportExecutionDraft => ({
  transport_means_type_public_id: form.transport_means_type_public_id,
  carrier_customer_id: form.carrier_customer_id ? Number(form.carrier_customer_id) : null,
  means_identifier: form.means_identifier.trim() || null,
  means_details: form.means_details.trim() || null,
  driver_name: form.driver_name.trim() || null,
  driver_contact: form.driver_contact.trim() || null,
  equipment: form.equipment.map((item) => ({
    type_public_id: item.type_public_id,
    identifier: item.identifier.trim() || null,
    details: item.details.trim() || null,
  })),
  ...(form.reason.trim() ? { reason: form.reason.trim() } : {}),
  ...(expectedVersion === undefined ? {} : { expected_version: expectedVersion }),
});

const messageFor = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 403) return "فقط کارشناس مسئول این محموله می‌تواند اجرای حمل را تغییر دهد.";
    if (error.status === 409) return "اطلاعات تغییر کرده یا یکی از گزینه‌ها دیگر فعال نیست؛ صفحه را تازه‌سازی و دوباره بررسی کنید.";
    if (error.status === 400 || error.status === 422) return "اطلاعات وسیله و واحد حمل را بررسی کنید.";
  }
  return "دریافت یا ذخیره اطلاعات اجرای حمل ممکن نشد.";
};

function ExecutionForm({
  options,
  initial,
  submitLabel,
  pending,
  showReason = false,
  onSubmit,
}: {
  options: TransportExecutionOptions;
  initial?: FormState;
  submitLabel: string;
  pending: boolean;
  showReason?: boolean;
  onSubmit: (form: FormState) => Promise<void>;
}) {
  const [form, setForm] = useState<FormState>(() => initial || emptyForm());
  const setEquipment = (index: number, patch: Partial<EquipmentDraft>) => {
    setForm((current) => ({
      ...current,
      equipment: current.equipment.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    }));
  };
  return <div className="mt-3 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2">
    <label className="space-y-1 text-sm"><span>نوع وسیله حمل (الزامی)</span><select aria-label="نوع وسیله حمل" className="min-h-11 w-full rounded-md border bg-white px-3" value={form.transport_means_type_public_id} onChange={(event) => setForm({ ...form, transport_means_type_public_id: event.target.value })}><option value="">انتخاب کنید</option>{options.means.map((item) => <option key={item.public_id} value={item.public_id}>{item.fa_name}</option>)}</select></label>
    <label className="space-y-1 text-sm"><span>شرکت حمل</span><select aria-label="شرکت حمل" className="min-h-11 w-full rounded-md border bg-white px-3" value={form.carrier_customer_id} onChange={(event) => setForm({ ...form, carrier_customer_id: event.target.value })}><option value="">فعلاً مشخص نیست</option>{options.carriers.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    <label className="space-y-1 text-sm"><span>شناسه وسیله</span><Input aria-label="شناسه وسیله حمل" placeholder="برای نمونه پلاک، شماره قطار یا سفر" value={form.means_identifier} onChange={(event) => setForm({ ...form, means_identifier: event.target.value })} /></label>
    <label className="space-y-1 text-sm"><span>توضیح وسیله</span><Input aria-label="توضیح وسیله حمل" placeholder="اختیاری" value={form.means_details} onChange={(event) => setForm({ ...form, means_details: event.target.value })} /></label>
    <label className="space-y-1 text-sm"><span>نام راننده / مسئول حرکت</span><Input aria-label="نام راننده" placeholder="اختیاری و فقط برای همین اجرا" value={form.driver_name} onChange={(event) => setForm({ ...form, driver_name: event.target.value })} /></label>
    <label className="space-y-1 text-sm"><span>راه ارتباطی</span><Input aria-label="راه ارتباطی راننده" placeholder="اختیاری" value={form.driver_contact} onChange={(event) => setForm({ ...form, driver_contact: event.target.value })} /></label>
    <div className="space-y-2 sm:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-medium">واحد / ظرف حمل</span><Button type="button" variant="outline" onClick={() => setForm({ ...form, equipment: [...form.equipment, { type_public_id: "", identifier: "", details: "" }] })}>افزودن واحد یا ظرف</Button></div>
      {!form.equipment.length && <p className="text-xs text-slate-600">در صورت نامشخص‌بودن، این بخش را می‌توان بعداً تکمیل کرد.</p>}
      {form.equipment.map((item, index) => <div key={index} className="grid gap-2 rounded-lg border bg-white p-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
        <select aria-label={`نوع واحد حمل ${index + 1}`} className="min-h-11 rounded-md border px-3" value={item.type_public_id} onChange={(event) => setEquipment(index, { type_public_id: event.target.value })}><option value="">نوع واحد / ظرف</option>{options.equipment.map((option) => <option key={option.public_id} value={option.public_id}>{option.fa_name}</option>)}</select>
        <Input aria-label={`شناسه واحد حمل ${index + 1}`} placeholder="شماره یا شناسه" value={item.identifier} onChange={(event) => setEquipment(index, { identifier: event.target.value })} />
        <Input aria-label={`توضیح واحد حمل ${index + 1}`} placeholder="توضیح اختیاری" value={item.details} onChange={(event) => setEquipment(index, { details: event.target.value })} />
        <Button type="button" variant="ghost" onClick={() => setForm({ ...form, equipment: form.equipment.filter((_, itemIndex) => itemIndex !== index) })}>حذف</Button>
      </div>)}
    </div>
    {showReason && <label className="space-y-1 text-sm sm:col-span-2"><span>دلیل تغییر (اختیاری)</span><Input aria-label="دلیل تغییر اجرای حمل" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label>}
    <div className="sm:col-span-2"><Button disabled={pending || !form.transport_means_type_public_id || form.equipment.some((item) => !item.type_public_id)} onClick={() => void onSubmit(form)}>{pending ? "در حال ذخیره…" : submitLabel}</Button></div>
  </div>;
}

function TransportChain({ revision }: { revision: TransportExecutionRevision }) {
  return <div className="mt-3 rounded-xl bg-slate-50 p-3 text-center">
    <p className="text-xs text-slate-500">شرکت حمل</p><p className="font-semibold">{revision.carrier?.label || "فعلاً مشخص نیست"}</p>
    <p aria-hidden="true" className="py-1 text-slate-400">↓</p>
    <p className="text-xs text-slate-500">وسیله حمل</p><p className="font-semibold">{revision.means.fa_name}{revision.means_identifier ? ` · ${revision.means_identifier}` : ""}</p>
    {revision.equipment.map((item) => <div key={`${revision.public_id}-${item.sequence}`}><p aria-hidden="true" className="py-1 text-slate-400">↓</p><p className="text-xs text-slate-500">واحد / ظرف حمل {item.sequence}</p><p className="font-semibold">{item.type.fa_name}{item.identifier ? ` · ${item.identifier}` : ""}</p></div>)}
  </div>;
}

function ExecutionCard({
  execution,
  options,
  pending,
  canManage,
  onRevise,
}: {
  execution: RouteStageTransportExecution;
  options: TransportExecutionOptions;
  pending: boolean;
  canManage: boolean;
  onRevise: (form: FormState) => Promise<void>;
}) {
  const previous = execution.history.filter((item) => item.revision_number !== execution.current.revision_number);
  return <article className="rounded-xl border border-slate-200 bg-white p-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><h4 className="font-bold">اجرای حمل {execution.current.revision_number > 1 ? `· نسخه ${execution.current.revision_number}` : ""}</h4><span className="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-800">اطلاعات جاری</span></div>
    <TransportChain revision={execution.current} />
    {execution.current.incomplete_fields.length > 0 && <p role="status" className="mt-3 rounded-lg bg-slate-100 p-2 text-sm text-slate-700">برخی جزئیات اجرایی هنوز مشخص نیست و بعداً قابل تکمیل است. این وضعیت، مسئله عملیاتی محسوب نمی‌شود.</p>}
    {(execution.current.means_details || execution.current.driver.name || execution.current.driver.contact) && <p className="mt-2 text-sm text-slate-600">{execution.current.means_details || ""}{execution.current.driver.name ? ` · مسئول حرکت: ${execution.current.driver.name}` : ""}{execution.current.driver.contact ? ` · ${execution.current.driver.contact}` : ""}</p>}
    {execution.current.reason && <p className="mt-2 text-sm text-slate-600">دلیل آخرین تغییر: {execution.current.reason}</p>}
    {previous.length > 0 && <details className="mt-3 rounded-lg border p-3"><summary className="cursor-pointer font-medium">سابقه تغییرات ({previous.length})</summary><div className="mt-3 space-y-3">{previous.map((revision) => <div key={revision.public_id} className="rounded-lg border border-dashed p-3"><p className="text-sm font-semibold">نسخه {revision.revision_number}{revision.reason ? ` · ${revision.reason}` : ""}</p><TransportChain revision={revision} /></div>)}</div></details>}
    {canManage && <details className="mt-3"><summary className="cursor-pointer font-medium text-blue-700">تکمیل یا تغییر اطلاعات</summary><ExecutionForm options={options} initial={fromRevision(execution.current)} submitLabel="ثبت نسخه تازه" pending={pending} showReason onSubmit={onRevise} /></details>}
  </article>;
}

export default function RouteStageTransportExecutionSection({ shipmentId, planId }: { shipmentId: string; planId: number }) {
  const [data, setData] = useState<RouteStageTransportExecutionList>();
  const [options, setOptions] = useState<TransportExecutionOptions>({ means: [], equipment: [], carriers: [] });
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    try {
      setError("");
      const [executions, choices] = await Promise.all([
        listRouteStageTransportExecutions(shipmentId, planId),
        getTransportExecutionOptions(shipmentId),
      ]);
      setData(executions.data);
      setOptions(choices.data);
    } catch (caught) {
      setError(messageFor(caught));
    }
  }, [shipmentId, planId]);
  useEffect(() => { void load(); }, [load]);

  const create = async (stageId: number, form: FormState) => {
    try {
      setPending(`create-${stageId}`); setError(""); setNotice("");
      await createRouteStageTransportExecution(shipmentId, planId, stageId, toPayload(form), crypto.randomUUID());
      setNotice("اجرای حمل برای این بخش مسیر ثبت شد.");
      await load();
    } catch (caught) { setError(messageFor(caught)); }
    finally { setPending(""); }
  };
  const revise = async (execution: RouteStageTransportExecution, form: FormState) => {
    try {
      setPending(execution.execution_public_id); setError(""); setNotice("");
      await reviseRouteStageTransportExecution(shipmentId, planId, execution.execution_public_id, toPayload(form, execution.unit_version), crypto.randomUUID());
      setNotice("نسخه تازه اطلاعات اجرای حمل ثبت شد و سابقه قبلی محفوظ ماند.");
      await load();
    } catch (caught) { setError(messageFor(caught)); await load(); }
    finally { setPending(""); }
  };

  return <Card className="border-slate-200 shadow-sm" dir="rtl">
    <CardHeader><CardTitle>وسیله و شرکت حمل هر بخش مسیر</CardTitle><p className="text-sm text-slate-600">برای هر بخش مسیر می‌توان یک یا چند اجرای مستقل ثبت کرد. کالا در این بخش تخصیص داده نمی‌شود.</p></CardHeader>
    <CardContent className="space-y-4">
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">{error} <Button variant="link" onClick={() => void load()}>تلاش دوباره</Button></p>}
      {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-emerald-800">{notice}</p>}
      {!data && !error && <p role="status">در حال دریافت اجرای حمل…</p>}
      {data?.stages.map((stage) => <section key={stage.id} aria-labelledby={`transport-stage-${stage.id}`} className="rounded-xl border border-slate-200 p-3 sm:p-4">
        <h3 id={`transport-stage-${stage.id}`} className="font-bold">بخش مسیر {stage.sequence_number}{stage.branch_label ? ` · ${stage.branch_label}` : ""}</h3>
        <p className="mt-1 text-sm text-slate-600">{stage.origin.display_name || "مبدأ ثبت نشده"} ← {stage.destination.display_name || "مقصد ثبت نشده"}</p>
        <div className="mt-3 grid gap-3 xl:grid-cols-2">{stage.executions.map((execution) => <ExecutionCard key={execution.public_id} execution={execution} options={options} pending={pending === execution.execution_public_id} canManage={data.can_manage} onRevise={(form) => revise(execution, form)} />)}</div>
        {!stage.executions.length && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">هنوز اجرای حملی برای این بخش ثبت نشده است.</p>}
        {data.can_manage && data.plan.is_active && <details className="mt-3"><summary className="cursor-pointer font-medium text-blue-700">افزودن اجرای حمل دیگر</summary><ExecutionForm key={`${stage.id}-${stage.executions.length}`} options={options} submitLabel="ثبت اجرای حمل" pending={pending === `create-${stage.id}`} onSubmit={(form) => create(stage.id, form)} /></details>}
      </section>)}
    </CardContent>
  </Card>;
}
