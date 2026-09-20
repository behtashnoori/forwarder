import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, Download, History, RefreshCw, Repeat2, Trash2, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  deleteCaseDocument,
  downloadCaseDocument,
  fetchCaseDocuments,
  uploadCaseDocument,
  type CaseDocumentFile,
  type CaseDocumentRequirement,
  type CaseDocumentsPayload,
} from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

type QueueState = "queued" | "uploading" | "succeeded" | "failed" | "unknown";
type QueueItem = {
  id: string;
  requirement: CaseDocumentRequirement;
  file: File;
  state: QueueState;
  replacesFilePublicId?: string;
  error?: string;
  retryable?: boolean;
  inspected?: boolean;
};

const stateLabel: Record<QueueState, string> = {
  queued: "در صف",
  uploading: "در حال بارگذاری",
  succeeded: "موفق",
  failed: "ناموفق",
  unknown: "نتیجه نامشخص",
};

const isRetryableFailure = (error: ApiError) =>
  error.status >= 500 || error.code === "DOCUMENT_ACTIVE_LIMIT_REACHED";

export default function CaseDocumentsTab({ caseId }: { caseId: string }) {
  const [data, setData] = useState<CaseDocumentsPayload | null>(null);
  const [miscTitle, setMiscTitle] = useState("");
  const [miscDescription, setMiscDescription] = useState("");
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await fetchCaseDocuments(caseId));
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "دریافت اسناد ناموفق بود");
    }
  }, [caseId]);

  useEffect(() => { void load(); }, [load]);

  const updateQueue = (id: string, changes: Partial<QueueItem>) =>
    setQueue((items) => items.map((item) => item.id === id ? { ...item, ...changes } : item));

  const submitItem = async (item: QueueItem) => {
    updateQueue(item.id, { state: "uploading", error: undefined, inspected: false });
    const form = new FormData();
    form.append("file", item.file);
    try {
      await uploadCaseDocument(
        caseId,
        {
          definitionPublicId: item.requirement.definition_public_id,
          sourceDefinitionRevision: item.requirement.source_definition_revision,
        },
        form,
        item.replacesFilePublicId,
      );
      updateQueue(item.id, { state: "succeeded", retryable: false });
      await load();
    } catch (caught) {
      if (!(caught instanceof ApiError)) {
        updateQueue(item.id, {
          state: "unknown",
          retryable: false,
          error: "پاسخ قطعی دریافت نشد. برای جلوگیری از ثبت تکراری، دوباره ارسال نمی‌شود.",
        });
        return;
      }
      updateQueue(item.id, {
        state: "failed",
        retryable: isRetryableFailure(caught),
        error: caught.message,
      });
    }
  };

  const enqueue = async (
    requirement: CaseDocumentRequirement,
    files: File[],
    replacesFilePublicId?: string,
  ) => {
    if (!files.length) return;
    if (!replacesFilePublicId) {
      const remaining = requirement.max_active_file_count - requirement.current_files.length;
      if (files.length > remaining) {
        setError(`فقط ${remaining.toLocaleString("fa-IR")} جای خالی برای این سند باقی مانده است.`);
        return;
      }
    }
    setError("");
    const items = files.map((file, index): QueueItem => ({
      id: `${Date.now()}-${index}-${file.name}`,
      requirement,
      file,
      state: "queued",
      replacesFilePublicId,
    }));
    setQueue((current) => [...current, ...items]);
    for (const item of items) await submitItem(item);
  };

  const remove = async (file: CaseDocumentFile) => {
    const reason = window.prompt("دلیل غیرفعال‌سازی را وارد کنید");
    if (!reason?.trim()) return;
    try {
      await deleteCaseDocument(caseId, file.public_id, reason.trim());
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "غیرفعال‌سازی ناموفق بود");
    }
  };

  const inspectUnknown = async (id: string) => {
    await load();
    updateQueue(id, { inspected: true });
  };

  const queueAnnouncement = useMemo(
    () => queue.map((item) => `${item.file.name}: ${stateLabel[item.state]}`).join("؛ "),
    [queue],
  );

  if (!data) return <p role="status">{error || "در حال بارگذاری..."}</p>;

  const metadata = (file: CaseDocumentFile) => (
    <div className="grid gap-1 text-sm text-slate-600 sm:grid-cols-2">
      <span>نوع: {file.canonical_extension.toUpperCase()}</span>
      <span>حجم: {Math.ceil(file.file_size_bytes / 1024).toLocaleString("fa-IR")} KB</span>
      <span>زمان: <time dateTime={file.uploaded_at} dir="auto">{formatDualCalendarInstant(file.uploaded_at, "fa-IR")}</time></span>
      <span>ثبت‌کننده: {file.uploader_label || "ثبت نشده"}</span>
    </div>
  );

  const historyRows = (file: CaseDocumentFile) => (
    <details className="mt-3 rounded-lg border border-slate-200 p-3">
      <summary className="flex cursor-pointer items-center gap-2 font-medium">
        <History className="h-4 w-4" /> تاریخچه ({file.history?.length || 0})
      </summary>
      {!file.history?.length ? (
        <p className="mt-2 text-sm text-slate-500">نسخه پیشین ندارد.</p>
      ) : (
        <div className="mt-3 space-y-2">
          {file.history.map((prior) => (
            <div key={prior.public_id} className="rounded-lg bg-slate-50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="break-all">{prior.original_filename} · نسخه مسیر {prior.lineage_version}</span>
                <Button variant="ghost" size="sm" onClick={() => void downloadCaseDocument(caseId, prior.public_id, prior.original_filename)}>
                  <Download className="ms-2 h-4 w-4" /> دریافت
                </Button>
              </div>
              {metadata(prior)}
            </div>
          ))}
        </div>
      )}
    </details>
  );

  const currentFileCard = (requirement: CaseDocumentRequirement, file: CaseDocumentFile) => (
    <article key={file.public_id} className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="break-all font-semibold">{file.original_filename}</p>
          <div className="mt-1 flex flex-wrap gap-2">
            <Badge>جاری</Badge>
            <Badge variant="outline">نسخه مسیر {file.lineage_version}</Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => void downloadCaseDocument(caseId, file.public_id, file.original_filename)}>
            <Download className="ms-2 h-4 w-4" /> دریافت
          </Button>
          {data.can_manage_documents && (
            <>
              <label className="inline-flex cursor-pointer items-center rounded-md border px-3 py-2 text-sm font-medium">
                <Repeat2 className="ms-2 h-4 w-4" /> جایگزینی همین فایل
                <input
                  aria-label={`جایگزینی ${file.original_filename}`}
                  className="hidden"
                  type="file"
                  accept={`.${requirement.allowed_formats.join(",.")}`}
                  onChange={(event) => {
                    const selected = event.target.files?.[0];
                    event.target.value = "";
                    if (selected) void enqueue(requirement, [selected], file.public_id);
                  }}
                />
              </label>
              <Button variant="ghost" size="sm" onClick={() => void remove(file)}>
                <Trash2 className="ms-2 h-4 w-4" /> غیرفعال‌سازی
              </Button>
            </>
          )}
        </div>
      </div>
      <div className="mt-2">{metadata(file)}</div>
      {historyRows(file)}
    </article>
  );

  return (
    <div className="space-y-4" dir="rtl">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {Object.entries(data.summary).map(([key, value]) => (
          <Card key={key}><CardContent className="p-4"><b>{value}</b><p className="text-xs text-slate-500">{({
            total_requirements: "کل نیازمندی‌ها",
            required_requirements: "الزامی",
            uploaded_requirements: "دارای فایل جاری",
            missing_required_requirements: "الزامی بدون فایل جاری",
            miscellaneous_file_count: "سایر مستندات",
          } as Record<string, string>)[key]}</p></CardContent></Card>
        ))}
      </div>

      {data.summary.missing_required_requirements > 0 && (
        <p className="flex gap-2 rounded-xl bg-amber-50 p-3 text-amber-800"><AlertCircle /> موارد الزامی بدون فایل جاری هستند؛ این وضعیت به معنی رد یا عدم آمادگی عملیاتی نیست.</p>
      )}

      {queue.length > 0 && (
        <Card>
          <CardHeader><CardTitle>صف بارگذاری فایل‌ها</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {queue.map((item) => {
              const candidates = data.requirements
                .find((requirement) => requirement.definition_public_id === item.requirement.definition_public_id)
                ?.current_files.filter((file) => file.original_filename === item.file.name && file.file_size_bytes === item.file.size) || [];
              return (
                <div key={item.id} data-testid={`document-queue-${item.file.name}`} className="rounded-lg border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="break-all">{item.file.name}</span>
                    <Badge variant={item.state === "failed" || item.state === "unknown" ? "destructive" : "outline"}>{stateLabel[item.state]}</Badge>
                  </div>
                  {item.error && <p className="mt-1 text-sm text-red-700">{item.error}</p>}
                  <div className="mt-2 flex flex-wrap gap-2">
                    {item.state === "failed" && item.retryable && (
                      <Button size="sm" variant="outline" onClick={() => void submitItem(item)}><RefreshCw className="ms-2 h-4 w-4" /> تلاش دوباره فقط همین فایل</Button>
                    )}
                    {item.state === "unknown" && (
                      <Button size="sm" variant="outline" onClick={() => void inspectUnknown(item.id)}><RefreshCw className="ms-2 h-4 w-4" /> تازه‌سازی و بررسی</Button>
                    )}
                  </div>
                  {item.state === "unknown" && item.inspected && (
                    <p className="mt-2 text-sm text-amber-800">
                      {candidates.length
                        ? `${candidates.length.toLocaleString("fa-IR")} فایل مشابه در وضعیت جاری دیده شد؛ ارتباط قطعی با این تلاش قابل اثبات نیست.`
                        : "فایل مشابهی در فهرست جاری دیده نشد؛ نتیجه این تلاش همچنان نامشخص است."}
                    </p>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
      <p className="sr-only" aria-live="polite">{queueAnnouncement}</p>

      {data.requirements.map((requirement) => {
        const remaining = requirement.max_active_file_count - requirement.current_files.length;
        return (
          <Card key={`${requirement.definition_public_id}:${requirement.source_definition_revision}`}>
            <CardHeader>
              <CardTitle className="flex flex-wrap gap-2">
                {requirement.title}
                <Badge>{requirement.is_required ? "الزامی" : "اختیاری"}</Badge>
                <Badge variant="outline">{requirement.has_current_file ? "دارای فایل جاری" : "بدون فایل جاری"}</Badge>
              </CardTitle>
              {requirement.description && <p>{requirement.description}</p>}
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-slate-600">
                فرمت‌ها: {requirement.allowed_formats.join("، ")} · حداکثر {Math.ceil(requirement.max_file_size_bytes / 1048576)} MB · {requirement.current_files.length.toLocaleString("fa-IR")} از {requirement.max_active_file_count.toLocaleString("fa-IR")} فایل جاری
              </p>
              {requirement.current_files.length ? requirement.current_files.map((file) => currentFileCard(requirement, file)) : <p className="rounded-lg border border-dashed p-3 text-slate-500">هنوز فایل جاری ثبت نشده است.</p>}
              {data.can_manage_documents && (
                <label className={`inline-flex items-center gap-2 rounded-lg border p-2 ${remaining > 0 ? "cursor-pointer" : "cursor-not-allowed opacity-50"}`}>
                  <Upload className="h-4 w-4" /> افزودن فایل‌ها
                  <input
                    aria-label={`افزودن فایل‌ها برای ${requirement.title}`}
                    className="hidden"
                    type="file"
                    multiple
                    disabled={remaining <= 0}
                    accept={`.${requirement.allowed_formats.join(",.")}`}
                    onChange={(event) => {
                      const selected = Array.from(event.target.files || []);
                      event.target.value = "";
                      void enqueue(requirement, selected);
                    }}
                  />
                </label>
              )}
            </CardContent>
          </Card>
        );
      })}

      <Card>
        <CardHeader><CardTitle>سایر مستندات</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {data.can_manage_documents && (
            <>
              <Input placeholder="عنوان الزامی" value={miscTitle} onChange={(event) => setMiscTitle(event.target.value)} />
              <Textarea placeholder="توضیحات اختیاری" value={miscDescription} onChange={(event) => setMiscDescription(event.target.value)} />
              <input
                aria-label="انتخاب سایر مستندات"
                type="file"
                disabled={!miscTitle.trim()}
                onChange={async (event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (!file) return;
                  const form = new FormData();
                  form.append("file", file);
                  form.append("title", miscTitle);
                  form.append("description", miscDescription);
                  try {
                    await uploadCaseDocument(caseId, null, form);
                    setMiscTitle(""); setMiscDescription(""); await load();
                  } catch (caught) {
                    setError(caught instanceof Error ? caught.message : "بارگذاری ناموفق بود");
                  }
                }}
              />
            </>
          )}
          {data.miscellaneous.map((file) => (
            <div key={file.public_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 p-3">
              <span className="break-all">{file.original_filename} · {Math.ceil(file.file_size_bytes / 1024).toLocaleString("fa-IR")} KB</span>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => void downloadCaseDocument(caseId, file.public_id, file.original_filename)}><Download className="ms-2 h-4 w-4" /> دریافت</Button>
                {data.can_manage_documents && <Button variant="ghost" onClick={() => void remove(file)}><Trash2 className="ms-2 h-4 w-4" /> غیرفعال‌سازی</Button>}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}
    </div>
  );
}
