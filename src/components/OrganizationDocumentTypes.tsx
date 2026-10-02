import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchOrganizationDocumentTypes, saveOrganizationDocumentType, type OrganizationDocumentType } from "@/lib/api";

export default function OrganizationDocumentTypes() {
  const [items, setItems] = useState<OrganizationDocumentType[]>([]);
  const [nameFa, setNameFa] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<OrganizationDocumentType | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const attempt = useRef<{payload: string; key: string} | null>(null);
  const load = async () => {
    try { setItems((await fetchOrganizationDocumentTypes()).items); setError(""); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "انواع سند دریافت نشدند"); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);
  const clear = () => { setNameFa(""); setNameEn(""); setDescription(""); setEditing(null); attempt.current = null; };
  const save = async (row?: OrganizationDocumentType) => {
    setBusy(true); setError(""); setNotice("");
    const target = row || editing;
    const payload = row ? {is_active: !row.is_active, expected_revision: row.revision} : {
      name_fa: nameFa.trim(), name_en: nameEn.trim(), description: description.trim(),
      ...(editing ? {expected_revision: editing.revision} : {}),
    };
    const identity = JSON.stringify({target: target?.public_id, payload});
    if (attempt.current?.payload !== identity) attempt.current = {payload: identity, key: crypto.randomUUID()};
    try {
      await saveOrganizationDocumentType(payload, attempt.current.key, target?.public_id);
      clear(); setNotice(row ? "وضعیت نوع سند ذخیره شد؛ فایل‌های قبلی حفظ می‌شوند." : "نوع سند ذخیره شد.");
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "ذخیره نوع سند انجام نشد"); }
    finally { setBusy(false); }
  };
  return <section className="space-y-4 rounded-xl border bg-white p-4" dir="rtl" aria-label="انواع اسناد سازمان">
    <div><h2 className="text-lg font-bold">انواع اسناد سازمان</h2><p className="mt-1 text-sm text-slate-600">نوع سند را تعریف کنید تا کارشناس هنگام بارگذاری آن را انتخاب کند. الزامی یا اختیاری بودن، جداگانه در الزامات مستندات تنظیم می‌شود.</p></div>
    <form className="grid gap-3 sm:grid-cols-2" onSubmit={event => { event.preventDefault(); void save(); }}>
      <label className="text-sm">نام فارسی<Input required maxLength={200} value={nameFa} onChange={event => setNameFa(event.target.value)} /></label>
      <label className="text-sm">نام انگلیسی (اختیاری)<Input dir="ltr" maxLength={200} value={nameEn} onChange={event => setNameEn(event.target.value)} /></label>
      <label className="text-sm sm:col-span-2">توضیح کوتاه (اختیاری)<Input maxLength={1000} value={description} onChange={event => setDescription(event.target.value)} /></label>
      <div className="flex gap-2"><Button disabled={busy || !nameFa.trim()} type="submit">{busy ? "در حال ذخیره…" : editing ? "ذخیره نوع سند" : "افزودن نوع سند"}</Button>{editing && <Button type="button" variant="outline" onClick={clear}>انصراف از ویرایش</Button>}</div>
    </form>
    {error && <div role="alert" className="text-sm text-red-700">{error}<Button variant="link" onClick={() => void load()}>دریافت دوباره</Button></div>}
    {notice && <p role="status" className="text-sm text-green-800">{notice}</p>}
    {loading ? <p role="status">در حال دریافت انواع سند…</p> : <ul className="divide-y rounded border">{items.map(row => <li key={row.public_id} className="flex flex-wrap items-center justify-between gap-3 p-3">
      <div className="min-w-0"><strong>{row.name_fa}</strong>{row.name_en && <p className="text-sm text-slate-500"><bdi dir="ltr">{row.name_en}</bdi></p>}<p className="text-sm text-slate-500">{row.description}</p><details className="text-xs text-slate-500"><summary>شناسه سند</summary><code dir="ltr" className="break-all">{row.code}</code></details></div>
      <div className="flex flex-wrap items-center gap-2 text-sm"><span>{row.is_active ? "فعال" : "غیرفعال"}</span>{row.ownership === "SYSTEM" ? <span className="text-slate-500">تعریف سیستم</span> : <><Button disabled={busy} variant="outline" onClick={() => {setEditing(row); setNameFa(row.name_fa); setNameEn(row.name_en || ""); setDescription(row.description || "");}}>ویرایش</Button><Button disabled={busy} variant="outline" onClick={() => void save(row)}>{row.is_active ? "غیرفعال کردن" : "فعال کردن"}</Button></>}</div>
    </li>)}</ul>}
    {!loading && !error && !items.length && <p className="text-sm text-slate-500">هنوز نوع سندی تعریف نشده است.</p>}
  </section>;
}
