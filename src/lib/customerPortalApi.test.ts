import { beforeEach,describe,expect,it,vi } from "vitest";
import {
  fetchCustomerSession,
  requestCustomerPasswordReset,
  respondToCustomerQuote,
  setAdminPortalAccountStatus,
  initiateAdminPortalRecovery,
  submitShipmentRequestForCurrentCustomer,
} from "./customerPortalApi";

beforeEach(()=>{vi.restoreAllMocks();});

describe("customer portal API boundary",()=>{
  it("uses credentialed cookies only through the customer client",async()=>{const fetchMock=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({authenticated:false}),{status:200,headers:{"Content-Type":"application/json"}}));await fetchCustomerSession();expect(fetchMock).toHaveBeenCalledWith("/api/customer/session",expect.objectContaining({credentials:"include"}));});
  it("submits the exact quote identity, discussion message, CSRF and response version",async()=>{const fetchMock=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({message:"saved",quote:{}}),{status:200,headers:{"Content-Type":"application/json"}}));await respondToCustomerQuote("request-public",{public_id:"quote-public",response_version:4,amount:10,currency:"IRR",created_at:"2026-09-23"},"discussion","csrf","please call");const [,init]=fetchMock.mock.calls[0];expect(fetchMock.mock.calls[0][0]).toBe("/api/customer/requests/request-public/quotes/quote-public/response");expect(init?.headers).toMatchObject({"X-CSRF-Token":"csrf"});expect(JSON.parse(String(init?.body))).toEqual({response:"discussion",expected_response_version:4,message:"please call"});});
  it("uses the enumeration-safe forgot endpoint",async()=>{const fetchMock=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({message:"accepted"}),{status:202,headers:{"Content-Type":"application/json"}}));await requestCustomerPasswordReset("nobody@example.test");expect(fetchMock.mock.calls[0][0]).toBe("/api/customer/password/forgot");});
  it("includes Customer cookies and CSRF only after an authenticated session check",async()=>{const fetchMock=vi.spyOn(globalThis,"fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({authenticated:true,csrf_token:"customer-csrf"}),{status:200,headers:{"Content-Type":"application/json"}}))
    .mockResolvedValueOnce(new Response(JSON.stringify({id:1,tracking_code:"SR2-PORTAL",message:"created",request_transport_intent:null,cargo_items:[],request_public_id:"request-public"}),{status:201,headers:{"Content-Type":"application/json"}}));
    const result=await submitShipmentRequestForCurrentCustomer({shipping_type:"domestic",contact_phone:"09123456789"});
    expect(fetchMock.mock.calls[1][0]).toBe("/api/shipment-request");
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({credentials:"include",headers:expect.objectContaining({"X-CSRF-Token":"customer-csrf"})}));
    expect(result).toMatchObject({customerAuthenticated:true,response:{request_public_id:"request-public"}});
  });
  it("falls back to cookie-free anonymous intake when session discovery fails",async()=>{const fetchMock=vi.spyOn(globalThis,"fetch")
    .mockRejectedValueOnce(new TypeError("session unavailable"))
    .mockResolvedValueOnce(new Response(JSON.stringify({id:2,tracking_code:"SR2-PUBLIC",message:"created",request_transport_intent:null,cargo_items:[]}),{status:201,headers:{"Content-Type":"application/json"}}));
    const result=await submitShipmentRequestForCurrentCustomer({shipping_type:"domestic",contact_phone:"09123456789"});
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({credentials:"omit"}));
    expect((fetchMock.mock.calls[1][1]?.headers as Record<string,string>)["X-CSRF-Token"]).toBeUndefined();
    expect(result.customerAuthenticated).toBe(false);
  });
  it("uses tenant-scoped admin status and email recovery endpoints",async()=>{const fetchMock=vi.spyOn(globalThis,"fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({account:{public_id:"customer-public"}}),{status:200,headers:{"Content-Type":"application/json"}}))
    .mockResolvedValueOnce(new Response(JSON.stringify({message:"processed",purpose:"RESET",delivery_channel:"EMAIL",delivery_status:"SENT"}),{status:202,headers:{"Content-Type":"application/json"}}));
    await setAdminPortalAccountStatus("customer-public","DISABLED");
    const capability=await initiateAdminPortalRecovery("customer-public");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/customer-portal-accounts/customer-public/status");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({status:"DISABLED"});
    expect(fetchMock.mock.calls[1][0]).toBe("/api/admin/customer-portal-accounts/customer-public/recovery");
    expect(capability).toMatchObject({delivery_channel:"EMAIL",delivery_status:"SENT"});
  });
});
