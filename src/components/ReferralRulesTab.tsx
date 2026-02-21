import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { previewReferralRule, type ReferralPreviewResult } from "@/lib/api";
import { Search } from "lucide-react";

export default function ReferralRulesTab() {
  const { toast } = useToast();
  const [previewRequestId, setPreviewRequestId] = useState("");
  const [previewResult, setPreviewResult] = useState<ReferralPreviewResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>توزیع خودکار ارجاع</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-gray-600">
            درخواست‌های جدید به‌صورت خودکار و به‌ترتیب (round-robin) بین همهٔ کارشناسان فعال توزیع می‌شوند.
            نیازی به تعریف قانون یا تنظیم خاصی نیست.
          </p>
          <p className="text-sm text-gray-500">
            کارشناسان با نقش «کارشناس» یا «کارشناس کسب‌وکار» که وضعیت آن‌ها فعال است در چرخش ارجاع قرار می‌گیرند.
          </p>
        </CardContent>
      </Card>

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
                  {previewResult.selected_expert ? (
                    <p>
                      <strong>کارشناس انتخاب‌شده (در چرخش بعدی):</strong>{" "}
                      {previewResult.selected_expert.full_name} (ID: {previewResult.selected_expert.id})
                    </p>
                  ) : (
                    <p>هیچ کارشناسی برای ارجاع موجود نیست.</p>
                  )}
                  {previewResult.strategy_used && (
                    <p><strong>روش:</strong> {previewResult.strategy_used}</p>
                  )}
                  {previewResult.candidates?.length != null && (
                    <p><strong>تعداد کارشناسان در چرخش:</strong> {previewResult.candidates.length}</p>
                  )}
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
