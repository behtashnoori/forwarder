import { useState } from "react";
import { Download, FileSpreadsheet, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  AdminReportDownloadHttpError,
  downloadAdminReportXlsx,
  type AdminReportPeriod,
} from "@/lib/api";

type ReportOption = {
  period: AdminReportPeriod;
  title: string;
  description: string;
  buttonLabel: string;
};

const reportOptions: ReportOption[] = [
  {
    period: "weekly",
    title: "گزارش هفتگی",
    description: "خروجی Excel از درخواست‌های ۷ روز اخیر",
    buttonLabel: "دانلود Excel هفتگی",
  },
  {
    period: "monthly",
    title: "گزارش ماهانه",
    description: "خروجی Excel از درخواست‌های ماه جاری",
    buttonLabel: "دانلود Excel ماهانه",
  },
  {
    period: "yearly",
    title: "گزارش سالانه",
    description: "خروجی Excel از درخواست‌های سال جاری",
    buttonLabel: "دانلود Excel سالانه",
  },
];

export default function AdminReportsTab() {
  const { toast } = useToast();
  const [downloadingPeriods, setDownloadingPeriods] = useState<Partial<Record<AdminReportPeriod, boolean>>>({});

  const handleDownload = async (period: AdminReportPeriod) => {
    const token = localStorage.getItem("expert_token");
    if (!token || token === "null") {
      toast({
        title: "ورود مجدد",
        description: "لطفاً دوباره وارد شوید",
        variant: "destructive",
      });
      return;
    }

    try {
      setDownloadingPeriods((current) => ({ ...current, [period]: true }));
      const { blob, filename } = await downloadAdminReportXlsx(token, period);
      triggerBlobDownload(blob, filename);
    } catch (error) {
      const isAuthError = error instanceof AdminReportDownloadHttpError && [401, 403].includes(error.status);
      toast({
        title: isAuthError ? "دسترسی نامعتبر" : "خطا",
        description: isAuthError
          ? "برای دریافت گزارش، لطفاً دوباره با حساب مدیر وارد شوید."
          : "دریافت گزارش انجام نشد. لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setDownloadingPeriods((current) => ({ ...current, [period]: false }));
    }
  };

  return (
    <div className="space-y-6">
      <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
        <CardHeader className="space-y-2 p-5 pb-3">
          <CardTitle className="flex items-center gap-2 text-xl text-slate-950">
            <FileSpreadsheet className="h-5 w-5 text-blue-600" />
            گزارش‌ها
          </CardTitle>
          <p className="max-w-4xl text-sm leading-7 text-slate-500">
            دریافت خروجی مدیریتی از درخواست‌ها، وضعیت‌ها، نوع حمل، مشتریان و عملکرد کارشناسان
          </p>
        </CardHeader>
        <CardContent className="grid gap-4 p-5 pt-2 md:grid-cols-3">
          {reportOptions.map((option) => {
            const isDownloading = Boolean(downloadingPeriods[option.period]);
            return (
              <Card key={option.period} className="rounded-2xl border-slate-200 bg-slate-50 shadow-none">
                <CardContent className="flex h-full flex-col gap-4 p-4">
                  <div className="flex items-start gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                      <FileSpreadsheet className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <h3 className="text-base font-bold text-slate-950">{option.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-500">{option.description}</p>
                    </div>
                  </div>

                  <Button
                    onClick={() => handleDownload(option.period)}
                    disabled={isDownloading}
                    className="mt-auto h-11 rounded-2xl bg-blue-600 hover:bg-blue-700"
                  >
                    {isDownloading ? (
                      <>
                        <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                        در حال آماده‌سازی فایل...
                      </>
                    ) : (
                      <>
                        <Download className="ml-2 h-4 w-4" />
                        {option.buttonLabel}
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}
