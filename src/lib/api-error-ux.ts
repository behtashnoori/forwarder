export type ApiErrorState = "permission" | "not-found" | "validation" | "conflict" | "network" | "server";

export type UserFacingApiError = { state: ApiErrorState; message: string; retryable: boolean };

/** Maps transport errors to short, safe Persian messages without changing API semantics. */
export function toUserFacingApiError(error: unknown): UserFacingApiError {
  const status = typeof error === "object" && error && "status" in error && typeof error.status === "number" ? error.status : undefined;
  if (status !== undefined) {
    if (status === 401 || status === 403) return { state: "permission", message: "اجازه انجام این اقدام را ندارید.", retryable: false };
    if (status === 404) return { state: "not-found", message: "مورد موردنظر دیگر در دسترس نیست.", retryable: false };
    if (status === 409) return { state: "conflict", message: "اطلاعات تغییر کرده یا این مورد از قبل وجود دارد. صفحه را تازه کنید.", retryable: true };
    if (status === 400 || status === 422) return { state: "validation", message: "اطلاعات واردشده را بررسی کنید.", retryable: false };
    if (status >= 500) return { state: "server", message: "سرویس موقتاً در دسترس نیست. دوباره تلاش کنید.", retryable: true };
  }
  if (error instanceof TypeError) return { state: "network", message: "ارتباط با سرویس برقرار نشد. اتصال اینترنت را بررسی و دوباره تلاش کنید.", retryable: true };
  return { state: "server", message: "امکان انجام این درخواست وجود ندارد. دوباره تلاش کنید.", retryable: true };
}
