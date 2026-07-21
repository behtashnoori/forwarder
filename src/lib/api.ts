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

export interface Country {
  id: number;
  name: string;
  name_en: string;
  code: string;
}

export interface InternationalCity {
  id: number;
  name: string;
  name_en: string;
  city_type: string;
  is_major_port: boolean;
  is_major_airport: boolean;
}

export interface IranPort {
  id: number;
  name_fa: string;
  name_en: string;
  port_type: string;
  province_id: number;
  province_name?: string;
  is_major_port: boolean;
  description?: string;
}

export interface PortProvinceMapping {
  id: number;
  port_id: number;
  port_name?: string;
  province_id: number;
  province_name?: string;
  suitability_score: number;
  transport_method?: string;
  estimated_days?: number;
  is_recommended: boolean;
}

export interface RecommendedPort {
  port_id: number;
  port_name_fa: string;
  port_name_en: string;
  port_type: string;
  suitability_score: number;
  transport_method?: string;
  estimated_days?: number;
  is_recommended: boolean;
  description?: string;
}

export interface TransportMethod {
  id: number;
  name: string;
  name_fa: string;
  description?: string;
  is_active?: boolean;
}

export interface TransportMethodOptions {
  international_methods: TransportMethod[];
  domestic_methods: TransportMethod[];
  preference_options: {
    value: string;
    label: string;
    description: string;
  }[];
}

export interface ShipmentRequestPayload {
  shipping_type: "domestic" | "international";
  // Domestic shipping fields
  origin_province_id?: number;
  origin_county_id?: number | null;
  origin_city_id?: number | null;
  dest_province_id?: number;
  dest_county_id?: number | null;
  dest_city_id?: number | null;
  // International shipping fields
  origin_country?: string;
  origin_city_international?: string;
  origin_address_international?: string;
  dest_country?: string;
  dest_city_international?: string;
  dest_address_international?: string;
  // Iran entry point fields (for international shipping to Iran)
  iran_entry_port?: string;
  iran_entry_province?: string;
  iran_entry_port_id?: number;
  iran_entry_province_id?: number;
  contact_phone: string;
  // Customer details (optional)
  customer_first_name?: string;
  customer_last_name?: string;
  transport_method?: string;  // Legacy field
  international_transport_method?: string;
  domestic_transport_method?: string;
  transport_method_preference?: string;
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

/** Build full URL for logo image so it loads correctly (handles path-only URLs from API). */
export function getLogoDisplayUrl(url: string | undefined): string {
  if (!url?.trim()) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  const base = env.API_URL.replace(/\/+$/, "");
  return base ? base + url : url;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!import.meta.env.DEV && !API_BASE_URL) {
    throw new Error("API URL is not configured. Set VITE_API_URL for production.");
  }
  const url = `${API_BASE_URL}${buildPath(path)}`;
  
  // Get token from localStorage
  const token = localStorage.getItem('expert_token');
  
  const requestInit: RequestInit = {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token && { "Authorization": `Bearer ${token}` }),
      ...(init?.headers ?? {}),
    },
  };
  let response = await fetch(url, requestInit);

  if (response.status === 401 && !path.includes("/auth/") && localStorage.getItem("expert_refresh_token")) {
    const refreshed = await refreshExpertSession();
    if (refreshed) {
      requestInit.headers = {
        ...(requestInit.headers ?? {}),
        Authorization: `Bearer ${localStorage.getItem("expert_token")}`,
      };
      response = await fetch(url, requestInit);
    }
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body && typeof body.message === "string") {
        message = body.message;
      } else if (body && typeof body.error === "string") {
        message = body.error;
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

export function fetchCountries(): Promise<Country[]> {
  return request<Country[]>("/api/countries");
}

export function fetchInternationalCities(countryId: number): Promise<InternationalCity[]> {
  const path = withQuery("/api/international-cities", { country_id: countryId });
  return request<InternationalCity[]>(path);
}

export function submitShipmentRequest(
  payload: ShipmentRequestPayload,
): Promise<{ message: string; id: number; tracking_code: string }> {
  return request<{ message: string; id: number; tracking_code: string }>("/api/shipment-request", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface PublicTrackingWorkflowStep {
  name: string;
  order: number;
  title: string;
  is_completed: boolean;
  completed_at: string | null;
  points_earned?: number;
  meta?: { warning?: string };
}

export interface TransportUnitUpdate {
  status: string;
  location: string | null;
  customer_note: string | null;
  event_at: string;
  location_reference_id?: number | null;
  location_name?: string | null;
  location_text?: string | null;
  country_code?: string | null;
  location_source?: "reference" | "manual" | null;
}

export interface TrackingLocationReference {
  id: number; name_fa: string; name_en: string | null; country_code: string;
  location_type: string; aliases: string[]; is_active: boolean;
  internal_key?: string; reference_status?: string; sort_order?: number; notes?: string | null;
}

export const fetchTrackingLocations = (q = ""): Promise<{ items: TrackingLocationReference[] }> =>
  request(`/api/tracking-locations${q ? `?q=${encodeURIComponent(q)}` : ""}`);
export const fetchAdminTrackingLocations = (q = ""): Promise<{ items: TrackingLocationReference[] }> =>
  request(`/api/tracking-locations?include_inactive=true${q ? `&q=${encodeURIComponent(q)}` : ""}`);
export const createTrackingLocation = (payload: Record<string, unknown>): Promise<TrackingLocationReference> =>
  request("/api/tracking-locations",{method:"POST",body:JSON.stringify(payload)});
export const updateTrackingLocation = (id:number,payload:Record<string,unknown>): Promise<TrackingLocationReference> =>
  request(`/api/tracking-locations/${id}`,{method:"PATCH",body:JSON.stringify(payload)});
export const deactivateTrackingLocation = (id:number): Promise<TrackingLocationReference> =>
  request(`/api/tracking-locations/${id}`,{method:"DELETE"});

// --- Admin location (origin/destination) management ------------------------
// Admin serializers return richer records than the public read endpoints, so
// these admin-facing shapes are separate from Province/County/City above.
export interface AdminProvince {
  id: number; name_fa: string; code: string | null; country_id: number | null; is_active: boolean;
}
export interface AdminCounty {
  id: number; name_fa: string; code: string | null; province_id: number; province_name: string | null; is_active: boolean;
}
export interface AdminCity {
  id: number; name_fa: string; code: string | null; county_id: number; county_name: string | null;
  province_id: number; province_name: string | null; is_active: boolean;
}
export interface AdminCountry {
  id: number; name_fa: string; name_en: string; code: string; is_active: boolean;
}
export interface AdminInternationalCity {
  id: number; name_fa: string; name_en: string; country_id: number; country_name: string | null;
  city_type: string; is_major_port: boolean; is_major_airport: boolean; is_active: boolean;
}
export interface AdminIranPort {
  id: number; name_fa: string; name_en: string; port_type: string; province_id: number;
  province_name: string | null; country_id: number | null; is_major_port: boolean;
  description: string | null; is_active: boolean;
}

/** Admin location resource segments (match backend `_RESOURCES` keys). */
export type AdminLocationResource =
  | "provinces" | "counties" | "cities" | "countries" | "international-cities" | "iran-ports";

function adminLocationPath(resource: AdminLocationResource, params?: Record<string, string | number | undefined>): string {
  return withQuery(`/api/admin/locations/${resource}`, { include_inactive: "true", ...params });
}

export const fetchAdminProvinces = (): Promise<{ items: AdminProvince[] }> =>
  request(adminLocationPath("provinces"));
export const fetchAdminCounties = (provinceId?: number): Promise<{ items: AdminCounty[] }> =>
  request(adminLocationPath("counties", { province_id: provinceId }));
export const fetchAdminCities = (countyId?: number): Promise<{ items: AdminCity[] }> =>
  request(adminLocationPath("cities", { county_id: countyId }));
export const fetchAdminCountries = (): Promise<{ items: AdminCountry[] }> =>
  request(adminLocationPath("countries"));
export const fetchAdminInternationalCities = (countryId?: number): Promise<{ items: AdminInternationalCity[] }> =>
  request(adminLocationPath("international-cities", { country_id: countryId }));
export const fetchAdminIranPorts = (): Promise<{ items: AdminIranPort[] }> =>
  request(adminLocationPath("iran-ports"));

export const createAdminLocation = <T>(resource: AdminLocationResource, payload: Record<string, unknown>): Promise<{ item: T }> =>
  request(`/api/admin/locations/${resource}`, { method: "POST", body: JSON.stringify(payload) });
export const updateAdminLocation = <T>(resource: AdminLocationResource, id: number, payload: Record<string, unknown>): Promise<{ item: T }> =>
  request(`/api/admin/locations/${resource}/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
export const deactivateAdminLocation = <T>(resource: AdminLocationResource, id: number): Promise<{ item: T }> =>
  request(`/api/admin/locations/${resource}/${id}`, { method: "DELETE" });

let refreshPromise: Promise<boolean> | null = null;

export function refreshExpertSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refreshToken = localStorage.getItem("expert_refresh_token");
    if (!refreshToken) return false;
    try {
      const response = await fetch(`${API_BASE_URL}/api/expert/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) throw new Error("refresh rejected");
      const tokens = await response.json();
      localStorage.setItem("expert_token", tokens.access_token);
      localStorage.setItem("expert_refresh_token", tokens.refresh_token);
      return true;
    } catch {
      localStorage.removeItem("expert_user");
      localStorage.removeItem("expert_token");
      localStorage.removeItem("expert_refresh_token");
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

export async function logoutExpert(token: string): Promise<boolean> {
  const url = `${API_BASE_URL}/api/expert/auth/logout`;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function logoutAllExpertSessions(token: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/expert/auth/logout-all`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.ok;
  } catch {
    return false;
  }
}

export interface PublicTransportUnitTracking {
  unit_code: string;
  unit_type: string;
  display_name: string | null;
  vehicle_reference: string | null;
  latest_status: string;
  latest_location: string | null;
  latest_event_at: string | null;
  timeline: TransportUnitUpdate[];
}

export type TrackingAggregateStatus = "not_started" | "in_progress" | "partially_delivered" | "attention_required" | "completed" | "cancelled";
export interface TrackingSummary {
  total_units: number; without_updates: number; not_started: number; loading: number;
  in_transit: number; delayed: number; arrived: number; delivered: number; cancelled: number;
}

export interface MultiUnitTracking {
  enabled: true;
  enabled_at: string | null;
  aggregate_status: TrackingAggregateStatus;
  progress_percent: number;
  summary: TrackingSummary;
  last_updated_at: string | null;
  units: PublicTransportUnitTracking[];
}

export interface InternalTransportUnitTracking {
  id: number; unit_code: string; unit_type: string; display_name: string | null;
  vehicle_reference: string | null; is_active: boolean; latest_status: string;
  latest_location: string | null; latest_event_at: string | null;
}
export interface InternalMultiUnitTracking {
  enabled: true; enabled_at: string | null; aggregate_status: TrackingAggregateStatus;
  summary: TrackingSummary; last_updated_at: string | null; units: InternalTransportUnitTracking[];
}

export interface PublicTrackingData {
  id: number;
  tracking_number: string;
  status: string;
  created_at: string;
  shipping_type: string;
  contact_phone: string;
  customer_first_name?: string;
  customer_last_name?: string;
  route: {
    origin: {
      province?: string;
      county?: string;
      city?: string;
      country?: string;
      city_international?: string;
      address?: string;
    };
    destination: {
      province?: string;
      county?: string;
      city?: string;
      country?: string;
      city_international?: string;
      address?: string;
    };
  };
  transport_method?: string;
  domestic_transport_method?: string;
  international_transport_method?: string;
  transport_method_preference?: string;
  cargo_description?: string;
  cargo_weight?: number;
  cargo_volume?: number;
  cargo_value?: number;
  special_instructions?: string;
  pickup_date?: string | null;
  delivery_date?: string | null;
  assigned_expert?: {
    id: number;
    full_name: string;
    phone: string;
    email?: string;
  };
  assigned_at?: string | null;
  last_customer_touch_at?: string | null;
  latest_quote?: {
    id: number;
    amount: number;
    currency: string;
    note?: string | null;
    valid_until?: string | null;
    created_at: string;
    created_by?: string | null;
  } | null;
  workflow_steps?: PublicTrackingWorkflowStep[];
  workflow_steps_simple?: PublicTrackingWorkflowStep[];
  unit_tracking?: MultiUnitTracking | null;
}

export class PublicTrackingNotFoundError extends Error {
  constructor() {
    super("Public tracking request not found");
    this.name = "PublicTrackingNotFoundError";
  }
}

export class PublicTrackingHttpError extends Error {
  status: number;

  constructor(status: number) {
    super(`Public tracking request failed with status ${status}`);
    this.name = "PublicTrackingHttpError";
    this.status = status;
  }
}

export async function fetchPublicTracking(identifier: string): Promise<PublicTrackingData> {
  const path = `/api/public/track/${encodeURIComponent(identifier)}`;
  const response = await fetch(`${API_BASE_URL}${buildPath(path)}`);

  if (response.status === 404) {
    throw new PublicTrackingNotFoundError();
  }

  if (!response.ok) {
    throw new PublicTrackingHttpError(response.status);
  }

  return (await response.json()) as PublicTrackingData;
}

export interface CustomerProfile {
  id: number;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  is_email_verified: boolean;
  total_requests: number;
  completed_requests: number;
  loyalty_points: number;
  customer_level: string;
  created_at: string;
}

export interface CustomerProfileWorkflowStep {
  step_name: string;
  step_order: number;
  is_completed: boolean;
  completed_at: string | null;
  points_earned: number;
  created_at: string;
}

export interface CustomerProfileRecentRequest {
  id: number;
  shipping_type: string;
  status: string;
  created_at: string;
  assigned_expert: {
    id: number;
    full_name: string;
    phone: string;
  } | null;
}

export interface CustomerProfileData {
  customer: CustomerProfile;
  recent_steps: CustomerProfileWorkflowStep[];
  recent_requests: CustomerProfileRecentRequest[];
}

export class CustomerProfileHttpError extends Error {
  status: number;

  constructor(status: number) {
    super(`Customer profile request failed with status ${status}`);
    this.name = "CustomerProfileHttpError";
    this.status = status;
  }
}

export async function fetchCustomerProfile(customerId: string): Promise<CustomerProfileData> {
  const path = `/api/customer/profile/${customerId}`;
  const response = await fetch(`${API_BASE_URL}${buildPath(path)}`);

  if (!response.ok) {
    throw new CustomerProfileHttpError(response.status);
  }

  return (await response.json()) as CustomerProfileData;
}

export interface CustomerWorkflowStep {
  name: string;
  order: number;
  title: string;
  points?: number;
  is_completed: boolean;
  completed_at: string | null;
  points_earned?: number;
  meta?: { warning?: string };
}

export interface CustomerWorkflowData {
  id: number;
  shipping_type: string;
  status: string;
  created_at: string;
  assigned_expert: {
    id: number;
    full_name: string;
    phone: string;
    email: string;
  } | null;
  workflow_steps: CustomerWorkflowStep[];
  workflow_steps_simple?: CustomerWorkflowStep[];
  total_points_earned: number;
  completed_steps: number;
  total_steps: number;
  latest_quote?: {
    id: number;
    amount: number;
    currency: string;
    note?: string | null;
    valid_until?: string | null;
    created_at: string;
    created_by?: string | null;
  } | null;
}

export class CustomerWorkflowHttpError extends Error {
  status: number;

  constructor(status: number) {
    super(`Customer workflow request failed with status ${status}`);
    this.name = "CustomerWorkflowHttpError";
    this.status = status;
  }
}

export async function fetchCustomerWorkflow(
  customerId: string,
  requestId: string,
): Promise<CustomerWorkflowData> {
  const path = `/api/customer/workflow/${customerId}?request_id=${requestId}`;
  const response = await fetch(`${API_BASE_URL}${buildPath(path)}`);

  if (!response.ok) {
    throw new CustomerWorkflowHttpError(response.status);
  }

  return (await response.json()) as CustomerWorkflowData;
}

export interface CustomerEmailVerificationResponse {
  message?: string;
  customer_id?: number;
}

export interface CustomerEmailVerificationResult {
  ok: boolean;
  data: CustomerEmailVerificationResponse;
}

export async function verifyCustomerEmail(token: string): Promise<CustomerEmailVerificationResult> {
  const path = `/api/customer/verify-email?token=${encodeURIComponent(token)}`;
  const response = await fetch(`${API_BASE_URL}${buildPath(path)}`);
  const data = (await response.json()) as CustomerEmailVerificationResponse;

  return {
    ok: response.ok,
    data,
  };
}

export interface AdminDashboardStats {
  total_requests: number;
  requests_per_transport_method: Record<string, number>;
  requests_per_status: Record<string, number>;
  last_7_days_count: number;
  last_24h_count: number;
  unassigned_count: number;
  top_provinces: Array<{ province: string; count: number }>;
}

export class AdminDashboardHttpError extends Error {
  status: number;

  constructor(status: number) {
    super(`Admin dashboard request failed with status ${status}`);
    this.name = "AdminDashboardHttpError";
    this.status = status;
  }
}

export async function fetchAdminDashboard(token: string): Promise<AdminDashboardStats> {
  const response = await fetch(`${API_BASE_URL}${buildPath("/api/admin/dashboard")}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new AdminDashboardHttpError(response.status);
  }

  return (await response.json()) as AdminDashboardStats;
}

export type AdminReportPeriod = "weekly" | "monthly" | "yearly";

export interface AdminReportDownload {
  blob: Blob;
  filename: string;
}

export class AdminReportDownloadHttpError extends Error {
  status: number;

  constructor(status: number) {
    super(`Admin report download failed with status ${status}`);
    this.name = "AdminReportDownloadHttpError";
    this.status = status;
  }
}

export async function downloadAdminReportXlsx(token: string, period: AdminReportPeriod): Promise<AdminReportDownload> {
  const response = await fetch(`${API_BASE_URL}${buildPath(`/api/admin/reports/export.xlsx?period=${period}`)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new AdminReportDownloadHttpError(response.status);
  }

  const contentDisposition = response.headers.get("Content-Disposition") || "";
  const filename = getFilenameFromContentDisposition(contentDisposition) || `forwarder-report-${period}.xlsx`;

  return {
    blob: await response.blob(),
    filename,
  };
}

function getFilenameFromContentDisposition(contentDisposition: string): string | null {
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].replace(/"/g, ""));
  }

  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return filenameMatch?.[1] || null;
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
  latest_quote?: {
    id: number;
    amount: number;
    currency: string;
    note?: string | null;
    valid_until?: string | null;
    created_at: string;
    created_by?: string | null;
  } | null;
}> {
  return request(`/api/expert/requests/${requestId}`);
}

export interface TrackingManagementData {
  eligible: boolean;
  request_status: string;
  tracking_code: string | null;
  enabled: boolean;
  unit_tracking: InternalMultiUnitTracking | null;
}

export const fetchTrackingManagement = (requestId: number): Promise<TrackingManagementData> =>
  request(`/api/expert/requests/${requestId}/tracking`);

export const enableTrackingManagement = (requestId: number): Promise<TrackingManagementData> =>
  request(`/api/expert/requests/${requestId}/tracking/enable`, { method: "POST" });

export const addTrackingUnit = (
  requestId: number,
  payload: { unit_code: string; unit_type: string; display_name?: string; vehicle_reference?: string },
): Promise<TrackingManagementData> =>
  request(`/api/expert/requests/${requestId}/tracking/units`, { method: "POST", body: JSON.stringify(payload) });

export const updateTrackingUnitMetadata = (
  requestId: number,
  unitId: number,
  payload: { display_name?: string; vehicle_reference?: string },
): Promise<TrackingManagementData> =>
  request(`/api/expert/requests/${requestId}/tracking/units/${unitId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const addTrackingUnitUpdate = (
  requestId: number,
  unitId: number,
  payload: {
    status: string;
    location?: string;
    location_reference_id?: number;
    location_text?: string;
    customer_message?: string;
    internal_note?: string;
    is_customer_visible: boolean;
    occurred_at: string;
  },
): Promise<TrackingManagementData> =>
  request(`/api/expert/requests/${requestId}/tracking/units/${unitId}/updates`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export interface SubmitQuotePayload {
  amount: number;
  currency?: string;
  note?: string;
  valid_until?: string;
}

export function submitQuote(
  requestId: number,
  payload: SubmitQuotePayload
): Promise<{ ok: boolean; quote: { id: number; amount: number; currency: string; note?: string | null; valid_until?: string | null; created_at: string }; request: { id: number; status: string } }> {
  return request(`/api/expert/requests/${requestId}/quote`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
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

// Site settings (public + admin)
export type SiteSettings = Record<string, string>;

export function fetchSiteSettings(): Promise<SiteSettings> {
  return request("/api/site-settings");
}

export function updateSiteSettings(settings: SiteSettings): Promise<SiteSettings> {
  return request("/api/admin/site-settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

/** Upload logo image; returns { url: string }. Admin only. */
export async function uploadLogo(file: File): Promise<{ url: string }> {
  const API_BASE_URL = import.meta.env.DEV ? "" : (import.meta.env.VITE_API_URL || "");
  const path = (p: string) => (API_BASE_URL ? `${API_BASE_URL}${p}` : p);
  const url = path("/api/admin/upload");
  const token = localStorage.getItem("expert_token");
  const formData = new FormData();
  formData.append("file", file);
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const response = await fetch(url, { method: "POST", body: formData, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error((body && body.error) || `Upload failed: ${response.status}`);
  }
  return response.json();
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

export interface CRMLinkCustomer {
  id: number;
  name: string;
  company_name?: string | null;
  email?: string | null;
  phone?: string | null;
  mobile?: string | null;
  customer_type?: string | null;
  status?: string | null;
  match_strength?: "strong" | "weak" | "possible";
  match_score?: number;
  match_reasons?: string[];
}

export interface CRMShipmentRequestLinkState {
  operation: "read" | "link" | "relink" | "unlink" | "noop" | "create" | "create_and_link";
  shipment_request: {
    id: number;
    customer_id: number | null;
    status: string;
    assigned_to?: number | null;
    gamification_customer_id?: number | null;
  };
  customer: CRMLinkCustomer | null;
}

export interface CRMCreateCustomerFields {
  first_name?: string | null;
  last_name?: string | null;
  company_name?: string | null;
  email?: string | null;
  phone?: string | null;
  mobile?: string | null;
  customer_type?: string | null;
  status?: string | null;
  source?: string | null;
  notes?: string | null;
  city?: string | null;
  province?: string | null;
  country?: string | null;
}

export interface CRMCustomerCreatePreview {
  operation: "preview";
  preview_only: true;
  shipment_request: CRMShipmentRequestLinkState["shipment_request"];
  suggested_customer: CRMCreateCustomerFields;
  duplicate_candidates: CRMLinkCustomer[];
  metadata: {
    match_policy: string;
    strong_duplicate_count: number;
    missing_fields: {
      required: string[];
      recommended: string[];
    };
    can_create_without_user_review: boolean;
    mutation_allowed: boolean;
  };
}

export interface CRMCustomerCreateResult extends CRMShipmentRequestLinkState {
  operation: "create" | "create_and_link";
  created_customer: CRMLinkCustomer;
  duplicate_candidates: CRMLinkCustomer[];
  metadata: {
    linked: boolean;
    strong_duplicate_count: number;
    duplicate_acknowledged: boolean;
  };
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
  return request(`/api/crm/customers/${customerId}`);
}

export function updateCustomer(
  customerId: number,
  customerData: Partial<CustomerDetail>
): Promise<{ message: string }> {
  return request(`/api/crm/customers/${customerId}`, {
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

export function searchCRMLinkCustomers(params?: {
  page?: number;
  per_page?: number;
  search?: string;
}): Promise<{
  customers: CRMLinkCustomer[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}> {
  const path = withQuery("/api/crm/customer-link/customers", params);
  return request(path);
}

export function fetchShipmentRequestCustomerLink(requestId: number): Promise<CRMShipmentRequestLinkState> {
  return request(`/api/crm/shipment-requests/${requestId}/customer-link`);
}

export function fetchShipmentRequestCustomerCreatePreview(
  requestId: number
): Promise<CRMCustomerCreatePreview> {
  return request(`/api/crm/shipment-requests/${requestId}/customer-create-preview`);
}

export function createCustomerFromShipmentRequest(
  requestId: number,
  payload: {
    customer: CRMCreateCustomerFields;
    link: boolean;
    duplicate_acknowledged?: boolean;
    reason?: string;
  }
): Promise<CRMCustomerCreateResult> {
  return request(`/api/crm/shipment-requests/${requestId}/create-customer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function linkShipmentRequestCustomer(
  requestId: number,
  customerId: number,
  note?: string
): Promise<CRMShipmentRequestLinkState> {
  return request(`/api/crm/shipment-requests/${requestId}/customer-link`, {
    method: "PUT",
    body: JSON.stringify({ customer_id: customerId, note: note?.trim() || undefined }),
  });
}

export function unlinkShipmentRequestCustomer(
  requestId: number,
  note?: string
): Promise<CRMShipmentRequestLinkState> {
  return request(`/api/crm/shipment-requests/${requestId}/customer-link`, {
    method: "DELETE",
    body: JSON.stringify({ note: note?.trim() || undefined }),
  });
}

// User Management Interfaces
export interface TransportMethod {
  id: number;
  name: string;
  name_fa: string;
  description?: string;
  is_active: boolean;
  created_at: string;
}

export interface UserSpecialization {
  id: number;
  transport_method: {
    id: number;
    name: string;
  };
  proficiency_level: string;
  is_primary: boolean;
}

export interface User {
  id: number;
  username: string;
  full_name: string;
  email?: string;
  phone?: string;
  role: string;
  department?: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
  manager?: {
    id: number;
    name: string;
  };
  subordinates_count: number;
  specializations: UserSpecialization[];
  workload: number;
}

export interface AssignmentRule {
  id: number;
  name: string;
  description?: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  priority: number;
  is_active: boolean;
  created_by: {
    id: number;
    name: string;
  };
  created_at: string;
  updated_at: string;
}

export interface AssignmentStatistics {
  total_assignments: number;
  automatic_assignments: number;
  manual_assignments: number;
  expert_workloads: {
    expert_id: number;
    expert_name: string;
    workload: number;
  }[];
}

// User Management API Functions
export function fetchUsers(): Promise<{ users: User[] }> {
  return request("/api/user-management/users");
}

export function createUser(userData: {
  username: string;
  password_hash: string;
  full_name: string;
  email?: string;
  phone?: string;
  role: string;
  department?: string;
  manager_id?: number;
  is_active?: boolean;
  specializations?: {
    transport_method_id: number;
    proficiency_level?: string;
    is_primary?: boolean;
  }[];
}): Promise<{ message: string; user_id: number }> {
  return request("/api/user-management/users", {
    method: "POST",
    body: JSON.stringify(userData),
  });
}

export function updateUser(
  userId: number,
  userData: Partial<User>
): Promise<{ message: string }> {
  return request(`/api/user-management/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(userData),
  });
}

export function fetchTransportMethods(): Promise<{ transport_methods: TransportMethod[] }> {
  return request("/api/user-management/transport-methods");
}

export function fetchTransportMethodOptions(): Promise<TransportMethodOptions> {
  return request("/api/transport-methods");
}

export function createTransportMethod(transportData: {
  name: string;
  name_fa: string;
  description?: string;
  is_active?: boolean;
}): Promise<{ message: string; transport_method_id: number }> {
  return request("/api/user-management/transport-methods", {
    method: "POST",
    body: JSON.stringify(transportData),
  });
}

export function fetchAssignmentRules(): Promise<{ assignment_rules: AssignmentRule[] }> {
  return request("/api/user-management/assignment-rules");
}

export function createAssignmentRule(ruleData: {
  name: string;
  description?: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  priority?: number;
  is_active?: boolean;
}): Promise<{ message: string; rule_id: number }> {
  return request("/api/user-management/assignment-rules", {
    method: "POST",
    body: JSON.stringify(ruleData),
  });
}

export function updateAssignmentRule(
  ruleId: number,
  ruleData: Partial<AssignmentRule>
): Promise<{ message: string }> {
  return request(`/api/user-management/assignment-rules/${ruleId}`, {
    method: "PUT",
    body: JSON.stringify(ruleData),
  });
}

export function fetchAssignmentStatistics(): Promise<AssignmentStatistics> {
  return request("/api/user-management/assignment-statistics");
}

export function manualAssignment(assignmentData: {
  request_id: number;
  expert_id: number;
  reason?: string;
}): Promise<{ message: string }> {
  return request("/api/user-management/manual-assignment", {
    method: "POST",
    body: JSON.stringify(assignmentData),
  });
}

// Referral rules (admin) - قوانین ارجاع
export interface ReferralRuleActionDirect {
  type: "direct_assign";
  expert_id: number;
}

export interface ReferralRuleActionPool {
  type: "pool_assign";
  expert_ids: number[];
  strategy: "round_robin" | "least_workload";
  max_active_assignments_per_expert?: number | null;
}

export type ReferralRuleAction = ReferralRuleActionDirect | ReferralRuleActionPool;

export interface ReferralRuleConditions {
  shipping_type?: "domestic" | "international" | null;
  transport_method?: "road" | "rail" | "air" | "sea" | "unknown" | null;
  origin_province?: number | null;
  destination_province?: number | null;
}

export interface ReferralRuleRow {
  id: number;
  name: string;
  is_active: boolean;
  priority: number;
  conditions: ReferralRuleConditions;
  action: ReferralRuleAction;
  stop_on_match: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  action_type: string;
  pool_expert_count: number;
  strategy: string | null;
}

export function fetchReferralRules(): Promise<{ referral_rules: ReferralRuleRow[] }> {
  return request("/api/admin/referral-rules");
}

export function createReferralRule(ruleData: {
  name: string;
  is_active?: boolean;
  priority?: number;
  conditions: ReferralRuleConditions;
  action: ReferralRuleAction;
  stop_on_match?: boolean;
}): Promise<{ message: string; rule_id: number }> {
  return request("/api/admin/referral-rules", {
    method: "POST",
    body: JSON.stringify(ruleData),
  });
}

export function updateReferralRule(
  ruleId: number,
  ruleData: Partial<{
    name: string;
    is_active: boolean;
    priority: number;
    conditions: ReferralRuleConditions;
    action: ReferralRuleAction;
    stop_on_match: boolean;
  }>
): Promise<{ message: string }> {
  return request(`/api/admin/referral-rules/${ruleId}`, {
    method: "PUT",
    body: JSON.stringify(ruleData),
  });
}

export function deleteReferralRule(ruleId: number): Promise<{ message: string }> {
  return request(`/api/admin/referral-rules/${ruleId}`, { method: "DELETE" });
}

export interface ReferralPreviewResult {
  matched_rule: { id: number; name: string; priority: number } | null;
  candidates: number[];
  selected_expert: { id: number; full_name: string } | null;
  strategy_used: string | null;
  debug_trace: Record<string, unknown>;
  error?: string;
}

export function previewReferralRule(requestId: number): Promise<ReferralPreviewResult> {
  return request("/api/admin/referral-rules/preview", {
    method: "POST",
    body: JSON.stringify({ request_id: requestId }),
  });
}

// Iran Ports API Functions
export function fetchIranPorts(portType?: string): Promise<IranPort[]> {
  const params = portType ? `?port_type=${portType}` : "";
  return request(`/api/iran-ports${params}`);
}

export function fetchPortProvinceMappings(params: {
  port_id?: number;
  province_id?: number;
}): Promise<PortProvinceMapping[]> {
  const queryParams = new URLSearchParams();
  if (params.port_id) queryParams.append("port_id", params.port_id.toString());
  if (params.province_id) queryParams.append("province_id", params.province_id.toString());
  
  const queryString = queryParams.toString();
  return request(`/api/port-province-mappings${queryString ? `?${queryString}` : ""}`);
}

export function fetchRecommendedPorts(provinceId: number): Promise<RecommendedPort[]> {
  return request(`/api/recommended-ports?province_id=${provinceId}`);
}
