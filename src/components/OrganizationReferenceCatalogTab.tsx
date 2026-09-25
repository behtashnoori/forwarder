import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Building2, Database, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ApiError,
  fetchOrganizationReferenceCatalog,
  setOrganizationReferenceCatalogActive,
  type OrganizationReferenceCatalogItem,
  type OrganizationReferenceCatalogResource,
} from "@/lib/api";

const resources: Array<{ id: OrganizationReferenceCatalogResource; label: string }> = [
  { id: "cargo-types", label: "انواع کالا" },
  { id: "units-of-measure", label: "واحدهای اندازه‌گیری" },
  { id: "packaging-types", label: "انواع بسته‌بندی" },
  { id: "transport-means-types", label: "انواع وسیله حمل" },
  { id: "transport-equipment-types", label: "تجهیزات و واحدهای بار" },
];

function statusLabel(item: OrganizationReferenceCatalogItem) {
  if (!item.central_active) return "غیرفعال در مرجع مرکزی";
  if (!item.organization_active) return "غیرفعال برای سازمان";
  return item.selectable ? "فعال و قابل انتخاب" : "فعال، اما فعلاً غیرقابل انتخاب";
}

export default function OrganizationReferenceCatalogTab() {
  const [resource, setResource] = useState<OrganizationReferenceCatalogResource>("cargo-types");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<OrganizationReferenceCatalogItem[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [pendingId, setPendingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setDenied(false);
    setLoadError("");
    try {
      const result = await fetchOrganizationReferenceCatalog(resource, { q: query || undefined, page, per_page: 20 });
      setItems(result.items);
      setPages(Math.max(result.pages ?? 1, 1));
    } catch (error) {
      setItems([]);
      if (error instanceof ApiError && error.status === 403) {
        setDenied(true);
      } else {
        setLoadError(error instanceof Error ? error.message : "دریافت تعاریف سازمان انجام نشد.");
      }
    } finally {
      setLoading(false);
    }
  }, [page, query, resource]);

  useEffect(() => { void load(); }, [load]);

  const changeAvailability = async (item: OrganizationReferenceCatalogItem) => {
    if (!item.central_active) return;
    setPendingId(item.public_id);
    setActionError("");
    try {
      const result = await setOrganizationReferenceCatalogActive(resource, item, !item.organization_active);
      setItems((current) => current.map((row) => row.public_id === item.public_id ? result.item : row));
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setActionError("وضعیت این تعریف هم‌زمان تغییر کرده است. فهرست تازه شد؛ دوباره بررسی کنید.");
        await load();
      } else if (error instanceof ApiError && error.status === 403) {
        setActionError("شما اجازه تغییر تعاریف قابل استفاده این سازمان را ندارید.");
      } else {
        setActionError(error instanceof Error ? error.message : "تغییر وضعیت تعریف انجام نشد.");
      }
    } finally {
      setPendingId(null);
    }
  };

  return (
    <section className="space-y-4" dir="rtl" aria-labelledby="organization-reference-catalog-title">
      <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
        <CardHeader className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
              <Building2 className="h-5 w-5" />
            </span>
            <div>
              <CardTitle id="organization-reference-catalog-title">تعاریف پایه حمل</CardTitle>
              <p className="mt-1 text-sm font-medium text-slate-600">تعاریف قابل استفاده سازمان</p>
            </div>
          </div>
          <p className="text-sm leading-7 text-muted-foreground">
            از میان تعریف‌های تأییدشده سامانه، موارد قابل استفاده برای انتخاب‌های جدید سازمان را فعال کنید. غیرفعال‌سازی، سابقه‌های ثبت‌شده را تغییر نمی‌دهد.
          </p>
        </CardHeader>
      </Card>

      <Input
        aria-label="جست‌وجوی تعاریف سازمان"
        className="max-w-xl rounded-xl bg-white"
        placeholder="جست‌وجو با نام یا کد تعریف"
        value={query}
        onChange={(event) => { setQuery(event.target.value); setPage(1); }}
      />

      <Tabs value={resource} onValueChange={(value) => { setResource(value as OrganizationReferenceCatalogResource); setPage(1); setActionError(""); }}>
        <TabsList className="flex h-auto flex-wrap justify-start rounded-2xl border border-slate-200 bg-white p-2">
          {resources.map((entry) => <TabsTrigger key={entry.id} value={entry.id} className="rounded-xl">{entry.label}</TabsTrigger>)}
        </TabsList>
        {resources.map((entry) => (
          <TabsContent key={entry.id} value={entry.id} className="space-y-4">
            {actionError && <ErrorState message={actionError} />}
            {loading ? <LoadingState label="در حال دریافت تعاریف قابل استفاده سازمان…" /> : denied ? (
              <div role="alert" className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <span>دسترسی به تنظیم تعاریف سازمان فقط برای مدیر سازمان مجاز است.</span>
              </div>
            ) : loadError ? <ErrorState message="دریافت تعاریف سازمان انجام نشد. دوباره تلاش کنید." onRetry={() => void load()} /> : items.length === 0 ? (
              <EmptyState>در این گروه هنوز تعریف مرکزی تأییدشده‌ای برای انتخاب سازمان وجود ندارد.</EmptyState>
            ) : (
              <div className="grid gap-3 lg:grid-cols-2">
                {items.map((item) => (
                  <article key={item.public_id}>
                  <Card className="rounded-2xl border-slate-200 shadow-none">
                    <CardContent className="space-y-4 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="break-words font-semibold text-slate-950">{item.fa_name}</h3>
                          <p dir="ltr" className="mt-1 break-words text-left text-sm text-slate-500">{item.en_name}</p>
                        </div>
                        <Badge variant="outline" className="gap-1 rounded-full border-blue-100 bg-blue-50 text-blue-700">
                          <Database className="h-3.5 w-3.5" />مرکزی / سامانه
                        </Badge>
                      </div>
                      {item.description && <p className="text-sm leading-6 text-slate-600">{item.description}</p>}
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <Badge className={item.central_active ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-50" : "bg-slate-100 text-slate-600 hover:bg-slate-100"}>
                          {item.central_active ? "مرجع مرکزی فعال" : "مرجع مرکزی غیرفعال"}
                        </Badge>
                        <Badge className={item.organization_active ? "bg-blue-50 text-blue-700 hover:bg-blue-50" : "bg-amber-50 text-amber-800 hover:bg-amber-50"}>
                          {item.organization_active ? "فعال برای سازمان" : "غیرفعال برای سازمان"}
                        </Badge>
                        <span className="text-slate-500">{statusLabel(item)}</span>
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
                        <code dir="ltr" className="text-xs text-slate-500">{item.code}</code>
                        {item.central_active ? (
                          <Button
                            type="button"
                            variant={item.organization_active ? "outline" : "default"}
                            disabled={pendingId === item.public_id}
                            onClick={() => void changeAvailability(item)}
                          >
                            {pendingId === item.public_id && <RefreshCw className="ml-2 h-4 w-4 animate-spin" />}
                            {item.organization_active ? "غیرفعال‌سازی برای سازمان" : "فعال‌سازی برای سازمان"}
                          </Button>
                        ) : <span className="text-xs text-slate-500">فقط برای خواندن سابقه</span>}
                      </div>
                    </CardContent>
                  </Card>
                  </article>
                ))}
              </div>
            )}
            {!loading && !denied && !loadError && pages > 1 && (
              <div className="flex items-center justify-end gap-2">
                <Button type="button" variant="outline" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>قبلی</Button>
                <span className="text-sm text-slate-600">صفحه {page} از {pages}</span>
                <Button type="button" variant="outline" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>بعدی</Button>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}
