import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchOrganizationDocumentPolicy,
  updateOrganizationDocumentPolicy,
  type OrganizationDocumentPolicyItem,
  type OrganizationDocumentRequirementLevel,
} from "@/lib/api";

const levels: OrganizationDocumentRequirementLevel[] = ["REQUIRED", "OPTIONAL", "CONDITIONAL", "DISABLED"];
const labels: Record<OrganizationDocumentRequirementLevel, string> = {
  REQUIRED: "الزامی",
  OPTIONAL: "اختیاری",
  CONDITIONAL: "مشروط",
  DISABLED: "برای سازمان لازم نیست",
};
const scopeLabels = { all: "همهٔ حمل‌ها", domestic: "حمل داخلی", international: "حمل بین‌المللی" } as const;

export default function OrganizationDocumentPolicyTab() {
  const [items, setItems] = useState<OrganizationDocumentPolicyItem[]>([]);
  const [mode, setMode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [savedLevels, setSavedLevels] = useState<Record<string, OrganizationDocumentRequirementLevel>>({});
  const [saved, setSaved] = useState("");
  const load = async () => {
    try {
      setError("");
      const result = await fetchOrganizationDocumentPolicy();
      const rows = Array.isArray(result?.items) ? result.items : [];
      setItems(rows);
      setSavedLevels(Object.fromEntries(rows.map(item => [item.document_definition_public_id, item.requirement_level || "DISABLED"])));
      setMode(result?.mode || "");
    } catch {
      setError("دریافت الزامات مدارک انجام نشد. دوباره تلاش کنید.");
    }
  };
  useEffect(() => { void load(); }, []);
  const save = async (item: OrganizationDocumentPolicyItem, level: OrganizationDocumentRequirementLevel) => {
    try {
      setBusy(item.document_definition_public_id);
      setError("");
      await updateOrganizationDocumentPolicy(item.document_definition_public_id, {
        requirement_level: level,
        is_active: level !== "DISABLED",
        ...(typeof item.version === "number" ? { version: item.version } : {}),
      });
      setSaved(item.document_definition_public_id);
      await load();
    } catch {
      setError("ذخیرهٔ الزام مدرک انجام نشد. وضعیت تازه را بررسی و دوباره تلاش کنید.");
    } finally {
      setBusy("");
    }
  };

  return <div className="space-y-4" dir="rtl">
    <Card><CardHeader><CardTitle>مدارک مورد نیاز سازمان</CardTitle></CardHeader><CardContent className="space-y-2 text-sm leading-7">
      <p>برای هر نوع مدرک مشخص کنید در کدام نوع حمل لازم است و الزام آن برای سازمان چیست. این تنظیم از زمان ثبت، برای رکوردهای جدید به کار می‌رود و فایل‌های واقعی را ایجاد یا حذف نمی‌کند.</p>
      <p className="text-muted-foreground">«برای سازمان لازم نیست» با مدرک اختیاری یا مدرک ناقص یکسان نیست. کارشناس فایل و وضعیت آمادگی هر پرونده را جداگانه مدیریت می‌کند.</p>
      {mode === "COMPATIBILITY_FALLBACK" && <p className="rounded border border-amber-300 bg-amber-50 p-3 text-amber-900">هنوز سیاست صریح سازمان ثبت نشده است؛ تا اولین ثبت، رفتار سازگار قبلی اعمال می‌شود. این صفحه هیچ الزام پیش‌فرض تازه‌ای ایجاد نمی‌کند.</p>}
      {error && <p role="alert" className="text-red-700">{error}</p>}
    </CardContent></Card>
    <Card><CardContent className="overflow-auto p-4"><table className="w-full min-w-[640px] text-sm">
      <thead><tr><th className="p-2 text-right">چه مدرکی لازم است؟</th><th className="p-2 text-right">برای چه نوع حملی؟</th><th className="p-2 text-right">الزام سازمان</th><th className="p-2 text-right">عملیات</th></tr></thead>
      <tbody>{items.map(item => {
        const value = item.requirement_level || "DISABLED";
        const primaryName = item.name_fa || item.title || "مدرک بدون عنوان";
        const secondaryName = item.name_en || (item.name_fa && item.title !== item.name_fa ? item.title : null);
        return <tr className="border-t" key={item.document_definition_public_id}>
          <td className="p-2"><strong>{primaryName}</strong>{secondaryName && secondaryName !== primaryName && <p dir="ltr" className="mt-1 text-left text-xs text-slate-500">{secondaryName}</p>}{item.description && <p className="mt-1 text-xs text-slate-500">{item.description}</p>}<details className="mt-1 text-xs text-slate-400"><summary>جزئیات فنی</summary><code dir="ltr">{item.code}</code></details></td>
          <td className="p-2">{scopeLabels[item.applicability_scope]}</td>
          <td className="p-2"><select className="min-h-10 rounded border px-2" aria-label={`سطح الزام ${item.title || item.code}`} value={value} onChange={event => setItems(current => current.map(row => row.document_definition_public_id === item.document_definition_public_id ? { ...row, requirement_level: event.target.value as OrganizationDocumentRequirementLevel } : row))}>{levels.map(level => <option key={level} value={level}>{labels[level]}</option>)}</select></td>
          <td className="p-2"><Button variant={savedLevels[item.document_definition_public_id]===value?"outline":"default"} disabled={busy === item.document_definition_public_id || !item.global_is_active || savedLevels[item.document_definition_public_id]===value} onClick={() => void save(item, value)}>{busy === item.document_definition_public_id ? "در حال ذخیره…" : savedLevels[item.document_definition_public_id]===value ? saved===item.document_definition_public_id?"ذخیره شد":"بدون تغییر" : "ذخیره تغییر"}</Button></td>
        </tr>;
      })}</tbody>
    </table>{!items.length && !error && <p className="p-4 text-center text-slate-500">هنوز نوع مدرکی از سوی مدیر سیستم تعریف نشده است.</p>}</CardContent></Card>
  </div>;
}
