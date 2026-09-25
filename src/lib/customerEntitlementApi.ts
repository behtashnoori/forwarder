import { request } from "@/lib/api";

export interface CustomerAccessGrant {
  public_id: string;
  portal_account_public_id: string;
  account_label: string;
  customer_id: number;
  customer_label: string;
  status: "ACTIVE" | "REVOKED";
  granted_at: string;
  granted_by: number;
  revoked_at: string | null;
  revoked_by: number | null;
}
export interface CustomerAccessConfiguration {
  accounts: Array<{ public_id: string; label: string }>;
  customers: Array<{ id: number; label: string }>;
  grants: CustomerAccessGrant[];
}
const path = "/api/admin/customer-entitlements";
export const fetchCustomerAccess = () => request<CustomerAccessConfiguration>(path, { cache: "no-store" });
export const grantCustomerAccess = (accountId: string, customerId: number, commandKey: string) =>
  request<{ item: CustomerAccessGrant }>(path, {
    method: "POST", headers: { "Idempotency-Key": commandKey },
    body: JSON.stringify({ portal_account_public_id: accountId, customer_id: customerId }),
  });
export const revokeCustomerAccess = (grantId: string) =>
  request<{ item: CustomerAccessGrant }>(`${path}/${encodeURIComponent(grantId)}/revoke`, { method: "POST" });
