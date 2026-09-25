import {
  request,
  submitShipmentRequest,
  type ShipmentRequestPayload,
} from "@/lib/api";
import { env } from "@/lib/env";

const API_BASE_URL = env.API_URL.replace(/\/+$/, "");

export class CustomerPortalApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string) {
    super(message);
    this.name = "CustomerPortalApiError";
  }
}

async function customerRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(!(init?.body instanceof FormData) && { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new CustomerPortalApiError(
      response.status,
      typeof data?.code === "string" ? data.code : "CUSTOMER_PORTAL_ERROR",
      typeof data?.message === "string" ? data.message : `Request failed with status ${response.status}`,
    );
  }
  return data as T;
}

export interface CustomerSharedDocument {
  public_id: string;
  filename: string;
  version: number;
  context_type: "SHIPMENT" | "ROUTE_LEG" | "EXECUTION_UNIT";
}

export const fetchCustomerSharedDocuments = (page = 1) =>
  customerRequest<{ data: CustomerSharedDocument[] }>(`/api/customer/documents?page=${page}`);

export async function downloadCustomerSharedDocument(documentId: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/customer/documents/${encodeURIComponent(documentId)}/download`, {
    credentials: "include", cache: "no-store",
  });
  if (!response.ok) throw new CustomerPortalApiError(response.status, "DOCUMENT_NOT_FOUND", "سند در دسترس نیست");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export type CustomerAccountStatus = "ACTIVE" | "DISABLED";
export type CustomerQuoteResponse = "accepted" | "discussion" | "declined";

export interface CustomerIdentity {
  public_id: string;
  email: string;
  phone: string;
  first_name: string | null;
  last_name: string | null;
  is_email_verified: boolean;
  account_status: CustomerAccountStatus;
}

export interface CustomerSession {
  authenticated: boolean;
  csrf_token?: string;
  customer?: CustomerIdentity;
}

export interface CustomerPortalQuote {
  public_id: string;
  response_version: number;
  amount: number;
  currency: string;
  note?: string | null;
  valid_until?: string | null;
  created_at: string;
  customer_response?: CustomerQuoteResponse | null;
  customer_response_message?: string | null;
  responded_at?: string | null;
}

export interface CustomerRequestSummary {
  public_id: string;
  tracking_code: string | null;
  shipping_type: string;
  status: string;
  created_at: string;
  has_quote: boolean;
  quote_response?: CustomerQuoteResponse | null;
}

export interface CustomerRequestList {
  customer: CustomerIdentity & { total_requests?: number };
  items: CustomerRequestSummary[];
  pagination: { page: number; per_page: number; pages: number; total: number; has_next: boolean; has_prev: boolean };
}

export interface CustomerRequestDetail {
  public_id: string;
  tracking_code: string | null;
  shipping_type: string;
  status: string;
  created_at: string;
  workflow_steps?: Array<{ name?: string; title: string; is_completed: boolean; completed_at?: string | null }>;
  latest_quote: CustomerPortalQuote | null;
  quote_history: CustomerPortalQuote[];
}

export const fetchCustomerSession = () => customerRequest<CustomerSession>("/api/customer/session");

export async function submitShipmentRequestForCurrentCustomer(
  payload: ShipmentRequestPayload,
) {
  let csrfToken: string | undefined;

  try {
    const session = await fetchCustomerSession();
    if (session.authenticated && session.csrf_token) {
      csrfToken = session.csrf_token;
    }
  } catch {
    // Session discovery is deliberately best-effort. Public intake must stay
    // available when the Customer portal is unavailable or has no session.
  }

  const response = await submitShipmentRequest(
    payload,
    csrfToken ? { csrfToken } : undefined,
  );

  return {
    response,
    customerAuthenticated: Boolean(csrfToken),
  };
}
export const registerCustomer = (payload: { email: string; phone: string; password: string; first_name?: string; last_name?: string }) =>
  customerRequest<CustomerSession>("/api/customer/register", { method: "POST", body: JSON.stringify(payload) });
export const loginCustomer = (email: string, password: string) =>
  customerRequest<CustomerSession>("/api/customer/login", { method: "POST", body: JSON.stringify({ email, password }) });
export const logoutCustomer = (csrfToken: string) =>
  customerRequest<CustomerSession>("/api/customer/logout", { method: "POST", headers: { "X-CSRF-Token": csrfToken }, body: "{}" });
export const fetchCustomerProfile = () => customerRequest<{ customer: CustomerIdentity }>("/api/customer/profile");
export const fetchCustomerRequests = (page = 1, perPage = 20) =>
  customerRequest<CustomerRequestList>(`/api/customer/requests?page=${page}&per_page=${perPage}`);
export const fetchCustomerRequest = (publicId: string) =>
  customerRequest<CustomerRequestDetail>(`/api/customer/requests/${encodeURIComponent(publicId)}`);
export const respondToCustomerQuote = (requestId: string, quote: CustomerPortalQuote, response: CustomerQuoteResponse, csrfToken: string, message?: string) =>
  customerRequest<{ message: string; quote: CustomerPortalQuote }>(
    `/api/customer/requests/${encodeURIComponent(requestId)}/quotes/${encodeURIComponent(quote.public_id)}/response`,
    { method: "POST", headers: { "X-CSRF-Token": csrfToken }, body: JSON.stringify({ response, expected_response_version: quote.response_version, ...(response === "discussion" ? { message } : {}) }) },
  );
export const changeCustomerPassword = (currentPassword: string, newPassword: string, csrfToken: string) =>
  customerRequest<{ message: string; authenticated: false }>("/api/customer/password/change", { method: "POST", headers: { "X-CSRF-Token": csrfToken }, body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
export const requestCustomerPasswordReset = (email: string) =>
  customerRequest<{ message: string }>("/api/customer/password/forgot", { method: "POST", body: JSON.stringify({ email }) });
export const resetCustomerPassword = (token: string, newPassword: string) =>
  customerRequest<{ message: string }>("/api/customer/password/reset", { method: "POST", body: JSON.stringify({ token, new_password: newPassword }) });
export const completeCustomerEnrollment = (token: string, newPassword: string) =>
  customerRequest<{ message: string }>("/api/customer/enrollment/complete", { method: "POST", body: JSON.stringify({ token, new_password: newPassword }) });

export interface AdminPortalAccount {
  public_id: string;
  email: string;
  phone: string;
  first_name: string | null;
  last_name: string | null;
  account_status: CustomerAccountStatus;
  enrollment_state?: "ENROLLED" | "PENDING_ENROLLMENT";
  request_count?: number;
  linkage_source?: string | null;
}
export const listAdminPortalAccounts = (query = "") => request<{ items: AdminPortalAccount[] }>(`/api/admin/customer-portal-accounts?q=${encodeURIComponent(query)}`);
export interface AdminPortalCapability {
  message: string;
  purpose: "ENROLLMENT";
  path: string;
  expires_at: string;
}
export interface AdminPortalRecoveryResult {
  message: string;
  purpose: "RESET";
  delivery_channel: "EMAIL";
  delivery_status: "SENT" | "FAILED" | "SUPPRESSED";
}

export const setAdminPortalAccountStatus = (publicId: string, status: CustomerAccountStatus) =>
  request<{ account: AdminPortalAccount }>(
    `/api/admin/customer-portal-accounts/${encodeURIComponent(publicId)}/status`,
    { method: "POST", body: JSON.stringify({ status }) },
  );
export const initiateAdminPortalRecovery = (publicId: string) =>
  request<AdminPortalRecoveryResult>(
    `/api/admin/customer-portal-accounts/${encodeURIComponent(publicId)}/recovery`,
    { method: "POST", body: "{}" },
  );
export const initiateAdminPortalEnrollment = (publicId: string) =>
  request<AdminPortalCapability>(
    `/api/admin/customer-portal-accounts/${encodeURIComponent(publicId)}/enrollment`,
    { method: "POST", body: "{}" },
  );
