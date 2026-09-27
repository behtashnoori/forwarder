type CustomerMaintenanceActor = { authority?: unknown; capabilities?: unknown };

/** Tenant customer master data belongs exclusively to Organization Admins. */
export function canManageTenantCustomers(actor: CustomerMaintenanceActor | null | undefined): boolean {
  return actor?.authority === "ORGANIZATION_ADMIN"
    || (Array.isArray(actor?.capabilities) && actor.capabilities.includes("ORGANIZATION_ADMIN"));
}

export function currentActorCanManageTenantCustomers(): boolean {
  try {
    return canManageTenantCustomers(JSON.parse(localStorage.getItem("expert_user") || "{}"));
  } catch {
    return false;
  }
}
