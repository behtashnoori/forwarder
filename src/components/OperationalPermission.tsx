import { ReactNode, useEffect, useState } from "react";
import { getOperationalContext } from "@/lib/api";

export default function OperationalPermission({ permission, children }: { permission: string; children: ReactNode }) {
  const [allowed, setAllowed] = useState(false);
  useEffect(() => {
    getOperationalContext().then((result) => setAllowed(result.data.permissions.includes(permission))).catch(() => setAllowed(false));
  }, [permission]);
  return allowed ? <>{children}</> : null;
}
