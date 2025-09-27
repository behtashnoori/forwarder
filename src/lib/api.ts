export interface Province {
  id: number;
  name: string;
  code?: string | null;
}

export interface County {
  id: number;
  name: string;
}

export interface City {
  id: number;
  name: string;
}

export interface ShipmentRequestPayload {
  origin_province_id: number;
  origin_county_id: number;
  origin_city_id: number;
  dest_province_id: number;
  dest_county_id: number;
  dest_city_id: number;
  contact_phone: string;
  // Customer details (optional)
  customer_first_name?: string;
  customer_last_name?: string;
  transport_method?: string;
  // Cargo details (optional)
  cargo_description?: string;
  cargo_weight?: number;
  cargo_volume?: number;
  cargo_value?: number;
  special_instructions?: string;
  pickup_date?: string;
  delivery_date?: string;
}

import { env } from './env';

const API_BASE_URL = env.API_URL.replace(/\/+$/, "");

function buildPath(path: string): string {
  if (!path.startsWith("/")) {
    return `/${path}`;
  }
  return path;
}

function withQuery(path: string, params?: Record<string, string | number | undefined>): string {
  if (!params) {
    return path;
  }

  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });

  if (!searchParams.toString()) {
    return path;
  }

  return `${path}?${searchParams.toString()}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error("API URL is not configured. Please check your environment variables.");
  }

  const url = `${API_BASE_URL}${buildPath(path)}`;
  const requestInit: RequestInit = {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  };
  const response = await fetch(url, requestInit);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body && typeof body.message === "string") {
        message = body.message;
      }
    } catch (error) {
      // Ignore JSON parsing errors and keep default message.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function fetchProvinces(): Promise<Province[]> {
  return request<Province[]>("/api/provinces");
}

export function fetchCounties(provinceId: number): Promise<County[]> {
  const path = withQuery("/api/counties", { province_id: provinceId });
  return request<County[]>(path);
}

export function fetchCities(countyId: number): Promise<City[]> {
  const path = withQuery("/api/cities", { county_id: countyId });
  return request<City[]>(path);
}

export function submitShipmentRequest(
  payload: ShipmentRequestPayload,
): Promise<{ message: string; id: number }> {
  return request<{ message: string; id: number }>("/api/shipment-request", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Expert Console Interfaces
export interface ExpertRequest {
  id: number;
  tracking_number: string;
  status: string;
  priority: string;
  created_at: string;
  sla_due_at?: string;
  sla_status: "on_time" | "due_soon" | "overdue";
  assigned_to?: {
    id: number;
    name: string;
  };
  customer: {
    name: string;
    phone: string;
  };
  route: {
    origin: {
      province: string;
      county: string;
      city: string;
    };
    destination: {
      province: string;
      county: string;
      city: string;
    };
  };
  transport_method?: string;
  cargo: {
    description?: string;
    weight?: number;
    volume?: number;
    value?: number;
  };
  has_unread: boolean;
}

export interface ExpertUser {
  id: number;
  username: string;
  full_name: string;
  role: string;
}

export interface ExpertMessage {
  id: number;
  type: "internal_note" | "customer_message";
  subject?: string;
  content: string;
  is_read_by_customer: boolean;
  customer_response?: string;
  created_at: string;
  created_by: string;
}

export interface ExpertNotification {
  id: number;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  shipment_request_id: number;
}

export interface KPIs {
  counts: {
    new: number;
    in_progress: number;
    waiting_for_customer: number;
    closed_today: number;
  };
  sla: {
    overdue: number;
    due_soon: number;
  };
}

// Expert Console API functions
export function fetchExpertRequests(params?: {
  page?: number;
  per_page?: number;
  status?: string;
  assigned_to?: number;
  priority?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
}): Promise<{
  requests: ExpertRequest[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}> {
  const path = withQuery("/api/expert/requests", params);
  return request(path);
}

export function fetchExpertRequestDetail(requestId: number): Promise<ExpertRequest & {
  customer: {
    first_name?: string;
    last_name?: string;
    phone: string;
    full_name: string;
  };
  dates: {
    pickup_date?: string;
    delivery_date?: string;
  };
  timeline: Array<{
    id: number;
    action: string;
    old_status?: string;
    new_status?: string;
    note?: string;
    created_at: string;
    created_by: string;
  }>;
  messages: ExpertMessage[];
}> {
  return request(`/api/expert/requests/${requestId}`);
}

export function assignRequest(requestId: number, expertId: number): Promise<{
  message: string;
  assigned_to: { id: number; name: string };
}> {
  return request(`/api/expert/requests/${requestId}/assign`, {
    method: "POST",
    body: JSON.stringify({ expert_id: expertId }),
  });
}

export function changeRequestStatus(
  requestId: number,
  status: string,
  note?: string
): Promise<{ message: string; status: string }> {
  return request(`/api/expert/requests/${requestId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, note }),
  });
}

export function addMessage(
  requestId: number,
  messageType: "internal_note" | "customer_message",
  content: string,
  subject?: string,
  expertId?: number
): Promise<{ message: string; message_id: number }> {
  return request(`/api/expert/requests/${requestId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      type: messageType,
      content,
      subject,
      expert_id: expertId,
    }),
  });
}

export function fetchNotifications(expertId: number, unreadOnly = false): Promise<{
  notifications: ExpertNotification[];
  unread_count: number;
}> {
  const path = withQuery("/api/expert/notifications", {
    expert_id: expertId,
    unread_only: unreadOnly,
  });
  return request(path);
}

export function fetchKPIs(expertId?: number): Promise<KPIs> {
  const path = withQuery("/api/expert/dashboard/kpis", expertId ? { expert_id: expertId } : undefined);
  return request(path);
}

export function markRequestAsRead(requestId: number, expertId: number): Promise<{
  message: string;
}> {
  const path = withQuery(`/api/expert/requests/${requestId}/mark-read`, {
    expert_id: expertId,
  });
  return request(path, { method: "POST" });
}

export function fetchExperts(): Promise<{ experts: ExpertUser[] }> {
  return request("/api/expert/experts");
}

// CRM Interfaces
export interface Customer {
  id: number;
  name: string;
  company_name?: string;
  email?: string;
  phone?: string;
  customer_type: string;
  status: string;
  industry?: string;
  last_contact_at?: string;
  created_at: string;
  total_opportunities: number;
  total_activities: number;
}

export interface CustomerDetail extends Customer {
  mobile?: string;
  website?: string;
  company_size?: string;
  source?: string;
  notes?: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  country?: string;
  contacts: CustomerContact[];
  opportunities: Opportunity[];
  recent_activities: Activity[];
}

export interface CustomerContact {
  id: number;
  name: string;
  email?: string;
  phone?: string;
  position?: string;
  is_primary: boolean;
  is_decision_maker: boolean;
}

export interface Opportunity {
  id: number;
  title: string;
  customer?: {
    id: number;
    name: string;
    company_name?: string;
  };
  stage: string;
  value?: number;
  probability: number;
  status: string;
  expected_close_date?: string;
  assigned_to?: {
    id: number;
    name: string;
  };
  created_at: string;
}

export interface Activity {
  id: number;
  type: string;
  subject: string;
  description?: string;
  status: string;
  priority: string;
  due_date?: string;
  completed_at?: string;
  outcome?: string;
  customer?: {
    id: number;
    name: string;
  };
  expert?: {
    id: number;
    name: string;
  };
  created_at: string;
}

export interface CRMDashboardKPIs {
  customers: {
    total: number;
    new_this_month: number;
  };
  opportunities: {
    total: number;
    open: number;
    won: number;
    pipeline_value: number;
  };
  activities: {
    total: number;
    completed: number;
  };
  recent_activities: Array<{
    id: number;
    type: string;
    subject: string;
    customer_name: string;
    expert_name: string;
    created_at: string;
  }>;
}

// CRM API Functions
export function fetchCustomers(params?: {
  page?: number;
  per_page?: number;
  search?: string;
  customer_type?: string;
  status?: string;
  sort_by?: string;
  sort_order?: string;
}): Promise<{
  customers: Customer[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}> {
  const path = withQuery("/api/crm/customers", params);
  return request(path);
}

export function createCustomer(customerData: {
  company_name?: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  mobile?: string;
  website?: string;
  industry?: string;
  company_size?: string;
  customer_type?: string;
  status?: string;
  source?: string;
  notes?: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  country?: string;
}): Promise<{ message: string; customer_id: number }> {
  return request("/api/crm/customers", {
    method: "POST",
    body: JSON.stringify(customerData),
  });
}

export function fetchCustomerDetail(customerId: number): Promise<CustomerDetail> {
  return request(`/crm/customers/${customerId}`);
}

export function updateCustomer(
  customerId: number,
  customerData: Partial<CustomerDetail>
): Promise<{ message: string }> {
  return request(`/crm/customers/${customerId}`, {
    method: "PUT",
    body: JSON.stringify(customerData),
  });
}

export function fetchOpportunities(params?: {
  page?: number;
  per_page?: number;
  stage?: string;
  assigned_to?: number;
  search?: string;
}): Promise<{
  opportunities: Opportunity[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}> {
  const path = withQuery("/api/crm/opportunities", params);
  return request(path);
}

export function createOpportunity(opportunityData: {
  customer_id: number;
  title: string;
  description?: string;
  stage?: string;
  probability?: number;
  value?: number;
  currency?: string;
  expected_close_date?: string;
  source?: string;
  assigned_to?: number;
  notes?: string;
}): Promise<{ message: string; opportunity_id: number }> {
  return request("/api/crm/opportunities", {
    method: "POST",
    body: JSON.stringify(opportunityData),
  });
}

export function fetchActivities(params?: {
  page?: number;
  per_page?: number;
  activity_type?: string;
  expert_id?: number;
  customer_id?: number;
  status?: string;
}): Promise<{
  activities: Activity[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}> {
  const path = withQuery("/api/crm/activities", params);
  return request(path);
}

export function createActivity(activityData: {
  customer_id?: number;
  opportunity_id?: number;
  shipment_request_id?: number;
  expert_user_id: number;
  activity_type: string;
  subject: string;
  description?: string;
  priority?: string;
  due_date?: string;
  outcome?: string;
  next_action?: string;
}): Promise<{ message: string; activity_id: number }> {
  return request("/api/crm/activities", {
    method: "POST",
    body: JSON.stringify(activityData),
  });
}

export function fetchCRMDashboardKPIs(): Promise<CRMDashboardKPIs> {
  return request("/api/crm/dashboard/kpis");
}
