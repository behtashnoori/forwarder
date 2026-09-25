import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  deleteShipmentDocument,
  downloadShipmentDocument,
  changeShipmentDocumentContext,
  fetchDocumentContextOptions,
  fetchShipmentDocumentContextHistory,
  fetchShipmentDocuments,
  uploadShipmentDocument,
  ApiError,
  type DocumentContextOptions,
  type ShipmentDocumentContext,
  type ShipmentDocument,
} from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

const stateLabel = (value: string) => ({
  active: "فعال", superseded: "جایگزین‌شده", deleted: "باطل‌شده",
}[value] || value);
const contextLabel = (value?: string) => ({
  SHIPMENT: "پرونده حمل", CARGO: "کالای مشتری", ROUTE_LEG: "مرحله مسیر", EXECUTION_UNIT: "اجرای حمل", DELIVERY: "تحویل کالا",
}[value || ""] || "زمینه ثبت نشده");
const visibilityLabel = (value?: string) => ({
  INTERNAL: "فقط داخلی", CARGO_OWNER: "مشتری صاحب کالا، پس از احراز مجوز هویتی",
  EXPLICIT_SHARED: "مشتریان انتخاب‌شده",
}[value || ""] || "فقط دسترسی داخلی پیشین");
const optionKey = (value: ShipmentDocumentContext["type"]) => ({
  SHIPMENT: "shipment", CARGO: "cargo", ROUTE_LEG: "route_leg", EXECUTION_UNIT: "execution_unit", DELIVERY: "delivery",
} as const)[value];

function ContextEditor({ row, shipmentPublicId, options, onSaved }: {
  row: ShipmentDocument; shipmentPublicId: string; options: DocumentContextOptions; onSaved: () => Promise<void>;
}) {
  const current = row.context!;
  const [type, setType] = useState<ShipmentDocumentContext["type"]>(current.type);
  const [target, setTarget] = useState(current.target_public_id || "");
  const [visibility, setVisibility] = useState<ShipmentDocumentContext["visibility"]>(current.visibility);
  const [audiences, setAudiences] = useState<string[]>(current.audiences);
  const [reason, setReason] = useState("");
  const [history, setHistory] = useState<Array<{ action: string; recorded_at: string; reason: string | null }>>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const targets = options[optionKey(type)] || [];
  const save = async () => {
    setBusy(true); setError("");
    try {
      await changeShipmentDocumentContext(shipmentPublicId, row.public_id, {
        expected_version: current.version, context_type: type,
        context_target_public_id: type === "SHIPMENT" ? shipmentPublicId : target,
        visibility, audience_public_ids: visibility === "EXPLICIT_SHARED" ? audiences : [],
        reason: reason.trim() || undefined,
      });
      await onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "اصلاح سند انجام نشد");
    } finally { setBusy(false); }
  };
  return <details className="mt-3 rounded border p-3 text-sm">
    <summary className="cursor-pointer">اصلاح زمینه یا دسترسی · تاریخچه</summary>
    <div className="mt-3 grid gap-2 sm:grid-cols-2">
      <label>این سند مربوط به چیست؟
        <select aria-label={`Document context ${row.public_id}`} className="mt-1 w-full rounded border p-2" value={type}
          onChange={(event) => {
            const next = event.target.value as ShipmentDocumentContext["type"];
            setType(next); setTarget(options[optionKey(next)]?.[0]?.id || ""); setVisibility("INTERNAL"); setAudiences([]);
          }}>
          <option value="SHIPMENT">پرونده حمل</option><option value="CARGO">کالای مشتری</option>
          <option value="ROUTE_LEG">مرحله مسیر</option><option value="EXECUTION_UNIT">اجرای حمل</option><option value="DELIVERY">تحویل کالا</option>
        </select>
      </label>
      <label>مورد مرتبط
        <select aria-label={`Document target ${row.public_id}`} className="mt-1 w-full rounded border p-2" value={target}
          onChange={(event) => setTarget(event.target.value)}>
          {targets.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      </label>
      <label>چه کسانی می‌توانند ببینند؟
        <select aria-label={`Document visibility ${row.public_id}`} className="mt-1 w-full rounded border p-2" value={visibility}
          onChange={(event) => { setVisibility(event.target.value as ShipmentDocumentContext["visibility"]); setAudiences([]); }}>
          <option value="INTERNAL">فقط داخلی</option>
          {["CARGO", "DELIVERY"].includes(type) && <option value="CARGO_OWNER">مشتری صاحب کالا، پس از احراز مجوز هویتی</option>}
          {!["CARGO", "DELIVERY"].includes(type) && <option value="EXPLICIT_SHARED">مشتریان انتخاب‌شده</option>}
        </select>
      </label>
      {visibility === "EXPLICIT_SHARED" && <label>مخاطبان مشخص
        <select aria-label={`Document audiences ${row.public_id}`} className="mt-1 w-full rounded border p-2" multiple
          value={audiences} onChange={(event) => setAudiences(Array.from(event.target.selectedOptions, item => item.value))}>
          {options.audience.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      </label>}
      <Input aria-label={`Document change reason ${row.public_id}`} placeholder="دلیل اصلاح (اختیاری)" value={reason}
        onChange={(event) => setReason(event.target.value)} />
      <Button disabled={busy || !target || (visibility === "EXPLICIT_SHARED" && !audiences.length)} onClick={() => void save()}>
        ثبت اصلاح با تاریخچه
      </Button>
    </div>
    {error && <p role="alert" className="mt-2 text-red-700">{error}</p>}
    <Button variant="link" onClick={async () => {
      try { setHistory((await fetchShipmentDocumentContextHistory(shipmentPublicId, row.public_id)).data); }
      catch (caught) { setError(caught instanceof Error ? caught.message : "تاریخچه دریافت نشد"); }
    }}>نمایش تاریخچه زمینه و دسترسی</Button>
    {history.map((entry, index) => <p key={index}>{entry.action} · {formatDualCalendarInstant(entry.recorded_at, "fa-IR")} {entry.reason || ""}</p>)}
  </details>;
}

export default function ShipmentDocuments({ shipmentPublicId }: { shipmentPublicId: string }) {
  const [rows, setRows] = useState<ShipmentDocument[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [options, setOptions] = useState<DocumentContextOptions | null>(null);
  const [contextType, setContextType] = useState<ShipmentDocumentContext["type"]>("SHIPMENT");
  const [target, setTarget] = useState(shipmentPublicId);
  const [visibility, setVisibility] = useState<ShipmentDocumentContext["visibility"]>("INTERNAL");
  const [audiences, setAudiences] = useState<string[]>([]);
  const [outcomes, setOutcomes] = useState<string[]>([]);
  const [replaceId, setReplaceId] = useState<string | null>(null);
  const uploadKeys = useRef(new WeakMap<File, string>());
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const payload = await fetchShipmentDocuments(shipmentPublicId);
      setRows(payload.data);
      setCanManage(payload.can_manage_documents);
      if (payload.can_manage_documents) setOptions((await fetchDocumentContextOptions(shipmentPublicId)).data);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "اسناد دریافت نشدند");
    } finally {
      setLoading(false);
    }
  }, [shipmentPublicId]);

  useEffect(() => { setOptions(null); void load(); }, [load]);

  const upload = async () => {
    if (!files.length || !title.trim()) return;
    try {
      setBusy(true);
      setError("");
      const failed: File[] = [];
      const results: string[] = [];
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        form.append("title", title.trim());
        if (description.trim()) form.append("description", description.trim());
        form.append("context_type", contextType);
        form.append("context_target_public_id", contextType === "SHIPMENT" ? shipmentPublicId : target);
        form.append("visibility", visibility);
        if (replaceId) form.append("replaces_document_public_id", replaceId);
        if (visibility === "EXPLICIT_SHARED") audiences.forEach((id) => form.append("audience_public_ids", id));
        try {
          let key = uploadKeys.current.get(file);
          if (!key) { key = crypto.randomUUID(); uploadKeys.current.set(file, key); }
          await uploadShipmentDocument(shipmentPublicId, form, key);
          uploadKeys.current.delete(file);
          results.push(`${file.name}: ثبت شد`);
        } catch (caught) {
          if (caught instanceof ApiError && caught.status < 500) uploadKeys.current.delete(file);
          failed.push(file);
          results.push(`${file.name}: ناموفق — ${caught instanceof Error ? caught.message : "خطا"}`);
        }
      }
      setOutcomes(results);
      setFiles(failed);
      if (!failed.length) { setTitle(""); setDescription(""); setReplaceId(null); }
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "بارگذاری ناموفق بود");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (row: ShipmentDocument) => {
    const reason = window.prompt("دلیل ابطال سند را وارد کنید:");
    if (!reason?.trim()) return;
    try {
      setBusy(true);
      await deleteShipmentDocument(shipmentPublicId, row.public_id, reason.trim());
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ابطال سند ناموفق بود");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card dir="rtl">
      <CardHeader>
        <CardTitle>اسناد و مدارک حمل</CardTitle>
        <p className="text-sm text-muted-foreground">همه اسناد مجاز محموله—چه متعلق به درخواست و چه خود محموله—در این بخش یکپارچه نمایش داده می‌شوند. اتصال به شماره مرجع اختیاری است.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
        {outcomes.length > 0 && <div role="status" className="rounded border p-3 text-sm">
          <p>نتیجه هر فایل؛ موارد ناموفق برای تلاش دوباره باقی مانده‌اند:</p>
          {outcomes.map((item, index) => <p key={index}>{item}</p>)}
        </div>}
        {canManage ? (
          <div className="grid gap-2 rounded border p-3 sm:grid-cols-2">
            {!options && <p className="sm:col-span-2 text-sm text-slate-600">گزینه‌های زمینه و دسترسی هنوز آماده نیستند.</p>}
            {replaceId && <p className="sm:col-span-2 rounded bg-amber-50 p-2 text-sm">جایگزینی نسخه انتخاب‌شده؛ نسخه جدید ابتدا فقط داخلی است.
              <Button variant="link" onClick={() => setReplaceId(null)}>لغو جایگزینی</Button>
            </p>}
            <Input aria-label="نوع یا دسته تجاری سند" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="نوع یا دسته تجاری سند" />
            <Input aria-label="توضیح سند" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="توضیح (اختیاری)" />
            {options && <>
              <label className="text-sm">این سند مربوط به چیست؟
                <select aria-label="Document upload context" className="mt-1 w-full rounded border p-2" value={contextType}
                  onChange={(event) => {
                    const next = event.target.value as ShipmentDocumentContext["type"];
                    setContextType(next); setTarget(options[optionKey(next)]?.[0]?.id || "");
                    setVisibility("INTERNAL"); setAudiences([]);
                  }}>
                  <option value="SHIPMENT">پرونده حمل</option><option value="CARGO">کالای مشتری</option>
                  <option value="ROUTE_LEG">مرحله مسیر</option><option value="EXECUTION_UNIT">اجرای حمل</option><option value="DELIVERY">تحویل کالا</option>
                </select>
              </label>
              <label className="text-sm">مورد مرتبط
                <select aria-label="Document upload target" className="mt-1 w-full rounded border p-2" value={target}
                  onChange={(event) => setTarget(event.target.value)}>
                  {(options[optionKey(contextType)] || []).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </label>
              <label className="text-sm">چه کسانی می‌توانند ببینند؟
                <select aria-label="Document upload visibility" className="mt-1 w-full rounded border p-2" value={visibility}
                  onChange={(event) => { setVisibility(event.target.value as ShipmentDocumentContext["visibility"]); setAudiences([]); }}>
                  <option value="INTERNAL">فقط داخلی</option>
                  {["CARGO", "DELIVERY"].includes(contextType) && <option value="CARGO_OWNER">مشتری صاحب کالا، پس از احراز مجوز هویتی</option>}
                  {!["CARGO", "DELIVERY"].includes(contextType) && <option value="EXPLICIT_SHARED">مشتریان انتخاب‌شده</option>}
                </select>
              </label>
              {visibility === "EXPLICIT_SHARED" && <label className="text-sm">مخاطبان مشخص
                <select aria-label="Document upload audiences" className="mt-1 w-full rounded border p-2" multiple value={audiences}
                  onChange={(event) => setAudiences(Array.from(event.target.selectedOptions, item => item.value))}>
                  {options.audience.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </label>}
            </>}
            <Input className="sm:col-span-2" aria-label="انتخاب فایل سند" type="file" multiple={!replaceId} accept=".pdf,.jpg,.jpeg,.png,.webp,.docx,.xlsx"
              onChange={(event) => setFiles(Array.from(event.target.files || []))} />
            <Button className="sm:col-span-2" disabled={busy || !options || !files.length || (Boolean(replaceId) && files.length !== 1) || !title.trim() || !target || (visibility === "EXPLICIT_SHARED" && !audiences.length)}
              onClick={() => void upload()}><Upload className="ms-2 h-4 w-4" />{busy ? "در حال بارگذاری…" : files.length > 1 ? `بارگذاری ${files.length} فایل` : "بارگذاری سند"}</Button>
          </div>
        ) : (
          <p className="rounded border border-dashed p-3 text-sm text-slate-600">دسترسی شما به این بخش فقط خواندنی است.</p>
        )}
        {loading ? <p role="status">در حال دریافت اسناد…</p> : !rows.length ? (
          <p className="rounded border border-dashed p-4">هنوز سندی برای این محموله ثبت نشده است.</p>
        ) : (
          <div className="space-y-3">
            {rows.map((row) => (
              <article key={row.public_id} className="min-w-0 rounded border p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0"><strong>{row.business_document_type}</strong><p dir="ltr" className="break-all text-sm">{row.filename}</p></div>
                  <span className="rounded bg-slate-100 px-2 py-1 text-xs">{stateLabel(row.lifecycle_state)}</span>
                </div>
                <div className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
                  <p>نسخه {row.version}</p><p>مالک/منشأ: {row.owner === "REQUEST" ? "درخواست" : "محموله"}</p>
                  <p>مربوط به: {contextLabel(row.context?.type)}</p><p>چه کسانی می‌توانند ببینند؟ {visibilityLabel(row.context?.visibility)}</p>
                  <p>زمان ثبت: <time dateTime={row.recorded_at} dir="auto">{formatDualCalendarInstant(row.recorded_at, "fa-IR")}</time></p><p>ثبت‌کننده: {row.actor || "ثبت نشده"}</p>
                  <p>مرجع مرتبط: {row.references.length ? row.references.map((item) => `${item.type}: ${item.display_value}`).join("، ") : "ندارد"}</p>
                  <p>الزام سند مرتبط: {row.requirements.length ? row.requirements.map((item) => item.title).join("، ") : "ندارد"}</p>
                </div>
                {row.description && <p className="mt-2 text-sm text-slate-600">{row.description}</p>}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => void downloadShipmentDocument(shipmentPublicId, row.public_id, row.filename)}><Download className="ms-2 h-4 w-4" />دریافت</Button>
                  {canManage && row.owner === "SHIPMENT" && row.lifecycle_state === "active" && (
                    <>
                      <Button variant="outline" disabled={busy} onClick={() => {
                        setReplaceId(row.public_id); setTitle(row.business_document_type);
                        setContextType(row.context?.type || "SHIPMENT");
                        setTarget(row.context?.target_public_id || shipmentPublicId);
                        setVisibility("INTERNAL"); setAudiences([]);
                      }}>جایگزینی این نسخه</Button>
                      <Button variant="ghost" disabled={busy} onClick={() => void remove(row)}><Trash2 className="ms-2 h-4 w-4" />ابطال</Button>
                    </>
                  )}
                </div>
                {canManage && options && row.owner === "SHIPMENT" && row.lifecycle_state === "active" && row.context &&
                  <ContextEditor key={`${row.public_id}-${row.context.version}`} row={row} shipmentPublicId={shipmentPublicId} options={options} onSaved={load} />}
              </article>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
