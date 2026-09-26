import { useEffect } from "react";

export const OWNER_CHANGED_EVENT = "forwarder-owner-changed";

/** Revalidate on return to this surface; server authorization remains decisive. */
export function useCurrentAuthorityRefresh(refresh: () => unknown, retire?: () => void) {
  useEffect(() => {
    const visible = () => { if (document.hidden) retire?.(); else void refresh(); };
    const resume = () => { if (!document.hidden) void refresh(); };
    window.addEventListener("focus", resume);
    window.addEventListener("pageshow", resume);
    window.addEventListener(OWNER_CHANGED_EVENT, resume);
    document.addEventListener("visibilitychange", visible);
    return () => {
      window.removeEventListener("focus", resume);
      window.removeEventListener("pageshow", resume);
      window.removeEventListener(OWNER_CHANGED_EVENT, resume);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [refresh, retire]);
}
