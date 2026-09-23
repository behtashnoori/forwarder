import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { LogIn, UserPlus } from "lucide-react";
import CustomerPortalLayout from "@/components/CustomerPortalLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CustomerPortalApiError, fetchCustomerSession, loginCustomer, registerCustomer } from "@/lib/customerPortalApi";
import { useI18n } from "@/i18n";

export default function CustomerPortalAccess() {
  const { t } = useI18n(); const navigate = useNavigate(); const location = useLocation();
  const [mode,setMode]=useState<"login"|"register">("login"), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const [form,setForm]=useState({email:"",phone:"",password:"",confirm:"",first_name:"",last_name:""});
  useEffect(()=>{ void fetchCustomerSession().then(s=>{if(s.authenticated) navigate("/customer/requests",{replace:true});}).catch(()=>undefined); },[navigate]);
  const submit=async(event:FormEvent)=>{event.preventDefault();setError("");if(mode==="register"&&form.password!==form.confirm){setError(t("customer.passwordMismatch"));return;}setBusy(true);try{
    if(mode==="login") await loginCustomer(form.email,form.password); else await registerCustomer({email:form.email,phone:form.phone,password:form.password,first_name:form.first_name||undefined,last_name:form.last_name||undefined});
    const requested=(location.state as {from?:string}|null)?.from; navigate(requested?.startsWith("/customer/")?requested:"/customer/requests",{replace:true});
  }catch(e){setError(e instanceof CustomerPortalApiError&&e.code==="ACCOUNT_DISABLED"?t("customer.accountDisabled"):e instanceof Error?e.message:t("common.error"));}finally{setBusy(false);}};
  return <CustomerPortalLayout><Card className="mx-auto max-w-lg"><CardHeader><CardTitle>{t("customer.portalTitle")}</CardTitle><p className="text-sm text-muted-foreground">{t("customer.portalDescription")}</p></CardHeader><CardContent>
    <div className="mb-5 grid grid-cols-2 gap-2"><Button type="button" variant={mode==="login"?"default":"outline"} onClick={()=>setMode("login")}><LogIn className="h-4 w-4"/>{t("customer.signIn")}</Button><Button type="button" variant={mode==="register"?"default":"outline"} onClick={()=>setMode("register")}><UserPlus className="h-4 w-4"/>{t("customer.createAccount")}</Button></div>
    <form className="space-y-4" onSubmit={submit}>
      {mode==="register"&&<div className="grid gap-3 sm:grid-cols-2"><div><Label htmlFor="customer-first">{t("customer.firstName")}</Label><Input id="customer-first" value={form.first_name} onChange={e=>setForm({...form,first_name:e.target.value})}/></div><div><Label htmlFor="customer-last">{t("customer.lastName")}</Label><Input id="customer-last" value={form.last_name} onChange={e=>setForm({...form,last_name:e.target.value})}/></div></div>}
      <div><Label htmlFor="customer-email">{t("common.email")}</Label><Input id="customer-email" type="email" autoComplete="email" required value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></div>
      {mode==="register"&&<div><Label htmlFor="customer-phone">{t("customer.phone")}</Label><Input id="customer-phone" required inputMode="tel" dir="ltr" value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></div>}
      <div><Label htmlFor="customer-password">{t("customer.password")}</Label><Input id="customer-password" type="password" minLength={10} maxLength={128} required autoComplete={mode==="login"?"current-password":"new-password"} value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/></div>
      {mode==="register"&&<div><Label htmlFor="customer-confirm">{t("customer.confirmPassword")}</Label><Input id="customer-confirm" type="password" minLength={10} maxLength={128} required autoComplete="new-password" value={form.confirm} onChange={e=>setForm({...form,confirm:e.target.value})}/></div>}
      {error&&<p role="alert" className="rounded bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
      <Button className="w-full" disabled={busy}>{mode==="login"?t("customer.signIn"):t("customer.createAccount")}</Button>
      {mode==="login"&&<Button asChild type="button" variant="link" className="w-full"><Link to="/customer/forgot-password">{t("customer.forgotPassword")}</Link></Button>}
    </form>
  </CardContent></Card></CustomerPortalLayout>;
}
