import { useCallback, useEffect, useMemo, useState } from "react";
import { Clock3, Edit3, Loader2, Plus, Power, PowerOff, Save, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import {
  createAdminSlaPolicy,
  disableAdminSlaPolicy,
  enableAdminSlaPolicy,
  fetchAdminSlaPolicies,
  type SlaPolicy,
  type SlaPolicyPayload,
  type SlaPriorityScope,
  type SlaShippingTypeScope,
  updateAdminSlaPolicy,
} from "@/lib/api";

type SlaPolicyFormState = {
  name: string;
  priority_scope: SlaPriorityScope;
  request_status_scope: string[];
  shipping_type_scope: Exclude<SlaShippingTypeScope, null>;
  transport_method_scope: string;
  response_time_minutes: string;
  near_deadline_threshold_minutes: string;
  sort_order: string;
  is_active: boolean;
};

const defaultFormState: SlaPolicyFormState = {
  name: "",
  priority_scope: "normal",
  request_status_scope: ["assigned", "in_progress"],
  shipping_type_scope: "all",
  transport_method_scope: "",
  response_time_minutes: "120",
  near_deadline_threshold_minutes: "60",
  sort_order: "100",
  is_active: true,
};

const priorityLabels: Record<SlaPriorityScope, string> = {
  all: "همه",
  low: "کم",
  normal: "عادی",
  high: "بالا",
  urgent: "فوری",
};

const statusOptions = [
  { value: "assigned", label: "ارجاع شده" },
  { value: "in_progress", label: "در حال پیگیری" },
];

const shippingLabels: Record<Exclude<SlaShippingTypeScope, null>, string> = {
  all: "همه",
  domestic: "داخلی",
  international: "بین‌المللی",
};

const numberFormatter = new Intl.NumberFormat("fa-IR");

const formatNumber = (value: number) => numberFormatter.format(value);

const formatMinutes = (value: number) => {
  if (value % 60 === 0) {
    return `${formatNumber(value / 60)} ساعت`;
  }
  return `${formatNumber(value)} دقیقه`;
};

const getToken = () => localStorage.getItem("expert_token") || "";

const SlaPoliciesTab = () => {
  const { toast } = useToast();
  const [policies, setPolicies] = useState<SlaPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [editingPolicy, setEditingPolicy] = useState<SlaPolicy | null>(null);
  const [formState, setFormState] = useState<SlaPolicyFormState>(defaultFormState);

  const editingLabel = editingPolicy ? "ویرایش قانون" : "ایجاد قانون";

  const loadPolicies = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      setFormError("نشست مدیریت معتبر نیست. دوباره وارد شوید.");
      return;
    }

    try {
      setLoading(true);
      const response = await fetchAdminSlaPolicies(token);
      setPolicies(response.sla_policies);
    } catch (error) {
      const message = error instanceof Error ? error.message : "خطا در دریافت قوانین SLA";
      toast({ title: "خطا", description: message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadPolicies();
  }, [loadPolicies]);

  const resetForm = () => {
    setEditingPolicy(null);
    setFormState(defaultFormState);
    setFormError("");
  };

  const startEdit = (policy: SlaPolicy) => {
    setEditingPolicy(policy);
    setFormState({
      name: policy.name,
      priority_scope: policy.priority_scope,
      request_status_scope: policy.request_status_scope.length ? policy.request_status_scope : ["assigned", "in_progress"],
      shipping_type_scope: policy.shipping_type_scope || "all",
      transport_method_scope: policy.transport_method_scope || "",
      response_time_minutes: String(policy.response_time_minutes),
      near_deadline_threshold_minutes: String(policy.near_deadline_threshold_minutes),
      sort_order: String(policy.sort_order),
      is_active: policy.is_active,
    });
    setFormError("");
  };

  const validateForm = (): SlaPolicyPayload | null => {
    const responseTime = Number(formState.response_time_minutes);
    const threshold = Number(formState.near_deadline_threshold_minutes);
    const sortOrder = Number(formState.sort_order || 100);

    if (!formState.name.trim()) {
      setFormError("نام قانون الزامی است.");
      return null;
    }
    if (!Number.isInteger(responseTime) || responseTime <= 0) {
      setFormError("مهلت پاسخ‌گویی باید عدد مثبت باشد.");
      return null;
    }
    if (!Number.isInteger(threshold) || threshold <= 0) {
      setFormError("آستانه نزدیک به مهلت باید عدد مثبت باشد.");
      return null;
    }
    if (threshold > responseTime) {
      setFormError("آستانه نزدیک به مهلت نباید بیشتر از مهلت پاسخ‌گویی باشد.");
      return null;
    }
    if (!Number.isInteger(sortOrder)) {
      setFormError("ترتیب اعمال باید عدد صحیح باشد.");
      return null;
    }
    if (!formState.request_status_scope.length) {
      setFormError("حداقل یک وضعیت مشمول را انتخاب کنید.");
      return null;
    }

    setFormError("");
    return {
      name: formState.name.trim(),
      priority_scope: formState.priority_scope,
      request_status_scope: formState.request_status_scope,
      shipping_type_scope: formState.shipping_type_scope,
      transport_method_scope: formState.transport_method_scope.trim() || null,
      response_time_minutes: responseTime,
      near_deadline_threshold_minutes: threshold,
      sort_order: sortOrder,
      is_active: formState.is_active,
    };
  };

  const handleSubmit = async () => {
    const payload = validateForm();
    const token = getToken();
    if (!payload || !token) return;

    try {
      setSaving(true);
      if (editingPolicy) {
        await updateAdminSlaPolicy(token, editingPolicy.id, payload);
        toast({ title: "قانون به‌روزرسانی شد" });
      } else {
        await createAdminSlaPolicy(token, payload);
        toast({ title: "قانون SLA ایجاد شد" });
      }
      resetForm();
      await loadPolicies();
    } catch (error) {
      const message = error instanceof Error ? error.message : "خطا در ذخیره قانون SLA";
      setFormError(message);
      toast({ title: "خطا", description: message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const togglePolicy = async (policy: SlaPolicy) => {
    const token = getToken();
    if (!token) return;

    try {
      if (policy.is_active) {
        await disableAdminSlaPolicy(token, policy.id);
        toast({ title: "قانون غیرفعال شد" });
      } else {
        await enableAdminSlaPolicy(token, policy.id);
        toast({ title: "قانون فعال شد" });
      }
      await loadPolicies();
    } catch (error) {
      const message = error instanceof Error ? error.message : "خطا در تغییر وضعیت قانون";
      toast({ title: "خطا", description: message, variant: "destructive" });
    }
  };

  const activeCount = useMemo(() => policies.filter((policy) => policy.is_active).length, [policies]);

  const toggleStatus = (status: string, checked: boolean) => {
    setFormState((current) => ({
      ...current,
      request_status_scope: checked
        ? Array.from(new Set([...current.request_status_scope, status]))
        : current.request_status_scope.filter((item) => item !== status),
    }));
  };

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <Badge className="mb-3 rounded-full bg-blue-50 px-3 py-1 text-blue-700 hover:bg-blue-50">
              SLA / مهلت پاسخ‌گویی
            </Badge>
            <h2 className="text-2xl font-bold text-slate-950">SLA / مهلت پاسخ‌گویی</h2>
            <p className="mt-2 text-sm leading-7 text-slate-500">
              تعریف و مدیریت قوانین زمان پاسخ‌گویی بر اساس اولویت درخواست‌ها
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="rounded-full bg-white px-3 py-2">
              {formatNumber(policies.length)} قانون
            </Badge>
            <Badge variant="outline" className="rounded-full border-emerald-200 bg-emerald-50 px-3 py-2 text-emerald-700">
              {formatNumber(activeCount)} فعال
            </Badge>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.45fr)]">
        <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="space-y-1 p-5 pb-3">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <Plus className="h-5 w-5 text-blue-600" />
              {editingLabel}
            </CardTitle>
            <p className="text-sm leading-6 text-slate-500">
              قوانین فعال هنگام ارجاع درخواست برای محاسبه مهلت پاسخ‌گویی استفاده می‌شوند.
            </p>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-2">
            {formError && (
              <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700">
                {formError}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="sla-name">نام قانون</Label>
              <Input
                id="sla-name"
                value={formState.name}
                onChange={(event) => setFormState((current) => ({ ...current, name: event.target.value }))}
                className="h-11 rounded-2xl border-slate-200 bg-slate-50"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>اولویت</Label>
                <Select
                  value={formState.priority_scope}
                  onValueChange={(value) => setFormState((current) => ({ ...current, priority_scope: value as SlaPriorityScope }))}
                >
                  <SelectTrigger className="h-11 rounded-2xl border-slate-200 bg-slate-50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(priorityLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>نوع حمل</Label>
                <Select
                  value={formState.shipping_type_scope}
                  onValueChange={(value) =>
                    setFormState((current) => ({ ...current, shipping_type_scope: value as Exclude<SlaShippingTypeScope, null> }))
                  }
                >
                  <SelectTrigger className="h-11 rounded-2xl border-slate-200 bg-slate-50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(shippingLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3">
              <Label>وضعیت‌های مشمول</Label>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {statusOptions.map((status) => (
                  <label
                    key={status.value}
                    className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"
                  >
                    <Checkbox
                      checked={formState.request_status_scope.includes(status.value)}
                      onCheckedChange={(checked) => toggleStatus(status.value, checked === true)}
                    />
                    {status.label}
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="sla-transport">روش حمل</Label>
              <Input
                id="sla-transport"
                value={formState.transport_method_scope}
                onChange={(event) => setFormState((current) => ({ ...current, transport_method_scope: event.target.value }))}
                placeholder="اختیاری"
                className="h-11 rounded-2xl border-slate-200 bg-slate-50"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="sla-response">مهلت پاسخ‌گویی</Label>
                <Input
                  id="sla-response"
                  type="number"
                  min="1"
                  value={formState.response_time_minutes}
                  onChange={(event) => setFormState((current) => ({ ...current, response_time_minutes: event.target.value }))}
                  className="h-11 rounded-2xl border-slate-200 bg-slate-50"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sla-threshold">آستانه نزدیک به مهلت</Label>
                <Input
                  id="sla-threshold"
                  type="number"
                  min="1"
                  value={formState.near_deadline_threshold_minutes}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, near_deadline_threshold_minutes: event.target.value }))
                  }
                  className="h-11 rounded-2xl border-slate-200 bg-slate-50"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sla-order">ترتیب اعمال</Label>
                <Input
                  id="sla-order"
                  type="number"
                  value={formState.sort_order}
                  onChange={(event) => setFormState((current) => ({ ...current, sort_order: event.target.value }))}
                  className="h-11 rounded-2xl border-slate-200 bg-slate-50"
                />
              </div>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <Label htmlFor="sla-active" className="text-sm text-slate-700">
                فعال
              </Label>
              <Switch
                id="sla-active"
                checked={formState.is_active}
                onCheckedChange={(checked) => setFormState((current) => ({ ...current, is_active: checked }))}
              />
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <Button onClick={handleSubmit} disabled={saving} className="h-11 rounded-2xl bg-blue-600 hover:bg-blue-700">
                {saving ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <Save className="ml-2 h-4 w-4" />}
                ذخیره
              </Button>
              {editingPolicy && (
                <Button onClick={resetForm} disabled={saving} variant="outline" className="h-11 rounded-2xl">
                  <X className="ml-2 h-4 w-4" />
                  انصراف
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="space-y-1 p-5 pb-3">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <Clock3 className="h-5 w-5 text-blue-600" />
              قوانین SLA
            </CardTitle>
            <p className="text-sm text-slate-500">فهرست قوانین از API مدیریت SLA دریافت می‌شود.</p>
          </CardHeader>
          <CardContent className="p-5 pt-2">
            {loading ? (
              <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 text-center text-slate-500">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                <p className="text-sm">در حال دریافت قوانین SLA</p>
              </div>
            ) : policies.length === 0 ? (
              <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                <Clock3 className="h-10 w-10 text-slate-300" />
                <p className="font-medium text-slate-700">هنوز قانونی برای SLA تعریف نشده است.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {policies.map((policy) => (
                  <div key={policy.id} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0 space-y-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="break-words text-base font-bold text-slate-950">{policy.name}</h3>
                          <Badge
                            variant="outline"
                            className={`rounded-full px-3 py-1 ${
                              policy.is_active ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-500"
                            }`}
                          >
                            {policy.is_active ? "فعال" : "غیرفعال"}
                          </Badge>
                        </div>

                        <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2 xl:grid-cols-3">
                          <InfoPill label="اولویت" value={priorityLabels[policy.priority_scope] || policy.priority_scope} />
                          <InfoPill label="وضعیت‌های مشمول" value={policy.request_status_scope.join("، ")} />
                          <InfoPill label="نوع حمل" value={policy.shipping_type_scope ? shippingLabels[policy.shipping_type_scope] : "همه"} />
                          <InfoPill label="روش حمل" value={policy.transport_method_scope || "همه"} />
                          <InfoPill label="مهلت پاسخ‌گویی" value={formatMinutes(policy.response_time_minutes)} />
                          <InfoPill label="آستانه نزدیک به مهلت" value={formatMinutes(policy.near_deadline_threshold_minutes)} />
                          <InfoPill label="ترتیب اعمال" value={formatNumber(policy.sort_order)} />
                        </div>
                      </div>

                      <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col">
                        <Button onClick={() => startEdit(policy)} variant="outline" size="sm" className="rounded-2xl">
                          <Edit3 className="ml-2 h-4 w-4" />
                          ویرایش قانون
                        </Button>
                        <Button
                          onClick={() => togglePolicy(policy)}
                          variant="outline"
                          size="sm"
                          className={`rounded-2xl ${
                            policy.is_active ? "text-red-600 hover:bg-red-50 hover:text-red-700" : "text-emerald-700 hover:bg-emerald-50"
                          }`}
                        >
                          {policy.is_active ? <PowerOff className="ml-2 h-4 w-4" /> : <Power className="ml-2 h-4 w-4" />}
                          {policy.is_active ? "غیرفعال" : "فعال"}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const InfoPill = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3">
    <p className="text-xs text-slate-500">{label}</p>
    <p className="mt-1 break-words text-sm font-semibold text-slate-800">{value || "همه"}</p>
  </div>
);

export default SlaPoliciesTab;
