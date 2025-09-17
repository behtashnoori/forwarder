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
}

const rawBaseUrl = import.meta.env.VITE_API_URL ?? "";
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

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
    throw new Error("VITE_API_URL is not defined");
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
  return request<Province[]>("/provinces");
}

export function fetchCounties(provinceId: number): Promise<County[]> {
  const path = withQuery("/counties", { province_id: provinceId });
  return request<County[]>(path);
}

export function fetchCities(countyId: number): Promise<City[]> {
  const path = withQuery("/cities", { county_id: countyId });
  return request<City[]>(path);
}

export function submitShipmentRequest(
  payload: ShipmentRequestPayload,
): Promise<{ message: string; id: number }> {
  return request<{ message: string; id: number }>("/shipment-request", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
