import { Construction } from "lucide-react";
import PageNav from "@/components/PageNav";
import { useI18n } from "@/i18n";

const CRMDashboard = () => {
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <PageNav backLabel={t("common.back")} />
        </div>
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="p-6 bg-amber-100 rounded-full mb-6">
            <Construction className="w-16 h-16 text-amber-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{t("crm.title")}</h1>
          <p className="text-xl text-gray-600">{t("crm.inDevelopment")}</p>
        </div>
      </div>
    </div>
  );
};

export default CRMDashboard;
