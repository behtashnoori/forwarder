import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { customerRequest, CustomerPortalApiError } from "@/lib/customerPortalApi";

/** No retained projection across navigation, return, revocation or failed reads. */
export function usePrivateCustomerRead<T extends { authorization_revision: string }>(path: string) {
  const navigate = useNavigate();
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{ path: string; data: T | null; loading: boolean; error: string }>({ path, data: null, loading: true, error: "" });
  const cancel = useRef<() => void>(() => undefined);
  useEffect(() => {
    let alive = true;
    let generation = 0;
    let controller: AbortController | undefined;
    const clear = () => {
      generation = generation + 1;
      controller?.abort();
      setState({ path, data: null, loading: true, error: "" });
    };
    cancel.current = () => { generation = generation + 1; controller?.abort(); };
    const load = async () => {
      clear();
      if (document.visibilityState === "hidden") return;
      const current = generation;
      controller = new AbortController();
      try {
        // Reauthorize after receiving a potentially delayed response, before render.
        // A changed scope discards that body and obtains a new projection once.
        for (let attempt = 0; attempt < 2; attempt += 1) {
          const data = await customerRequest<T>(path, { cache: "no-store", signal: controller.signal });
          if (!alive || current !== generation) return;
          const authorization = await customerRequest<{ authorization_revision: string }>("/api/customer/shipments/authorization", { cache: "no-store", signal: controller.signal });
          if (!alive || current !== generation) return;
          if (data.authorization_revision && data.authorization_revision === authorization.authorization_revision) {
            setState({ path, data, loading: false, error: "" });
            return;
          }
        }
        throw new Error("دسترسی تغییر کرده است؛ دوباره بخوانید.");
      } catch (error) {
        if (!alive || current !== generation) return;
        setState({ path, data: null, loading: false, error: error instanceof Error ? error.message : "دریافت اطلاعات ممکن نشد." });
        if (error instanceof CustomerPortalApiError && error.status === 401) navigate("/customer", { replace: true });
      }
    };
    const refresh = () => { void load(); };
    const visibility = () => { if (document.visibilityState === "hidden") clear(); else refresh(); };
    void load();
    window.addEventListener("focus", refresh);
    window.addEventListener("pageshow", refresh);
    window.addEventListener("pagehide", clear);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      alive = false; generation = generation + 1; controller?.abort(); cancel.current = () => undefined;
      window.removeEventListener("focus", refresh); window.removeEventListener("pageshow", refresh);
      window.removeEventListener("pagehide", clear); document.removeEventListener("visibilitychange", visibility);
    };
  }, [path, revision, navigate]);
  const refresh = useCallback(() => {
    cancel.current(); setState({ path, data: null, loading: true, error: "" }); setRevision(value => value + 1);
  }, [path]);
  const invalidate = useCallback((error: string) => {
    cancel.current(); setState({ path, data: null, loading: false, error });
  }, [path]);
  return { ...(state.path === path ? state : { data: null, loading: true, error: "" }), refresh, invalidate };
}
