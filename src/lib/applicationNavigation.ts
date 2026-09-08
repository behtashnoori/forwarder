const PREVIOUS_ROUTE = "forwarder_previous_app_route";
const CURRENT_ROUTE = "forwarder_current_app_route";

export const authenticatedHome = () => {
  try {
    const user = JSON.parse(localStorage.getItem("expert_user") || "{}");
    return ["PLATFORM_ADMIN", "ORGANIZATION_ADMIN"].includes(user.authority) ? "/admin" : "/expert";
  } catch {
    return "/expert";
  }
};

export const rememberApplicationRoute = (route: string) => {
  const current = sessionStorage.getItem(CURRENT_ROUTE);
  if (current && current !== route && current !== "/") sessionStorage.setItem(PREVIOUS_ROUTE, current);
  sessionStorage.setItem(CURRENT_ROUTE, route);
};

export const safePreviousRoute = () => {
  const previous = sessionStorage.getItem(PREVIOUS_ROUTE);
  return previous && previous.startsWith("/") && previous !== "/" ? previous : authenticatedHome();
};
