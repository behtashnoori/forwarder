import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ReferralRulesTab() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>توزیع خودکار درخواست‌ها</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-gray-600">
            درخواست‌های جدید به صورت خودکار و چرخشی بین کارشناسان فعال توزیع می‌شوند.
            نیازی به تعریف قانون یا تنظیم خاصی نیست.
          </p>
          <p className="text-sm text-gray-500">
            کارشناسان با نقش «کارشناس» یا «کارشناس کسب‌وکار» که وضعیت آن‌ها فعال است در چرخش توزیع قرار می‌گیرند.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
