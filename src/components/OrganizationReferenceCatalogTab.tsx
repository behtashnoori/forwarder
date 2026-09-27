import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Building2, RefreshCw } from "lucide-react";
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
  { id: "transport-means-types", label: "وسایل حمل" },
  { id: "transport-equipment-types", label: "تجهیزات و واحدهای بار" },
];

const dimensionLabels: Record<string, string> = {
  COUNT: "تعداد",
  WEIGHT: "وزن",
  VOLUME: "حجم",
  LENGTH: "طول، ابعاد و فاصله",
  OTHER_GOVERNED: "سایر واحدهای تأییدشده",
};

function groups(resource: OrganizationReferenceCatalogResource, items: OrganizationReferenceCatalogItem[]) {
  if (resource !== "units-of-measure") return [{ label: "", items }];
  const order = ["COUNT", "WEIGHT", "VOLUME", "LENGTH", "OTHER_GOVERNED"];
  return order.map(dimension => ({
    label: dimensionLabels[dimension],
    items: items.filter(item => item.measurement_dimension === dimension),
  })).filter(group => group.items.length);
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
      const result = await fetchOrganizationReferenceCatalog(resource, { q: query || undefined, page, per_page: 100 });
      setItems(result.items);
      setPages(Math.max(result.pages ?? 1, 1));
    } catch (error) {
      setItems([]);
      if (error instanceof ApiError && error.status === 403) setDenied(true);
      else setLoadError(error instanceof Error ? error.message : "دریافت تعاریف سازمان انجام نشد.");
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
      setItems(current => current.map(row => row.public_id === item.public_id ? result.item : row));
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setActionError("وضعیت این تعریف هم‌زمان تغییر کرده است. فهرست تازه شد؛ دوباره بررسی کنید.");
        await load();
      } else if (error instanceof ApiError && error.status === 403) {
        setActionError("شما اجازهٔ تغییر تعاریف قابل استفادهٔ این سازمان را ندارید.");
      } else {
        setActionError("تغییر وضعیت تعریف انجام نشد. دوباره تلاش کنید.");
      }
    } finally {
      setPendingId(null);
    }
  };

  return <section className="space-y-4" dir="rtl" aria-labelledby="organization-reference-catalog-title">
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardHeader className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700"><Building2 className="h-5 w-5" /></span>
          <div><CardTitle id="organization-reference-catalog-title">تعاریف پایهٔ قابل استفادهٔ سازمان</CardTitle><p className="mt-1 text-sm font-medium text-slate-600">انتخاب از تعریف‌های استاندارد سیستم</p></div>
        </div>
        <p className="text-sm leading-7 text-muted-foreground">موارد مورد نیاز سازمان را فعال کنید تا کارشناسان بتوانند آن‌ها را در عملیات انتخاب کنند. غیرفعال کردن یک مورد، سابقه‌های ثبت‌شده را تغییر نمی‌دهد.</p>
      </CardHeader>
    </Card>

    <Input aria-label="جست‌وجوی تعاریف سازمان" className="max-w-xl rounded-xl bg-white" placeholder="جست‌وجو با نام" value={query} onChange={event => { setQuery(event.target.value); setPage(1); }} />

    <Tabs value={resource} onValueChange={value => { setResource(value as OrganizationReferenceCatalogResource); setPage(1); setActionError(""); }}>
      <TabsList className="flex h-auto flex-wrap justify-start rounded-2xl border border-slate-200 bg-white p-2">
        {resources.map(entry => <TabsTrigger key={entry.id} value={entry.id} className="rounded-xl">{entry.label}</TabsTrigger>)}
      </TabsList>
      {resources.map(entry => <TabsContent key={entry.id} value={entry.id} className="space-y-4">
        {actionError && <ErrorState message={actionError} />}
        {loading ? <LoadingState label="در حال دریافت تعریف‌ها…" /> : denied ? (
          <div role="alert" className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><AlertCircle className="mt-0.5 h-5 w-5 shrink-0" /><span>تنظیم این فهرست فقط برای مدیر همین سازمان مجاز است.</span></div>
        ) : loadError ? <ErrorState message="دریافت تعاریف سازمان انجام نشد. دوباره تلاش کنید." onRetry={() => void load()} /> : items.length === 0 ? (
          <EmptyState>در این گروه هنوز تعریف استانداردی برای انتخاب سازمان وجود ندارد.</EmptyState>
        ) : <div className="space-y-5">
          {groups(resource, items).map(group => <section key={group.label || "all"} className="space-y-3">
            {group.label && <h3 className="text-base font-semibold text-slate-900">{group.label}</h3>}
            <div className="grid gap-3 lg:grid-cols-2">
              {group.items.map(item => <Card key={item.public_id} data-testid={`organization-reference-${item.code}`} className="rounded-2xl border-slate-200 shadow-none">
                <CardContent className="space-y-4 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0"><h4 className="break-words font-semibold text-slate-950">{item.fa_name}{item.symbol ? <span dir="ltr" className="mr-2 text-sm font-normal text-slate-500">({item.symbol})</span> : null}</h4><p dir="ltr" className="mt-1 break-words text-left text-sm text-slate-500">{item.en_name}</p></div>
                    <Badge variant="outline" className="rounded-full border-blue-100 bg-blue-50 text-blue-700">تعریف استاندارد سیستم</Badge>
                  </div>
                  {item.description && <p className="text-sm leading-7 text-slate-700">{item.description}</p>}
                  <div className="rounded-xl bg-slate-50 p-3 text-sm"><span className="text-slate-500">برای سازمان شما: </span><strong className={item.organization_active ? "text-emerald-700" : "text-amber-800"}>{item.organization_active ? "فعال" : "هنوز فعال نشده"}</strong>{!item.central_active && <span className="mr-2 text-slate-500">(برای انتخاب جدید در دسترس نیست)</span>}</div>
                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
                    <details className="text-xs text-slate-500"><summary className="cursor-pointer">جزئیات فنی</summary><code dir="ltr" className="mt-2 block break-all">{item.code}</code></details>
                    {item.central_active ? <Button type="button" variant={item.organization_active ? "outline" : "default"} disabled={pendingId === item.public_id} onClick={() => void changeAvailability(item)}>
                      {pendingId === item.public_id && <RefreshCw className="ml-2 h-4 w-4 animate-spin" />}{item.organization_active ? "غیرفعال کردن برای سازمان" : "فعال کردن برای سازمان"}
                    </Button> : <span className="text-xs text-slate-500">فقط برای خواندن سابقه</span>}
                  </div>
                </CardContent>
              </Card>)}
            </div>
          </section>)}
        </div>}
        {!loading && !denied && !loadError && pages > 1 && <div className="flex items-center justify-end gap-2"><Button type="button" variant="outline" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>قبلی</Button><span className="text-sm text-slate-600">صفحه {page} از {pages}</span><Button type="button" variant="outline" disabled={page >= pages} onClick={() => setPage(value => value + 1)}>بعدی</Button></div>}
      </TabsContent>)}
    </Tabs>
  </section>;
}
