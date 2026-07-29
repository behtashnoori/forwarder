const RETURN_TO_KEY = "expert_return_to";

export function isSafeInternalReturnTo(value: string | null | undefined): value is string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return false;
  try {
    const parsed = new URL(value, window.location.origin);
    return parsed.origin === window.location.origin;
  } catch {
    return false;
  }
}

export function rememberCurrentRouteForLogin(): void {
  const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (isSafeInternalReturnTo(returnTo) && returnTo !== "/") {
    sessionStorage.setItem(RETURN_TO_KEY, returnTo);
  }
}

export function consumeReturnTo(fallback: string): string {
  const candidate = sessionStorage.getItem(RETURN_TO_KEY);
  sessionStorage.removeItem(RETURN_TO_KEY);
  return isSafeInternalReturnTo(candidate) ? candidate : fallback;
}

export function clearExpertSession(): void {
  localStorage.removeItem("expert_user");
  localStorage.removeItem("expert_token");
  localStorage.removeItem("expert_refresh_token");
}
