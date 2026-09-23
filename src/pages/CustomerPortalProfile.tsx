import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import CustomerPortalLayout from "@/components/CustomerPortalLayout";
import { Card,CardContent,CardHeader,CardTitle } from "@/components/ui/card";
import { fetchCustomerProfile, type CustomerIdentity } from "@/lib/customerPortalApi";
import { useI18n } from "@/i18n";

export default function CustomerPortalProfile(){const {t}=useI18n();const navigate=useNavigate(),location=useLocation();const [profile,setProfile]=useState<CustomerIdentity|null>(null),[error,setError]=useState("");useEffect(()=>{void fetchCustomerProfile().then(r=>setProfile(r.customer)).catch(e=>{if((e as {status?:number}).status===401)navigate("/customer",{replace:true,state:{from:location.pathname}});else setError(e instanceof Error?e.message:t("common.error"));});},[location.pathname,navigate,t]);
 return <CustomerPortalLayout privateNav><Card className="mx-auto max-w-2xl"><CardHeader><CardTitle>{t("customer.profile")}</CardTitle><p className="text-sm text-muted-foreground">{t("customer.profileReadOnly")}</p></CardHeader><CardContent>{error&&<p role="alert" className="text-destructive">{error}</p>}{profile&&<dl className="grid gap-4 sm:grid-cols-2"><Field label={t("customer.firstName")} value={profile.first_name}/><Field label={t("customer.lastName")} value={profile.last_name}/><Field label={t("common.email")} value={profile.email}/><Field label={t("customer.phone")} value={profile.phone}/><Field label={t("customer.accountStatus")} value={profile.account_status==="ACTIVE"?t("customer.active"):t("customer.disabled")}/></dl>}</CardContent></Card></CustomerPortalLayout>}
function Field({label,value}:{label:string;value:string|null|undefined}){return <div className="rounded border p-3"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-medium">{value||"—"}</dd></div>}
