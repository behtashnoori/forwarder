import { createElement, type ComponentProps } from "react";
import { createRoot } from "react-dom/client";
import CustomerPage from "./pages/QuoteCapabilityCustomer";
const root = createRoot(document.getElementById("root")!);
let sequence = 0;
function mountCustomer(call: ComponentProps<typeof CustomerPage>["call"] | null) {
  root.render(call ? createElement(CustomerPage, { call, key: ++sequence }) :
    createElement("p", null, "برای مشاهده پیشنهاد، پیوند خصوصی ارسال‌شده را باز کنید."));
}

document.dispatchEvent(new CustomEvent("quote-customer-ready", { detail: mountCustomer }));
