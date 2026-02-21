import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import {
  fetchReferralRules,
  createReferralRule,
  updateReferralRule,
  deleteReferralRule,
  previewReferralRule,
  type ReferralRuleRow,
  type ReferralRuleConditions,
  type ReferralRuleAction,
  type ReferralPreviewResult,
} from "@/lib/api";
import { fetchUsers } from "@/lib/api";
import { fetchProvinces } from "@/lib/api";
import type { User } from "@/lib/api";
import { Plus, Edit, Trash2, RefreshCw, Search } from "lucide-react";

const ANY = "__any__";
const SHIPPING_TYPES = [
  { value: ANY, label: "همه" },
  { value: "domestic", label: "داخلی" },
  { value: "international", label: "بین‌المللی" },
];

const TRANSPORT_METHODS = [
  { value: ANY, label: "همه" },
  { value: "road", label: "جاده‌ای" },
  { value: "rail", label: "ریلی" },
  { value: "air", label: "هوایی" },
  { value: "sea", label: "دریایی" },
  { value: "unknown", label: "نامشخص" },
];

const STRATEGIES = [
  { value: "round_robin", label: "Round-robin (نوبتی)" },
  { value: "least_workload", label: "کمترین بار کاری" },
];

export default function ReferralRulesTab() {
  const { toast } = useToast();
  const [rules, setRules] = useState<ReferralRuleRow[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [provinces, setProvinces] = useState<{ id: number; name_fa?: string; name?: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ReferralRuleRow | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [ruleToDelete, setRuleToDelete] = useState<ReferralRuleRow | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [previewRequestId, setPreviewRequestId] = useState("");
  const [previewResult, setPreviewResult] = useState<ReferralPreviewResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [form, setForm] = useState({
    name: "",
    priority: 1,
    is_active: true,
    stop_on_match: true,
    conditions: {} as ReferralRuleConditions,
    action: {
      type: "direct_assign" as const,
      expert_id: 0,
    } as ReferralRuleAction,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [rulesRes, usersRes, provincesRes] = await Promise.all([
        fetchReferralRules(),
        fetchUsers(),
        fetchProvinces(),
      ]);
      setRules(rulesRes.referral_rules);
      setUsers(usersRes.users);
      setProvinces(provincesRes as { id: number; name_fa?: string; name?: string }[]);
    } catch (e) {
      toast({
        title: "خطا",
        description: "خطا در بارگذاری قوانین ارجاع",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const experts = users.filter((u) => ["expert", "business_expert"].includes(u.role) && u.is_active);

  const openCreate = () => {
    setEditingRule(null);
    setForm({
      name: "",
      priority: 1,
      is_active: true,
      stop_on_match: true,
      conditions: {},
      action: { type: "direct_assign", expert_id: experts[0]?.id ?? 0 },
    });
    setDialogOpen(true);
  };

  const openEdit = (rule: ReferralRuleRow) => {
    setEditingRule(rule);
    setForm({
      name: rule.name,
      priority: rule.priority,
      is_active: rule.is_active,
      stop_on_match: rule.stop_on_match,
      conditions: rule.conditions || {},
      action: rule.action as ReferralRuleAction,
    });
    setDialogOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.action.type === "pool_assign") {
      const ids = (form.action as { expert_ids?: number[] }).expert_ids;
      if (!ids?.length) {
        toast({ title: "خطا", description: "برای pool حداقل یک کارشناس انتخاب کنید", variant: "destructive" });
        return;
      }
    }
    setSaving(true);
    try {
      const conditions: ReferralRuleConditions = {
        shipping_type: form.conditions.shipping_type === "" ? undefined : (form.conditions.shipping_type as "domestic" | "international") || undefined,
        transport_method: form.conditions.transport_method === "" ? undefined : (form.conditions.transport_method as "road" | "rail" | "air" | "sea" | "unknown") || undefined,
        origin_province: form.conditions.origin_province || undefined,
        destination_province: form.conditions.destination_province || undefined,
      };
      if (editingRule) {
        await updateReferralRule(editingRule.id, {
          name: form.name,
          priority: form.priority,
          is_active: form.is_active,
          stop_on_match: form.stop_on_match,
          conditions,
          action: form.action,
        });
        toast({ title: "موفق", description: "قانون به‌روزرسانی شد" });
      } else {
        await createReferralRule({
          name: form.name,
          priority: form.priority,
          is_active: form.is_active,
          stop_on_match: form.stop_on_match,
          conditions,
          action: form.action,
        });
        toast({ title: "موفق", description: "قانون ایجاد شد" });
      }
      setDialogOpen(false);
      loadData();
    } catch (err) {
      toast({
        title: "خطا",
        description: err instanceof Error ? err.message : "خطا در ذخیره",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!ruleToDelete) return;
    setDeleting(true);
    try {
      await deleteReferralRule(ruleToDelete.id);
      toast({ title: "موفق", description: "قانون حذف شد" });
      setDeleteDialogOpen(false);
      setRuleToDelete(null);
      loadData();
    } catch (err) {
      toast({
        title: "خطا",
        description: err instanceof Error ? err.message : "خطا در حذف",
        variant: "destructive",
      });
    } finally {
      setDeleting(false);
    }
  };

  const runPreview = async () => {
    const id = parseInt(previewRequestId, 10);
    if (Number.isNaN(id)) {
      toast({ title: "خطا", description: "شناسه درخواست معتبر وارد کنید", variant: "destructive" });
      return;
    }
    setPreviewLoading(true);
    setPreviewResult(null);
    try {
      const result = await previewReferralRule(id);
      setPreviewResult(result);
    } catch (err) {
      toast({
        title: "خطا",
        description: err instanceof Error ? err.message : "خطا در پیش‌نمایش",
        variant: "destructive",
      });
    } finally {
      setPreviewLoading(false);
    }
  };

  const summaryConditions = (c: ReferralRuleConditions) => {
    const parts: string[] = [];
    if (c.shipping_type) parts.push(`نوع: ${c.shipping_type === "domestic" ? "داخلی" : "بین‌المللی"}`);
    if (c.transport_method) parts.push(`حمل: ${c.transport_method}`);
    if (c.origin_province) parts.push("استان مبدا");
    if (c.destination_province) parts.push("استان مقصد");
    return parts.length ? parts.join("، ") : "—";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">قوانین ارجاع</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ml-2 ${loading ? "animate-spin" : ""}`} />
            بروزرسانی
          </Button>
          <Button size="sm" onClick={openCreate}>
            <Plus className="w-4 h-4 ml-2" />
            قانون جدید
          </Button>
        </div>
      </div>

      {/* List */}
      <Card>
        <CardHeader>
          <CardTitle>لیست قوانین</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : rules.length === 0 ? (
            <p className="text-gray-500 text-center py-6">قانونی تعریف نشده است.</p>
          ) : (
            <div className="space-y-3">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center justify-between p-4 border rounded-lg bg-gray-50/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium">{rule.name}</span>
                      {rule.is_active ? (
                        <Badge variant="default">فعال</Badge>
                      ) : (
                        <Badge variant="secondary">غیرفعال</Badge>
                      )}
                      <span className="text-sm text-gray-500">اولویت: {rule.priority}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">شرط: {summaryConditions(rule.conditions)}</p>
                    <p className="text-sm text-gray-600">
                      اکشن: {rule.action_type === "direct_assign" ? "ارجاع مستقیم" : `Pool (${rule.strategy || ""}, ${rule.pool_expert_count} کارشناس)`}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => openEdit(rule)}>
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red-600"
                      onClick={() => {
                        setRuleToDelete(rule);
                        setDeleteDialogOpen(true);
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preview */}
      <Card>
        <CardHeader>
          <CardTitle>پیش‌نمایش ارجاع</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 items-end">
            <div className="flex-1 max-w-xs">
              <Label>شناسه درخواست</Label>
              <Input
                type="number"
                placeholder="مثال: 1"
                value={previewRequestId}
                onChange={(e) => setPreviewRequestId(e.target.value)}
              />
            </div>
            <Button onClick={runPreview} disabled={previewLoading}>
              <Search className="w-4 h-4 ml-2" />
              {previewLoading ? "در حال محاسبه..." : "پیش‌نمایش"}
            </Button>
          </div>
          {previewResult && (
            <div className="p-4 bg-gray-50 rounded-lg space-y-2 text-sm">
              {previewResult.error ? (
                <p className="text-red-600">{previewResult.error}</p>
              ) : (
                <>
                  {previewResult.matched_rule ? (
                    <p>
                      <strong>قانون منطبق:</strong> {previewResult.matched_rule.name} (اولویت {previewResult.matched_rule.priority})
                    </p>
                  ) : (
                    <p>هیچ قانون فعالی با این درخواست منطبق نشد.</p>
                  )}
                  {previewResult.selected_expert && (
                    <p>
                      <strong>کارشناس انتخاب‌شده:</strong> {previewResult.selected_expert.full_name} (ID: {previewResult.selected_expert.id})
                    </p>
                  )}
                  {previewResult.strategy_used && (
                    <p><strong>استراتژی:</strong> {previewResult.strategy_used}</p>
                  )}
                  {previewResult.candidates?.length > 0 && (
                    <p><strong>نامزدها:</strong> {previewResult.candidates.join(", ")}</p>
                  )}
                  {Object.keys(previewResult.debug_trace || {}).length > 0 && (
                    <pre className="mt-2 p-2 bg-white rounded text-xs overflow-auto max-h-40">
                      {JSON.stringify(previewResult.debug_trace, null, 2)}
                    </pre>
                  )}
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingRule ? "ویرایش قانون" : "قانون جدید"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <Label>نام</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="نام قانون"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>اولویت (کمتر = بالاتر)</Label>
                <Input
                  type="number"
                  value={form.priority}
                  onChange={(e) => setForm((f) => ({ ...f, priority: parseInt(e.target.value, 10) || 1 }))}
                />
              </div>
              <div className="flex items-center gap-4 pt-6">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={form.is_active}
                    onCheckedChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
                  />
                  <Label>فعال</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={form.stop_on_match}
                    onCheckedChange={(v) => setForm((f) => ({ ...f, stop_on_match: v }))}
                  />
                  <Label>توقف با اولین تطابق</Label>
                </div>
              </div>
            </div>

            <div className="border-t pt-4">
              <Label className="text-base">شرایط</Label>
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div>
                  <Label className="text-xs">نوع ارسال</Label>
                  <Select
                    value={form.conditions.shipping_type ?? ANY}
                    onValueChange={(v) =>
                      setForm((f) => ({
                        ...f,
                        conditions: { ...f.conditions, shipping_type: v === ANY ? undefined : (v as "domestic" | "international") },
                      }))
                    }
                  >
                    <SelectTrigger><SelectValue placeholder="همه" /></SelectTrigger>
                    <SelectContent>
                      {SHIPPING_TYPES.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">روش حمل</Label>
                  <Select
                    value={form.conditions.transport_method ?? ANY}
                    onValueChange={(v) =>
                      setForm((f) => ({
                        ...f,
                        conditions: { ...f.conditions, transport_method: v === ANY ? undefined : (v as "road" | "rail" | "air" | "sea" | "unknown") },
                      }))
                    }
                  >
                    <SelectTrigger><SelectValue placeholder="همه" /></SelectTrigger>
                    <SelectContent>
                      {TRANSPORT_METHODS.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">استان مبدا</Label>
                  <Select
                    value={String(form.conditions.origin_province ?? "")}
                    onValueChange={(v) =>
                      setForm((f) => ({
                        ...f,
                        conditions: { ...f.conditions, origin_province: v ? parseInt(v, 10) : undefined },
                      }))
                    }
                  >
                    <SelectTrigger><SelectValue placeholder="هر" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">هر</SelectItem>
                      {provinces.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>{p.name_fa || p.name || p.id}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">استان مقصد</Label>
                  <Select
                    value={String(form.conditions.destination_province ?? "")}
                    onValueChange={(v) =>
                      setForm((f) => ({
                        ...f,
                        conditions: { ...f.conditions, destination_province: v ? parseInt(v, 10) : undefined },
                      }))
                    }
                  >
                    <SelectTrigger><SelectValue placeholder="هر" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">هر</SelectItem>
                      {provinces.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>{p.name_fa || p.name || p.id}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <div className="border-t pt-4">
              <Label className="text-base">نوع اکشن</Label>
              <Select
                value={form.action.type}
                onValueChange={(v: "direct_assign" | "pool_assign") =>
                  setForm((f) => ({
                    ...f,
                    action:
                      v === "direct_assign"
                        ? { type: "direct_assign", expert_id: experts[0]?.id ?? 0 }
                        : { type: "pool_assign", expert_ids: [], strategy: "round_robin" },
                  }))
                }
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="direct_assign">ارجاع مستقیم (یک کارشناس)</SelectItem>
                  <SelectItem value="pool_assign">Pool (چند کارشناس + توزیع)</SelectItem>
                </SelectContent>
              </Select>

              {form.action.type === "direct_assign" && (
                <div className="mt-2">
                  <Label className="text-xs">کارشناس</Label>
                  <Select
                    value={String((form.action as { expert_id: number }).expert_id)}
                    onValueChange={(v) =>
                      setForm((f) => ({
                        ...f,
                        action: { ...f.action, expert_id: parseInt(v, 10) } as ReferralRuleAction,
                      }))
                    }
                  >
                    <SelectTrigger><SelectValue placeholder="انتخاب کارشناس" /></SelectTrigger>
                    <SelectContent>
                      {experts.map((u) => (
                        <SelectItem key={u.id} value={String(u.id)}>{u.full_name} ({u.role})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {form.action.type === "pool_assign" && (
                <div className="mt-2 space-y-2">
                  <Label className="text-xs">کارشناسان (چند انتخاب)</Label>
                  <Select
                    value=""
                    onValueChange={(v) => {
                      const id = parseInt(v, 10);
                      const pool = form.action as { expert_ids: number[]; strategy: string; max_active_assignments_per_expert?: number };
                      if (pool.expert_ids.includes(id)) return;
                      setForm((f) => ({
                        ...f,
                        action: {
                          ...(f.action as object),
                          expert_ids: [...(pool.expert_ids || []), id],
                          strategy: pool.strategy || "round_robin",
                          max_active_assignments_per_expert: pool.max_active_assignments_per_expert,
                        } as ReferralRuleAction,
                      }));
                    }}
                  >
                    <SelectTrigger><SelectValue placeholder="افزودن کارشناس" /></SelectTrigger>
                    <SelectContent>
                      {experts
                        .filter((u) => !(form.action as { expert_ids?: number[] }).expert_ids?.includes(u.id))
                        .map((u) => (
                          <SelectItem key={u.id} value={String(u.id)}>{u.full_name}</SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <div className="flex flex-wrap gap-2">
                    {(form.action as { expert_ids?: number[] }).expert_ids?.map((eid) => {
                      const u = experts.find((x) => x.id === eid);
                      return (
                        <Badge key={eid} variant="secondary" className="flex items-center gap-1">
                          {u?.full_name ?? eid}
                          <button
                            type="button"
                            className="ml-1 hover:text-red-600"
                            onClick={() =>
                              setForm((f) => {
                                const pool = f.action as { expert_ids: number[]; strategy: string; max_active_assignments_per_expert?: number };
                                return {
                                  ...f,
                                  action: {
                                    ...pool,
                                    expert_ids: pool.expert_ids.filter((id) => id !== eid),
                                  } as ReferralRuleAction,
                                };
                              })
                            }
                          >
                            ×
                          </button>
                        </Badge>
                      );
                    })}
                  </div>
                  <div>
                    <Label className="text-xs">استراتژی</Label>
                    <Select
                      value={(form.action as { strategy: string }).strategy || "round_robin"}
                      onValueChange={(v: "round_robin" | "least_workload") =>
                        setForm((f) => ({
                          ...f,
                          action: { ...(f.action as object), strategy: v } as ReferralRuleAction,
                        }))
                      }
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {STRATEGIES.map((s) => (
                          <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">سقف ظرفیت هر کارشناس (اختیاری)</Label>
                    <Input
                      type="number"
                      min={0}
                      placeholder="خالی = بدون سقف"
                      value={(form.action as { max_active_assignments_per_expert?: number }).max_active_assignments_per_expert ?? ""}
                      onChange={(e) => {
                        const v = e.target.value.trim();
                        setForm((f) => ({
                          ...f,
                          action: {
                            ...(f.action as object),
                            max_active_assignments_per_expert: v ? parseInt(v, 10) : undefined,
                          } as ReferralRuleAction,
                        }));
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                انصراف
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "در حال ذخیره..." : editingRule ? "به‌روزرسانی" : "ایجاد"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>حذف قانون</AlertDialogTitle>
            <AlertDialogDescription>
              آیا از حذف قانون «{ruleToDelete?.name}» اطمینان دارید؟
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>انصراف</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleting} className="bg-red-600">
              {deleting ? "در حال حذف..." : "حذف"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
