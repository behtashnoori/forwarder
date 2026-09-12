import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router";
import { Plus, Search, Users } from "lucide-react";
import { ApiError, createCustomer, fetchCustomers } from "@/lib/api";
import PageNav from "@/components/PageNav";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";

const emptyForm = { company_name: "", first_name: "", last_name: "", country: "Iran" };
const customerRoles = new Set(["admin", "crm_manager", "supervisor", "business_expert"]);

function actorCanManageCustomers() {
  try {
    const user = JSON.parse(localStorage.getItem("expert_user") || "{}");
    return user.authority !== "PLATFORM_ADMIN" && customerRoles.has(user.role);
  } catch { return false; }
}

export default function CustomerManagement() {
  const allowed = actorCanManageCustomers();
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [draftSearch, setDraftSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [duplicateAcknowledged, setDuplicateAcknowledged] = useState(false);
  const [duplicateMessage, setDuplicateMessage] = useState("");
  const customers = useQuery({ queryKey: ["tenant-customers", search], queryFn: () => fetchCustomers({ search: search || undefined, per_page: 100, sort_by: "company", sort_order: "asc" }), retry: false, enabled: allowed });
  const create = useMutation({
    mutationFn: () => createCustomer({ ...form, duplicate_acknowledged: duplicateAcknowledged }),
    onSuccess: async () => {
      setForm(emptyForm); setDuplicateAcknowledged(false); setDuplicateMessage(""); setOpen(false);
      await client.invalidateQueries({ queryKey: ["tenant-customers"] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === "DUPLICATE_CUSTOMER_CONFIRMATION_REQUIRED") {
        setDuplicateAcknowledged(true);
        setDuplicateMessage("مشتری مشابهی در همین سازمان پیدا شد. پس از بررسی، دوباره ایجاد را تایید کنید.");
      }
    },
  });
  const error = useMemo(() => create.error instanceof Error ? create.error.message : "ایجاد مشتری انجام نشد.", [create.error]);
  if (!allowed) return <Navigate to="/expert" replace />;
  if (customers.isLoading) return <main dir="rtl" className="min-h-screen bg-slate-50 p-6" aria-busy="true"><div className="mx-auto max-w-5xl h-40 animate-pulse rounded-xl bg-slate-200" /></main>;
  if (customers.isError) return <main dir="rtl" className="min-h-screen bg-slate-50 p-6"><Alert className="mx-auto max-w-2xl" variant="destructive"><AlertDescription>دریافت مشتریان سازمان ممکن نیست.</AlertDescription></Alert></main>;
  const rows = customers.data?.customers || [];
  return <main dir="rtl" className="min-h-screen bg-slate-50 p-4 sm:p-8"><div className="mx-auto max-w-5xl space-y-5">
    <PageNav backLabel="بازگشت" />
    <header className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-bold">مشتریان</h1><p className="text-sm text-muted-foreground">مشتریان فعال و غیرفعال همین سازمان</p></div><Button onClick={() => setOpen(true)}><Plus className="ml-2 h-4 w-4" />ایجاد مشتری</Button></header>
    <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); setSearch(draftSearch.trim()); }}><Input aria-label="جستجوی مشتری" value={draftSearch} onChange={(event) => setDraftSearch(event.target.value)} placeholder="جستجوی نام شرکت یا مخاطب" /><Button type="submit" variant="outline"><Search className="ml-2 h-4 w-4" />جستجو</Button></form>
    {!rows.length ? <Card><CardContent className="py-12 text-center"><Users className="mx-auto mb-3 h-10 w-10 text-muted-foreground" /><p>مشتری‌ای در این سازمان یافت نشد.</p></CardContent></Card> : <section className="grid gap-3">{rows.map((customer) => <Card key={customer.id}><CardHeader className="py-4"><CardTitle className="text-base">{customer.company_name || customer.name}</CardTitle><CardDescription>{customer.name}</CardDescription></CardHeader><CardContent className="pt-0 text-sm text-muted-foreground">{customer.status === "active" ? "فعال" : "غیرفعال"}</CardContent></Card>)}</section>}
    <Sheet open={open} onOpenChange={(value) => { setOpen(value); if (!value && !create.isPending) { setForm(emptyForm); setDuplicateAcknowledged(false); setDuplicateMessage(""); create.reset(); } }}><SheetContent side="left" className="overflow-y-auto" dir="rtl"><SheetHeader><SheetTitle>ایجاد مشتری</SheetTitle><SheetDescription>مشتری فقط در سازمان فعال شما ثبت می‌شود.</SheetDescription></SheetHeader><form className="mt-6 space-y-4" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
      <CustomerField label="نام شرکت" value={form.company_name} onChange={(company_name) => setForm({ ...form, company_name })} required />
      <CustomerField label="نام" value={form.first_name} onChange={(first_name) => setForm({ ...form, first_name })} required />
      <CustomerField label="نام خانوادگی" value={form.last_name} onChange={(last_name) => setForm({ ...form, last_name })} required />
      <CustomerField label="کشور" value={form.country} onChange={(country) => setForm({ ...form, country })} />
      {duplicateMessage && <Alert><AlertDescription>{duplicateMessage}</AlertDescription></Alert>}
      {create.isError && !duplicateMessage && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      <Button className="w-full" disabled={create.isPending}>{create.isPending ? "در حال ثبت…" : duplicateAcknowledged ? "تایید و ایجاد مشتری" : "ثبت مشتری"}</Button>
    </form></SheetContent></Sheet>
  </div></main>;
}

function CustomerField({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  const id = `customer-${label}`;
  return <div className="space-y-2"><Label htmlFor={id}>{label}{required ? " *" : ""}</Label><Input id={id} value={value} required={required} onChange={(event) => onChange(event.target.value)} /></div>;
}
