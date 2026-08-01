import { Link } from "react-router";
import { ArrowLeft } from "lucide-react";
import Header from "@/components/Header";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

const InformationPage = ({ kind }: { kind: "about" | "contact" }) => {
  const { direction, t } = useI18n();
  return <div className="min-h-screen bg-slate-50"><Header /><main className="mx-auto max-w-3xl px-4 py-12 sm:py-16"><article className={`rounded-2xl border bg-white p-6 shadow-sm sm:p-9 ${direction === "rtl" ? "text-right" : "text-left"}`}><h1 className="text-3xl font-bold text-slate-950">{t(`information.${kind}.title`)}</h1><p className="mt-5 whitespace-pre-line text-base leading-8 text-slate-600">{t(`information.${kind}.body`)}</p><Button className="mt-7" variant="outline" asChild><Link to="/"><ArrowLeft className={`h-4 w-4 ${direction === "ltr" ? "rotate-180" : ""}`} />{t("common.backHome")}</Link></Button></article></main></div>;
};

export default InformationPage;
